from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional, Dict
import random
import re
import httpx
from datetime import datetime, timedelta

from ..core.db import get_session, get_engine
from ..core.config import settings
from ..core.email import send_otp_email, send_payment_receipt_email
from ..core.security import Security
from ..schemas.tenant import Tenant
from ..schemas.barber import Barber

router = APIRouter(prefix="/api/v1/registration", tags=["registration"])

# Almacenamiento temporal en memoria para los OTPs:
# email -> {"otp": "123456", "expires_at": datetime, "verified": bool}
otp_store: Dict[str, dict] = {}

class RequestOTPRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class CreateOrderRequest(BaseModel):
    plan: str
    email: str

class CompleteRegistrationRequest(BaseModel):
    order_id: str
    plan: str
    email: str
    shop_name: str
    phone: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str
    image_url: Optional[str] = None
    owner_name: str
    password: str

def clean_expired_otps():
    now = datetime.utcnow()
    expired = [email for email, data in otp_store.items() if data["expires_at"] < now]
    for email in expired:
        del otp_store[email]

def slugify(text: str) -> str:
    text = text.lower().strip()
    # Eliminar acentos y caracteres especiales
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def generate_unique_slug(session: Session, shop_name: str) -> str:
    base_slug = slugify(shop_name)
    if not base_slug:
        base_slug = "barberia"
    slug = base_slug
    counter = 1
    while True:
        existing = session.exec(select(Tenant).where(Tenant.slug == slug)).first()
        if not existing:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1

async def get_paypal_access_token() -> str:
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Las credenciales de la API de PayPal no están configuradas."
        )
    
    # URL de OAuth2 de Sandbox o Live
    host = "api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "api-m.paypal.com"
    url = f"https://{host}/v1/oauth2/token"
    
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en_US",
    }
    data = {
        "grant_type": "client_credentials"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                url,
                auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
                headers=headers,
                data=data,
                timeout=12.0
            )
            if resp.status_code != 200:
                print(f"[PayPal Auth Error] Status: {resp.status_code}, Body: {resp.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Error al autenticar con PayPal."
                )
            return resp.json()["access_token"]
        except httpx.RequestError as e:
            print(f"[PayPal Connection Error] {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="No se pudo establecer conexión con los servidores de PayPal."
            )

@router.post("/request-otp")
async def request_otp(request: RequestOTPRequest, session: Session = Depends(get_session)):
    """
    Genera un código OTP de 6 dígitos para verificar el correo del dueño de la barbería,
    y se lo envía usando la cuenta de Gmail configurada.
    """
    clean_expired_otps()
    email = request.email.strip().lower()
    
    if not email:
        raise HTTPException(status_code=400, detail="El correo electrónico es requerido.")
        
    # Verificar si el correo ya está registrado para algún barbero
    existing_barber = session.exec(select(Barber).where(Barber.email == email)).first()
    if existing_barber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_RECORD,
            detail="Este correo electrónico ya está registrado en la plataforma."
        )

    # Generar OTP de 6 dígitos
    otp = f"{random.randint(100000, 999999)}"
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Enviar correo electrónico
    success = send_otp_email(email, otp)
    msg_detail = "Código de verificación enviado con éxito."
    if not success:
        print("\n" + "="*80)
        print(" WARNING: FALLBACK OTP GENERATED ".center(80, "="))
        print(f"Failed to send email to: {email}")
        print(f"Your verification OTP code is: {otp}")
        print(f"Please use this code in the frontend registration form.")
        print("="*80 + "\n")
        msg_detail = f"Código de verificación generado (Respaldo activo: OTP={otp})."
        
    # Almacenar en la caché temporal
    otp_store[email] = {
        "otp": otp,
        "expires_at": expires_at,
        "verified": False
    }
    
    return {"message": msg_detail}

@router.post("/verify-otp")
def verify_otp(request: VerifyOTPRequest):
    """
    Verifica que el OTP ingresado por el usuario coincida con el enviado y no haya expirado.
    """
    clean_expired_otps()
    email = request.email.strip().lower()
    user_otp = request.otp.strip()
    
    if email not in otp_store:
        raise HTTPException(
            status_code=400,
            detail="No se ha solicitado ningún código de verificación para este correo."
        )
        
    otp_data = otp_store[email]
    
    if otp_data["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="El código de verificación ha expirado. Solicita uno nuevo."
        )
        
    if otp_data["otp"] != user_otp:
        raise HTTPException(
            status_code=400,
            detail="El código de verificación es incorrecto."
        )
        
    otp_store[email]["verified"] = True
    return {"message": "Correo verificado exitosamente."}

@router.post("/create-paypal-order")
async def create_paypal_order(request: CreateOrderRequest):
    """
    Crea una orden de pago en PayPal Sandbox para el plan seleccionado.
    Solo se permite si el correo ha sido previamente verificado con OTP.
    """
    clean_expired_otps()
    email = request.email.strip().lower()
    plan = request.plan.strip().lower()
    
    if plan not in ("normal", "pro"):
        raise HTTPException(status_code=400, detail="El plan seleccionado no es válido.")
        
    if email not in otp_store or not otp_store[email]["verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes verificar tu correo electrónico con OTP antes de realizar el pago."
        )
        
    price = "700.00" if plan == "pro" else "300.00"
    
    token = await get_paypal_access_token()
    
    host = "api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "api-m.paypal.com"
    url = f"https://{host}/v2/checkout/orders"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "MXN",
                "value": price
            },
            "description": f"Registro Balam Barber Platform - Plan {plan.upper()}"
        }]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, json=body, timeout=12.0)
            if resp.status_code not in (200, 201):
                print(f"[PayPal Order Error] Status: {resp.status_code}, Body: {resp.text}")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error al crear la orden de PayPal.")
            return {"order_id": resp.json()["id"]}
        except httpx.RequestError as e:
            print(f"[PayPal Connection Error] {e}")
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Fallo en la comunicación con PayPal.")

@router.post("/complete")
async def complete_registration(request: CompleteRegistrationRequest, session: Session = Depends(get_session)):
    """
    Captura la orden de PayPal. Si el pago es exitoso, crea el Tenant (Barbería)
    y el Barber (Administrador) en la base de datos de producción.
    """
    clean_expired_otps()
    email = request.email.strip().lower()
    order_id = request.order_id.strip()
    plan = request.plan.strip().lower()
    
    # 1. Validaciones previas
    if email not in otp_store or not otp_store[email]["verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El correo electrónico no ha sido verificado."
        )
        
    if plan not in ("normal", "pro"):
        raise HTTPException(status_code=400, detail="El plan no es válido.")

    # 2. Capturar el pago en PayPal
    token = await get_paypal_access_token()
    
    host = "api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "api-m.paypal.com"
    url = f"https://{host}/v2/checkout/orders/{order_id}/capture"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, timeout=15.0)
            if resp.status_code not in (200, 201):
                print(f"[PayPal Capture Error] Status: {resp.status_code}, Body: {resp.text}")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="El cobro no pudo completarse en PayPal.")
            
            capture_data = resp.json()
            if capture_data.get("status") != "COMPLETED":
                raise HTTPException(status_code=400, detail="La transacción de PayPal no ha sido completada.")
        except httpx.RequestError as e:
            print(f"[PayPal Connection Error] {e}")
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Fallo en la comunicación con PayPal.")

    # 3. Pago exitoso -> Crear Tenant y Barbero
    try:
        # Generar un slug único
        slug = generate_unique_slug(session, request.shop_name)
        
        # Calcular fecha de vencimiento de la suscripción (30 días a partir de hoy)
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Crear Barbería (Tenant)
        # Plan Pro es destacado (is_featured = True)
        is_featured = (plan == "pro")
        
        new_tenant = Tenant(
            name=request.shop_name.strip(),
            slug=slug,
            phone=request.phone.strip(),
            is_active=True,
            address=request.address.strip(),
            latitude=request.latitude,
            longitude=request.longitude,
            is_featured=is_featured,
            image_url=request.image_url.strip() if request.image_url else "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=600&q=80",
            description=request.description.strip(),
            subscription_expires_at=expires_at,
            business_hours={
                "monday": {"open": "09:00", "close": "18:00"},
                "tuesday": {"open": "09:00", "close": "18:00"},
                "wednesday": {"open": "09:00", "close": "18:00"},
                "thursday": {"open": "09:00", "close": "18:00"},
                "friday": {"open": "09:00", "close": "18:00"},
                "saturday": {"open": "09:00", "close": "16:00"},
                "sunday": None
            }
        )
        
        session.add(new_tenant)
        session.flush() # Obtener el ID autogenerado del Tenant
        
        # Crear el primer Barbero (Administrador) para esta barbería
        password_hash = Security.hash_password(request.password)
        
        new_barber = Barber(
            name=request.owner_name.strip(),
            email=email,
            password_hash=password_hash,
            tenant_id=new_tenant.id,
            is_active=True
        )
        
        session.add(new_barber)
        session.commit()
        
        # Limpiar la caché temporal del OTP
        del otp_store[email]
        
        # Enviar comprobante de pago por correo electrónico (sin bloquear el registro si SMTP falla)
        try:
            amount = 700.00 if plan == "pro" else 300.00
            send_payment_receipt_email(
                to_email=email,
                owner_name=request.owner_name.strip(),
                shop_name=request.shop_name.strip(),
                plan_name=plan,
                amount=amount,
                expires_at=expires_at
            )
        except Exception as email_err:
            print(f"[Registration Email Warning] No se pudo enviar el comprobante de pago por correo: {email_err}")
        
        return {
            "status": "success",
            "message": "Registro completado con éxito.",
            "tenant": {
                "id": str(new_tenant.id),
                "name": new_tenant.name,
                "slug": new_tenant.slug,
                "is_featured": new_tenant.is_featured
            },
            "barber": {
                "id": str(new_barber.id),
                "name": new_barber.name,
                "email": new_barber.email
            }
        }
    except Exception as e:
        session.rollback()
        print(f"[Registration DB Error] {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al registrar la barbería en la base de datos."
        )
