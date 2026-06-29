from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from ..core.db import get_session
from ..core.security import Security
from ..schemas.barber import Barber
from ..schemas.tenant import Tenant
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Schemas para request/response
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    barber: dict

class LogoutRequest(BaseModel):
    pass

@router.post("/register")
def register(request: RegisterRequest, session: Session = Depends(get_session)):
    """
    Registrar un nuevo barbero.
    """
    # Verificar si el email ya existe
    existing = session.exec(
        select(Barber).where(Barber.email == request.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ya registrado"
        )

    # Crear tenant si no existe
    tenant = session.exec(select(Tenant)).first()
    if not tenant:
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Default Tenant",
            slug="default-tenant",
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant)
        session.flush()

    # Crear barbero
    barber = Barber(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name=request.name,
        email=request.email,
        password_hash=Security.hash_password(request.password),
        is_active=True
    )
    session.add(barber)
    session.commit()

    return {"message": "Barbero registrado exitosamente", "barber_id": str(barber.id)}

@router.post("/login")
def login(request: LoginRequest, session: Session = Depends(get_session)):
    """
    Login del barbero.
    Retorna JWT token si las credenciales son válidas.
    """
    # Buscar barbero por email
    barber = session.exec(
        select(Barber).where(Barber.email == request.email, Barber.is_active == True)
    ).first()

    if not barber or not barber.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña inválidos"
        )

    # Verificar contraseña
    if not Security.verify_password(request.password, barber.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña inválidos"
        )

    # Crear JWT token
    token_data = {
        "barber_id": str(barber.id),
        "email": barber.email,
        "name": barber.name,
        "tenant_id": str(barber.tenant_id)
    }
    access_token = Security.create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        barber={
            "id": str(barber.id),
            "name": barber.name,
            "email": barber.email,
            "tenant_id": str(barber.tenant_id)
        }
    )

@router.post("/logout")
def logout():
    """
    Logout del barbero.
    En cliente, simplemente descartar el token.
    """
    return {"message": "Sesión cerrada exitosamente"}

class FCMTokenRequest(BaseModel):
    fcm_token: str

from .bookings import get_current_barber

@router.post("/fcm-token")
def update_fcm_token(
    request: FCMTokenRequest,
    session: Session = Depends(get_session),
    current_barber: dict = Depends(get_current_barber)
):
    """
    Actualizar el FCM token del barbero logueado para recibir notificaciones push.
    """
    barber_id = current_barber["barber_id"]
    barber = session.exec(select(Barber).where(Barber.id == barber_id)).first()
    if not barber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbero no encontrado"
        )
    
    barber.fcm_token = request.fcm_token
    session.add(barber)
    session.commit()
    return {"message": "FCM token actualizado exitosamente"}
