from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlmodel import Session, select
import httpx
import logging
import asyncio
from ..core.config import settings
from ..core.db import get_session
from ..core.nemoclaw import normalize_to_10_digits
from ..schemas.client import Client
from ..schemas.booking import Booking
from ..schemas.service import Service
from ..schemas.barber import Barber
from ..core.notifications import notify_barber_by_id

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db_session: Session = Depends(get_session)
):
    """
    Recibe eventos en formato JSON desde OpenWA WhatsApp API Gateway.
    Verifica si el número remitente está registrado en la base de datos (filtro de contactos).
    Si está registrado, gestiona la confirmación o cancelación de citas pendientes.
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[WhatsApp Webhook] Error al decodificar JSON: {e}")
        raise HTTPException(status_code=400, detail="Cuerpo de solicitud inválido")

    event = payload.get("event")
    
    # 1. Ignorar eventos que no sean de nuevos mensajes recibidos
    if event != "message.received":
        logger.debug(f"[WhatsApp Webhook] Evento ignorado: {event}")
        return {"status": "ignored", "event": event}

    data = payload.get("data", {})
    from_me = data.get("fromMe", False)

    # 2. Ignorar mensajes salientes enviados por el propio bot (para evitar bucles infinitos)
    if from_me:
        logger.debug("[WhatsApp Webhook] Mensaje saliente de la cuenta del bot ignorado.")
        return {"status": "ignored", "reason": "outbound_message"}

    # 3. Extraer remitente JID (ej: '5219661086709@c.us') y cuerpo
    sender_jid = data.get("from") or data.get("sender", {}).get("id")
    body = data.get("body") or data.get("text", "")

    if not sender_jid:
        logger.warning("[WhatsApp Webhook] Remitente no especificado en el payload.")
        return {"status": "error", "message": "Falta el remitente"}

    # 4. Normalizar el número telefónico del remitente a 10 dígitos
    sender_normalized = normalize_to_10_digits(sender_jid)
    logger.info(f"[WhatsApp Webhook] Mensaje de {sender_jid} (Normalizado: {sender_normalized}): '{body}'")

    # 5. SEGURIDAD: Buscar si el cliente existe en la base de datos (Whitelisting / Lista blanca)
    clients = db_session.exec(select(Client)).all()
    client = None

    # Intentar buscar de forma directa
    for c in clients:
        c_norm = normalize_to_10_digits(c.phone)
        if c_norm == sender_normalized:
            client = c
            break

    # Si no se encuentra y el JID es un LID o si no hay coincidencia, intentamos resolver el JID real de OpenWA
    if not client:
        session_id = payload.get("sessionId") or settings.OPENWA_SESSION_UUID or settings.OPENWA_SESSION_ID
        if session_id:
            logger.info(f"[WhatsApp Webhook] Cliente no encontrado de forma directa para {sender_jid}. Resolviendo JID en OpenWA...")
            contact_url = f"{settings.OPENWA_API_URL}/sessions/{session_id}/contacts/{sender_jid}"
            headers = {
                "X-API-Key": settings.OPENWA_API_KEY,
                "Content-Type": "application/json"
            }
            try:
                async with httpx.AsyncClient() as client_http:
                    resp = await client_http.get(contact_url, headers=headers, timeout=5.0)
                    if resp.status_code == 200:
                        contact_data = resp.json()
                        real_id = contact_data.get("id")
                        if real_id and real_id != sender_jid:
                            new_normalized = normalize_to_10_digits(real_id)
                            logger.info(f"[WhatsApp Webhook] JID {sender_jid} resuelto a {real_id} (Nuevo normalizado: {new_normalized})")
                            for c in clients:
                                if normalize_to_10_digits(c.phone) == new_normalized:
                                    client = c
                                    sender_normalized = new_normalized
                                    break
            except Exception as ex:
                logger.error(f"[WhatsApp Webhook] Error resolviendo JID {sender_jid}: {ex}")

    if not client:
        # Bloquear respuesta a contactos externos no registrados en la barbería
        logger.info(f"[WhatsApp Webhook] Mensaje ignorado de número no registrado: {sender_jid}")
        return {"status": "ignored", "reason": "unregistered_contact"}

    # 6. Buscar la cita más reciente con estatus 'pending' de este cliente
    booking = db_session.exec(
        select(Booking)
        .where(Booking.client_id == client.id, Booking.status == "pending")
        .order_by(Booking.created_at.desc())
    ).first()

    # Normalizar respuesta del cliente (quitar acentos, espacios y convertir a minúsculas)
    body_clean = body.strip().lower()
    for active, replacement in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        body_clean = body_clean.replace(active, replacement)

    # Palabras clave de confirmación y cancelación
    keywords_confirm = {"si", "si", "confirmar", "confirmado", "confirmo", "ok", "listo", "yes", "va", "aceptar", "acepto"}
    keywords_cancel = {"no", "cancelar", "cancela", "cancelado", "anular", "no ire", "rechazar"}

    words = body_clean.split()
    is_confirm = any(word in keywords_confirm for word in words) or body_clean in keywords_confirm
    is_cancel = any(word in keywords_cancel for word in words) or body_clean in keywords_cancel

    agent_reply = ""

    if is_confirm:
        if booking:
            # Confirmar la cita
            booking.status = "confirmed"
            booking.is_whatsapp_verified = True
            db_session.add(booking)
            db_session.commit()
            db_session.refresh(booking)
            
            service = db_session.exec(select(Service).where(Service.id == booking.service_id)).first()
            barber = db_session.exec(select(Barber).where(Barber.id == booking.barber_id)).first()
            
            service_name = service.name if service else "Servicio"
            barber_name = barber.name if barber else "Cualquiera"
            formatted_date = booking.appointment_date.strftime("%d/%m/%Y")
            formatted_time = booking.appointment_date.strftime("%H:%M")

            agent_reply = (
                f"💈 *BALAM BARBER* 💈\n"
                f"----------------------------------\n"
                f"¡Muchas gracias, *{client.name}*! 🌟\n\n"
                f"Tu cita ha sido *CONFIRMADA* con éxito.\n\n"
                f"📅 *Detalles de tu cita:*\n"
                f"✂️ *Servicio:* {service_name}\n"
                f"📅 *Fecha:* {formatted_date}\n"
                f"⏰ *Hora:* {formatted_time} hrs\n"
                f"👤 *Barbero:* {barber_name}\n\n"
                f"📍 *Ubicación:* Tuxtla Gutiérrez\n"
                f"💈 ¡Te esperamos para brindarte la mejor experiencia! 🔥"
            )
            
            # Notificar en tiempo real a la app del barbero mediante WebSockets
            try:
                from . import websocket as ws_module
                await ws_module.notify_booking_updated(
                    str(booking.barber_id),
                    str(booking.id),
                    booking.status,
                    booking.is_whatsapp_verified
                )
            except Exception as ws_err:
                logger.error(f"[WebSocket] Error notificando confirmación de cita: {ws_err}")

            # Enviar notificación push
            try:
                notify_barber_by_id(
                    barber_id=str(booking.barber_id),
                    title="Cita Confirmada por WhatsApp 💈",
                    body=f"El cliente {client.name} ha confirmado su cita para {service_name}.",
                    data={"booking_id": str(booking.id), "status": booking.status},
                    db_session=db_session
                )
            except Exception as push_err:
                logger.error(f"[Push] Error enviando notificación push: {push_err}")
        else:
            agent_reply = f"Hola {client.name}, no encontramos ninguna cita pendiente para confirmar. Si deseas agendar una nueva cita, por favor visita nuestro sitio web."

    elif is_cancel:
        if booking:
            # Cancelar la cita
            booking.status = "cancelled"
            db_session.add(booking)
            db_session.commit()
            db_session.refresh(booking)
            
            agent_reply = (
                f"💈 *BALAM BARBER* 💈\n"
                f"----------------------------------\n"
                f"Entendido, *{client.name}*.\n\n"
                f"Tu cita ha sido *CANCELADA* con éxito. ❌\n\n"
                f"Si deseas agendar en otro momento, puedes hacerlo de nuevo a través de nuestro asistente en la web.\n"
                f"¡Que tengas un excelente día! 👋"
            )
            
            # Notificar en tiempo real a la app del barbero mediante WebSockets
            try:
                from . import websocket as ws_module
                await ws_module.notify_booking_updated(
                    str(booking.barber_id),
                    str(booking.id),
                    booking.status,
                    booking.is_whatsapp_verified
                )
            except Exception as ws_err:
                logger.error(f"[WebSocket] Error notificando cancelación de cita: {ws_err}")

            # Enviar notificación push
            try:
                notify_barber_by_id(
                    barber_id=str(booking.barber_id),
                    title="Cita Cancelada por WhatsApp ❌",
                    body=f"El cliente {client.name} ha cancelado su cita.",
                    data={"booking_id": str(booking.id), "status": booking.status},
                    db_session=db_session
                )
            except Exception as push_err:
                logger.error(f"[Push] Error enviando notificación push: {push_err}")
        else:
            agent_reply = f"Hola {client.name}, no encontramos ninguna cita pendiente para cancelar."

    else:
        # Respuesta por defecto / Instrucciones si no envía palabras clave
        if booking:
            formatted_date = booking.appointment_date.strftime("%d/%m a las %H:%M")
            agent_reply = (
                f"Hola {client.name}. Tienes una cita pendiente para el {formatted_date}.\n\n"
                f"Por favor, responde únicamente con la palabra *'Confirmar'* para asegurar tu asistencia, "
                f"o *'Cancelar'* si deseas anularla."
            )
        else:
            agent_reply = f"Hola {client.name}. Para agendar una nueva cita en Balam Barber, por favor visita nuestro sitio web."

    # 7. Responder al cliente usando la API REST de OpenWA
    session_id = payload.get("sessionId") or settings.OPENWA_SESSION_ID
    send_url = f"{settings.OPENWA_API_URL}/sessions/{session_id}/messages/send-text"
    headers = {
        "X-API-Key": settings.OPENWA_API_KEY,
        "Content-Type": "application/json"
    }
    payload_out = {
        "chatId": sender_jid,
        "text": agent_reply
    }

    try:
        async with httpx.AsyncClient() as client_http:
            response = await client_http.post(send_url, json=payload_out, headers=headers, timeout=10.0)
            response.raise_for_status()
            logger.info(f"[WhatsApp Webhook] Respuesta enviada con éxito a {sender_jid}")
    except httpx.HTTPStatusError as e:
        logger.error(f"[WhatsApp Webhook] Error HTTP al responder vía OpenWA ({send_url}): {e.response.status_code} - {e.response.text}")
        return {"status": "error", "message": "Error al enviar mensaje vía OpenWA"}
    except Exception as e:
        logger.error(f"[WhatsApp Webhook] Error de conexión al responder vía OpenWA: {e}")
        return {"status": "error", "message": "Error de conexión con OpenWA"}

    return {"status": "success", "recipient": sender_jid}

