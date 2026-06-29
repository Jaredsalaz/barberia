from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime
import asyncio
from ..core.db import get_session
from ..core.security import Security
from ..schemas.booking import Booking
from ..schemas.barber import Barber
from ..schemas.client import Client
from ..schemas.service import Service

router = APIRouter(prefix="/api/v1", tags=["bookings"])

# Schemas
class UpdateBookingRequest(BaseModel):
    status: str  # pending, confirmed, completed, cancelled

class BookingDetailResponse(BaseModel):
    id: str
    appointment_date: datetime
    status: str
    client_name: str
    client_phone: str
    service_name: str
    service_price: float
    service_duration: int
    barber_name: str
    is_whatsapp_verified: bool

def get_current_barber(authorization: str = Header(None)):
    """Verificar JWT token y retornar datos del barbero"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado"
        )

    token = authorization.replace("Bearer ", "")
    payload = Security.decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    return payload

@router.get("/barbers/{barber_id}/bookings")
def get_barber_bookings(
    barber_id: str,
    status: str = None,
    date: str = None,
    session: Session = Depends(get_session),
    current_barber: dict = Depends(get_current_barber)
):
    """
    Obtener citas del barbero.
    Query params: ?status=pending,confirmed,completed&date=YYYY-MM-DD
    """
    # Verificar que el barbero solo acceda sus propias citas
    if current_barber["barber_id"] != barber_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver estas citas"
        )

    # Construir query
    query = select(Booking).where(Booking.barber_id == barber_id)

    # Filtrar por estado si se proporciona
    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.where(Booking.status.in_(statuses))

    # Filtrar por fecha si se proporciona
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.where(
                (Booking.appointment_date >= datetime.combine(target_date, datetime.min.time())) &
                (Booking.appointment_date <= datetime.combine(target_date, datetime.max.time()))
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )

    bookings = session.exec(query).all()

    # Enriquecer datos con información de cliente y servicio
    result = []
    for booking in bookings:
        client = session.exec(select(Client).where(Client.id == booking.client_id)).first()
        service = session.exec(select(Service).where(Service.id == booking.service_id)).first()

        result.append({
            "id": str(booking.id),
            "appointment_date": booking.appointment_date.isoformat(),
            "status": booking.status,
            "client_name": client.name if client else "Desconocido",
            "client_phone": client.phone if client else "",
            "service_name": service.name if service else "Servicio",
            "service_price": service.price if service else 0,
            "service_duration": service.duration_minutes if service else 0,
            "is_whatsapp_verified": booking.is_whatsapp_verified
        })

    return result

@router.get("/bookings/{booking_id}")
def get_booking_detail(
    booking_id: str,
    session: Session = Depends(get_session),
    current_barber: dict = Depends(get_current_barber)
):
    """Obtener detalle de una cita específica"""
    booking = session.exec(select(Booking).where(Booking.id == booking_id)).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada"
        )

    # Verificar que la cita pertenece al barbero actual
    if str(booking.barber_id) != current_barber["barber_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta cita"
        )

    client = session.exec(select(Client).where(Client.id == booking.client_id)).first()
    service = session.exec(select(Service).where(Service.id == booking.service_id)).first()
    barber = session.exec(select(Barber).where(Barber.id == booking.barber_id)).first()

    return {
        "id": str(booking.id),
        "appointment_date": booking.appointment_date.isoformat(),
        "status": booking.status,
        "client_name": client.name if client else "Desconocido",
        "client_phone": client.phone if client else "",
        "service_name": service.name if service else "Servicio",
        "service_price": service.price if service else 0,
        "service_duration": service.duration_minutes if service else 0,
        "barber_name": barber.name if barber else "Desconocido",
        "is_whatsapp_verified": booking.is_whatsapp_verified
    }

@router.patch("/bookings/{booking_id}")
def update_booking(
    booking_id: str,
    request: UpdateBookingRequest,
    session: Session = Depends(get_session),
    current_barber: dict = Depends(get_current_barber)
):
    """Actualizar estado de una cita"""
    booking = session.exec(select(Booking).where(Booking.id == booking_id)).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada"
        )

    # Verificar que la cita pertenece al barbero actual
    if str(booking.barber_id) != current_barber["barber_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta cita"
        )

    # Validar estado
    valid_statuses = ["pending", "confirmed", "completed", "cancelled"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Debe ser uno de: {', '.join(valid_statuses)}"
        )

    # Actualizar estado
    booking.status = request.status
    session.add(booking)
    session.commit()
    session.refresh(booking)

    client = session.exec(select(Client).where(Client.id == booking.client_id)).first()
    service = session.exec(select(Service).where(Service.id == booking.service_id)).first()

    # Notificar a través de WebSocket (import dinámico para evitar circular imports)
    try:
        from . import websocket as ws_module
        ws_module.notify_booking_updated_sync(
            str(booking.barber_id),
            str(booking.id),
            booking.status,
            booking.is_whatsapp_verified
        )
    except Exception as e:
        print(f"[Bookings] Error notificando WebSocket: {e}")

    return {
        "id": str(booking.id),
        "appointment_date": booking.appointment_date.isoformat(),
        "status": booking.status,
        "client_name": client.name if client else "Desconocido",
        "client_phone": client.phone if client else "",
        "service_name": service.name if service else "Servicio",
        "service_price": service.price if service else 0,
        "service_duration": service.duration_minutes if service else 0,
        "is_whatsapp_verified": booking.is_whatsapp_verified
    }
