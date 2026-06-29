from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .core.config import settings
from .core.db import init_db
from .agents.booking_agent import run_booking_agent
from .routers import whatsapp, auth, bookings, websocket, tenants, registration

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(whatsapp.router, prefix=settings.API_V1_STR, tags=["whatsapp"])
app.include_router(auth.router, tags=["auth"])
app.include_router(bookings.router, tags=["bookings"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(tenants.router, tags=["tenants"])
app.include_router(registration.router, tags=["registration"])

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import asyncio
import httpx

async def init_openwa():
    """
    Inicializa la sesión y configura el webhook en OpenWA de manera resiliente.
    Se ejecuta en segundo plano para no bloquear el inicio del servidor API.
    """
    max_retries = 15
    retry_delay = 5 # segundos
    headers = {
        "X-API-Key": settings.OPENWA_API_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"[OpenWA Init] Iniciando intento de conexión con OpenWA en {settings.OPENWA_API_URL}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                # 1. Obtener todas las sesiones para resolver el ID UUID por nombre
                sessions_resp = await client.get(f"{settings.OPENWA_API_URL}/sessions", headers=headers, timeout=5.0)
                sessions_resp.raise_for_status()
                sessions = sessions_resp.json()
                
                session_id = None
                for s in sessions:
                    if s.get("name") == settings.OPENWA_SESSION_ID:
                        session_id = s.get("id")
                        break
                
                # 2. Si la sesión no existe por nombre, crearla
                if not session_id:
                    print(f"[OpenWA Init] Creando sesión '{settings.OPENWA_SESSION_ID}'...")
                    create_resp = await client.post(
                        f"{settings.OPENWA_API_URL}/sessions",
                        json={"name": settings.OPENWA_SESSION_ID},
                        headers=headers,
                        timeout=5.0
                    )
                    create_resp.raise_for_status()
                    session_id = create_resp.json().get("id")
                
                if not session_id:
                    raise Exception("No se pudo resolver o crear el ID de la sesión en OpenWA")
                
                # Guardar el UUID globalmente en la configuración
                settings.OPENWA_SESSION_UUID = session_id
                
                # 3. Iniciar la Sesión usando el UUID (session_id)
                session_url = f"{settings.OPENWA_API_URL}/sessions/{session_id}"
                print(f"[OpenWA Init] Asegurando inicio de sesión para '{settings.OPENWA_SESSION_ID}' (ID: {session_id})...")
                start_resp = await client.post(f"{session_url}/start", headers=headers, timeout=5.0)
                if start_resp.status_code not in (200, 201, 400):
                    start_resp.raise_for_status()
                
                # Give the engine extra time to generate the QR (e.g., 30 seconds)
                await asyncio.sleep(30)
                
                # 4. Verificar/Registrar el Webhook usando el UUID
                webhooks_resp = await client.get(f"{session_url}/webhooks", headers=headers, timeout=5.0)
                webhooks_resp.raise_for_status()
                webhooks = webhooks_resp.json()
                
                webhook_exists = any(w.get("url") == settings.WHATSAPP_WEBHOOK_URL for w in webhooks)
                if not webhook_exists:
                    print(f"[OpenWA Init] Registrando webhook para '{settings.WHATSAPP_WEBHOOK_URL}'...")
                    webhook_resp = await client.post(
                        f"{session_url}/webhooks",
                        json={
                            "url": settings.WHATSAPP_WEBHOOK_URL,
                            "events": ["message.received"]
                        },
                        headers=headers,
                        timeout=5.0
                    )
                    webhook_resp.raise_for_status()
                else:
                    print(f"[OpenWA Init] Webhook ya registrado para '{settings.WHATSAPP_WEBHOOK_URL}'")
                
                print("[OpenWA Init] Inicialización de OpenWA completada con éxito.")
                return
        except Exception as e:
            print(f"[OpenWA Init] Intento {attempt}/{max_retries} falló: {e}. Reintentando en {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            
    print("[OpenWA Init] ADVERTENCIA: No se pudo inicializar OpenWA después de varios intentos. Deberá configurarse manualmente.")

@app.on_event("startup")
async def on_startup():
    from .routers import websocket as ws_module
    ws_module.main_loop = asyncio.get_running_loop()
    init_db()
    # Iniciar configuración de OpenWA en segundo plano
    asyncio.create_task(init_openwa())
    # Iniciar programador de notificaciones push en segundo plano
    asyncio.create_task(daily_notification_scheduler())

class AgentRequest(BaseModel):
    message: str
    shop_id: str
    shop_name: str

# Diccionario temporal en memoria para guardar el historial de cada cliente
# En producción, esto debería ir a Redis o una base de datos
chat_sessions = {}

from fastapi import Depends
from sqlmodel import Session
from .core.db import get_session

@app.post(f"{settings.API_V1_STR}/chat")
def chat_with_agent(request: AgentRequest, session: Session = Depends(get_session)):
    try:
        from .schemas.tenant import Tenant
        from sqlmodel import select
        import uuid
        
        try:
            shop_uuid = uuid.UUID(request.shop_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="El ID de la barbería no es válido.")
            
        tenant = session.exec(
            select(Tenant).where(
                Tenant.id == shop_uuid,
                Tenant.is_active == True,
                (Tenant.subscription_expires_at == None) | (Tenant.subscription_expires_at >= datetime.utcnow())
            )
        ).first()
        
        if not tenant:
            raise HTTPException(
                status_code=403,
                detail="Esta barbería no se encuentra activa o su suscripción mensual ha vencido."
            )
            
        shop_config = {"name": request.shop_name}
        
        # Recuperar o inicializar el historial de esta sesión
        # Usamos request.message temporalmente como llave (idealmente sería un user_id o session_id)
        # Para pruebas, guardaremos todo en un solo historial global de la tienda para que funcione el demo
        session_id = str(request.shop_id) 
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
            
        response_data = run_booking_agent(
            user_message=request.message,
            shop_config=shop_config,
            session=session,
            history=chat_sessions[session_id]
        )
        
        # Guardar la interacción en el historial
        chat_sessions[session_id].append({"role": "user", "content": request.message})
        chat_sessions[session_id].append({"role": "assistant", "content": response_data["response"]})
        
        return response_data
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from datetime import datetime, timedelta
from sqlmodel import Session, select
from .schemas.barber import Barber
from .core.notifications import send_push_notification
from .core.db import get_engine

def send_daily_reminder_to_all_barbers():
    engine = get_engine()
    with Session(engine) as session:
        barbers = session.exec(select(Barber).where(Barber.fcm_token != None)).all()
        if not barbers:
            print("[Firebase Scheduler] No hay barberos con FCM token registrados para notificar.")
            return
            
        print(f"[Firebase Scheduler] Enviando recordatorio diario a {len(barbers)} barberos...")
        for barber in barbers:
            title = "📅 ¡Entra a ver tus citas!"
            body = f"Hola {barber.name}, recuerda revisar tu agenda para hoy y verificar tus próximas citas. ¡Que tengas un excelente día! 💈"
            send_push_notification(barber.fcm_token, title, body)

async def daily_notification_scheduler():
    """
    Tarea en segundo plano que revisa la hora cada 30 segundos.
    Envía una notificación push diaria a las 2:45 PM (14:45) hora México Centro.
    """
    print("[Firebase Scheduler] Iniciando programador de notificaciones push...")
    last_sent_date = None
    
    while True:
        try:
            # Hora local de México Centro (UTC - 6)
            now_mex = datetime.utcnow() - timedelta(hours=6)
            
            # Verificar si son las 2:52 PM (14:52)
            if now_mex.hour == 14 and now_mex.minute == 52:
                current_date = now_mex.date()
                if last_sent_date != current_date:
                    print(f"[Firebase Scheduler] ¡Es hora (14:45)! Ejecutando notificaciones diarias para la fecha {current_date}...")
                    try:
                        send_daily_reminder_to_all_barbers()
                        last_sent_date = current_date
                    except Exception as e:
                        print(f"[Firebase Scheduler] Error al enviar recordatorios: {e}")
            
            # Esperar 30 segundos
            await asyncio.sleep(30)
        except Exception as e:
            print(f"[Firebase Scheduler] Error en el bucle principal: {e}")
            await asyncio.sleep(60)

@app.get(f"{settings.API_V1_STR}/test-push")
@app.post(f"{settings.API_V1_STR}/test-push")
def test_push_notifications():
    """
    Endpoint de prueba para disparar la notificación de recordatorio diario a todos los barberos inmediatamente.
    """
    try:
        send_daily_reminder_to_all_barbers()
        return {"status": "success", "message": "Notificaciones de prueba enviadas exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Bienvenido a Balam SaaS API"}
