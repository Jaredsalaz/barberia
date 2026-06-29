from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Query
from sqlmodel import Session, select
import json
import asyncio
from datetime import datetime
from ..core.db import get_engine
from ..core.security import Security
from ..schemas.booking import Booking
from ..schemas.barber import Barber
from ..schemas.client import Client
from ..schemas.service import Service

router = APIRouter(prefix="/api/v1", tags=["websocket"])

main_loop = None

def run_async(coro):
    """Ejecuta una corrutina de forma segura, usando el loop principal si está disponible"""
    if main_loop and main_loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, main_loop)
    else:
        try:
            return asyncio.run(coro)
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return asyncio.ensure_future(coro, loop=loop)
                else:
                    return loop.run_until_complete(coro)
            except Exception:
                new_loop = asyncio.new_event_loop()
                return new_loop.run_until_complete(coro)


# Diccionario para mantener conexiones WebSocket activas
# Estructura: { barber_id: [WebSocket, WebSocket, ...] }
active_connections: dict = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, barber_id: str, websocket: WebSocket):
        """Aceptar y registrar nueva conexión WebSocket"""
        await websocket.accept()
        if barber_id not in self.active_connections:
            self.active_connections[barber_id] = []
        self.active_connections[barber_id].append(websocket)
        print(f"[WebSocket] Barbero {barber_id} conectado. Total conexiones: {len(self.active_connections[barber_id])}")

    async def disconnect(self, barber_id: str, websocket: WebSocket):
        """Desconectar y remover conexión WebSocket"""
        if barber_id in self.active_connections:
            self.active_connections[barber_id].remove(websocket)
            if not self.active_connections[barber_id]:
                del self.active_connections[barber_id]
        print(f"[WebSocket] Barbero {barber_id} desconectado")

    async def broadcast_to_barber(self, barber_id: str, message: dict):
        """Enviar mensaje a todas las conexiones de un barbero"""
        if barber_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[barber_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"[WebSocket] Error enviando mensaje: {e}")
                    disconnected.append(connection)

            # Remover conexiones que fallaron
            for conn in disconnected:
                self.active_connections[barber_id].remove(conn)

manager = ConnectionManager()

@router.websocket("/ws/barber/{barber_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    barber_id: str,
    token: str = Query(None)
):
    """
    WebSocket para sincronización en tiempo real de citas.

    Conectar con: ws://localhost:8000/api/v1/ws/barber/{barber_id}?token={jwt_token}

    Eventos enviados:
    - booking_created: Nueva cita creada
    - booking_updated: Cita actualizada
    - booking_cancelled: Cita cancelada
    - bookings_list: Lista inicial de citas
    """

    # Validar token JWT
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token no proporcionado")
        return

    payload = Security.decode_token(token)
    if not payload or payload.get("barber_id") != barber_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido")
        return

    # Conectar
    await manager.connect(barber_id, websocket)

    # Enviar lista inicial de citas
    try:
        engine = get_engine()
        with Session(engine) as session:
            bookings = session.exec(
                select(Booking).where(Booking.barber_id == barber_id)
            ).all()

            bookings_list = []
            for booking in bookings:
                # Buscar información relacionada
                client = session.exec(select(Client).where(Client.id == booking.client_id)).first()
                service = session.exec(select(Service).where(Service.id == booking.service_id)).first()
                
                bookings_list.append({
                    "id": str(booking.id),
                    "appointment_date": booking.appointment_date.isoformat(),
                    "status": booking.status,
                    "client_name": client.name if client else "Cliente",
                    "client_phone": client.phone if client else "",
                    "service_name": service.name if service else "Servicio",
                    "service_price": service.price if service else 0,
                    "service_duration": service.duration_minutes if service else 0,
                    "is_whatsapp_verified": booking.is_whatsapp_verified
                })

            await websocket.send_json({
                "event": "bookings_list",
                "bookings": bookings_list
            })
    except Exception as e:
        print(f"[WebSocket] Error enviando lista inicial: {e}")

    # Mantener conexión abierta y escuchar mensajes
    try:
        while True:
            data = await websocket.receive_text()
            # El cliente puede enviar ping o solicitudes
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(barber_id, websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        await manager.disconnect(barber_id, websocket)

async def notify_booking_created(barber_id: str, booking_data: dict):
    """Notificar cuando se crea una nueva cita"""
    message = {
        "event": "booking_created",
        "booking": booking_data
    }
    await manager.broadcast_to_barber(barber_id, message)

async def notify_booking_updated(barber_id: str, booking_id: str, new_status: str, is_whatsapp_verified: bool = False):
    """Notificar cuando se actualiza el estado de una cita"""
    message = {
        "event": "booking_updated",
        "booking_id": booking_id,
        "status": new_status,
        "is_whatsapp_verified": is_whatsapp_verified
    }
    await manager.broadcast_to_barber(barber_id, message)

async def notify_booking_cancelled(barber_id: str, booking_id: str):
    """Notificar cuando se cancela una cita"""
    message = {
        "event": "booking_cancelled",
        "booking_id": booking_id
    }
    await manager.broadcast_to_barber(barber_id, message)

def notify_booking_created_sync(barber_id: str, booking_data: dict):
    run_async(notify_booking_created(barber_id, booking_data))

def notify_booking_updated_sync(barber_id: str, booking_id: str, new_status: str, is_whatsapp_verified: bool = False):
    run_async(notify_booking_updated(barber_id, booking_id, new_status, is_whatsapp_verified))

