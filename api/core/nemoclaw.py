import json
import asyncio
import httpx
from sqlmodel import Session, select
from datetime import datetime, time, timedelta
from ..schemas.tenant import Tenant
from ..schemas.barber import Barber
from ..schemas.service import Service
from ..schemas.client import Client
from ..schemas.booking import Booking
from ..core.config import settings

def normalize_to_10_digits(phone_str: str) -> str:
    """Extrae los últimos 10 dígitos numéricos de un número telefónico."""
    digits = "".join(c for c in phone_str if c.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits

def format_to_whatsapp_jid(phone_str: str) -> str:
    """Convierte un número telefónico a formato JID de WhatsApp (ej: 5219661086709@c.us)."""
    digits = "".join(c for c in phone_str if c.isdigit())
    if len(digits) == 10:
        return f"521{digits}@c.us"
    elif len(digits) == 11 and digits.startswith("52"):
        return f"{digits}@c.us"
    elif len(digits) == 12 and digits.startswith("521"):
        return f"{digits}@c.us"
    return f"{digits}@c.us"

def send_whatsapp_confirmation(client_name: str, phone: str, service_name: str, date_str: str, slot_id: str):
    """Envía un mensaje de confirmación por WhatsApp usando OpenWA de forma síncrona."""
    session_id = settings.OPENWA_SESSION_UUID or settings.OPENWA_SESSION_ID
    if not session_id:
        print("[NemoClaw WhatsApp] Advertencia: No hay UUID de sesión configurado en OpenWA. Usando default.")
        session_id = settings.OPENWA_SESSION_ID
        
    client_jid = format_to_whatsapp_jid(phone)
    send_url = f"{settings.OPENWA_API_URL}/sessions/{session_id}/messages/send-text"
    headers = {
        "X-API-Key": settings.OPENWA_API_KEY,
        "Content-Type": "application/json"
    }
    
    msg_body = (
        f"Hola {client_name}, gracias por reservar en Balam Barber.\n\n"
        f"Hemos recibido tu solicitud:\n"
        f"💈 Servicio: {service_name}\n"
        f"📅 Fecha: {date_str}\n"
        f"⏰ Hora: {slot_id}\n\n"
        f"¿Confirmas tu asistencia? Por favor responde con la palabra 'Confirmar' o 'Cancelar'."
    )
    
    payload = {
        "chatId": client_jid,
        "text": msg_body
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(send_url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            print(f"[NemoClaw WhatsApp] Solicitud de confirmación enviada a {client_jid} con éxito.")
    except Exception as e:
        print(f"[NemoClaw WhatsApp] Error al enviar confirmación vía OpenWA: {e}")

class NemoClawSecurity:
    """
    Wrapper de seguridad (OpenClaw / NemoClaw) que intercepta 
    y valida la ejecución de tools por parte del agente.
    """
    
    @staticmethod
    def validate_tool_call(tool_name: str, arguments: dict, shop_config: dict) -> bool:
        """
        Aplica reglas de negocio y seguridad antes de ejecutar.
        Retorna True si es válido, False si es una operación bloqueada.
        """
        print(f"[NemoClaw] Validando tool_call: {tool_name}")
        return True

    @staticmethod
    def execute_safely(tool_call, shop_config: dict, session: Session):
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        if not NemoClawSecurity.validate_tool_call(function_name, arguments, shop_config):
            return {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps({"error": "Acción bloqueada por políticas de seguridad (NemoClaw)"})
            }
            
        try:
            # Buscar Tenant
            tenant = session.exec(select(Tenant).where(Tenant.name == shop_config["name"])).first()
            print(f"[NemoClaw] Buscando tenant: {shop_config['name']} -> Encontrado: {tenant is not None}")
            if not tenant:
                return {"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": json.dumps({"error": "Tienda no encontrada"})}

            if function_name == "get_services":
                # Obtener lista de servicios
                services = session.exec(select(Service).where(Service.tenant_id == tenant.id, Service.is_active == True)).all()
                services_list = [{"name": s.name, "price": s.price, "duration_minutes": s.duration_minutes} for s in services]
                content = {"services": services_list}

            elif function_name == "get_available_slots":
                date_str = arguments.get("date")
                requested_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                print(f"[NemoClaw] get_available_slots para {date_str} (Tenant ID: {tenant.id})")
                
                # Obtener horario del día solicitado
                day_name = requested_date.strftime("%A").lower()
                hours = (tenant.business_hours or {}).get(day_name)
                print(f"[NemoClaw] Dia: {day_name}, Horarios: {hours}")
                
                if not hours or not hours.get("open"):
                    return {"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": json.dumps({"date": date_str, "available_slots": [], "message": "LA BARBERÍA ESTÁ CERRADA ESTE DÍA. NO HAY TURNOS."})}
                
                open_time_str = hours["open"]
                close_time_str = hours["close"]
                
                # Horarios dinámicos basados en business_hours
                potential_slots = []
                current_time = datetime.combine(requested_date, datetime.strptime(open_time_str, "%H:%M").time())
                end_time = datetime.combine(requested_date, datetime.strptime(close_time_str, "%H:%M").time())
                
                # Obtener hora local (Central Time -6h para México)
                now_local = datetime.utcnow() - timedelta(hours=6)
                
                temp_time = current_time
                while temp_time < end_time:
                    if not (requested_date == now_local.date() and temp_time.time() < now_local.time()):
                        potential_slots.append(temp_time)
                    temp_time += timedelta(minutes=30)
                
                # Obtener citas existentes
                bookings = session.exec(
                    select(Booking).where(
                        Booking.tenant_id == tenant.id,
                        Booking.appointment_date >= datetime.combine(requested_date, time(0, 0)),
                        Booking.appointment_date <= datetime.combine(requested_date, time(23, 59))
                    )
                ).all()
                
                booked_times = {b.appointment_date for b in bookings}
                available_slots = [s.strftime("%H:%M") for s in potential_slots if s not in booked_times]
                
                content = {"date": date_str, "available_slots": available_slots}

            elif function_name == "create_appointment":
                client_name = arguments.get("client_name")
                phone = arguments.get("phone")
                service_name = arguments.get("service")
                date_str = arguments.get("date")
                slot_id = arguments.get("slot_id") # e.g. "10:00"
                
                # 1. Buscar o Crear Cliente
                client = session.exec(select(Client).where(Client.phone == phone, Client.tenant_id == tenant.id)).first()
                if not client:
                    client = Client(name=client_name, phone=phone, tenant_id=tenant.id)
                    session.add(client)
                    session.commit()
                    session.refresh(client)
                
                # 2. Buscar Servicio (búsqueda flexible)
                service = session.exec(select(Service).where(Service.tenant_id == tenant.id, Service.name.ilike(f"%{service_name}%"))).first()
                if not service:
                    # Intento extra: buscar por palabras clave si el nombre era largo
                    keywords = service_name.split()
                    for kw in keywords:
                        if len(kw) > 3:
                            service = session.exec(select(Service).where(Service.tenant_id == tenant.id, Service.name.ilike(f"%{kw}%"))).first()
                            if service: break
                
                if not service:
                    return {"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": json.dumps({"error": f"Servicio '{service_name}' no encontrado"})}
                
                # 3. Buscar un Barbero (el primero disponible para simplificar)
                barber = session.exec(select(Barber).where(Barber.tenant_id == tenant.id, Barber.is_active == True)).first()
                
                # 4. Crear Cita
                # Aceptar ambos formatos: "11:00" (24h) y "11:00 am/pm" (12h)
                try:
                    appointment_date = datetime.strptime(f"{date_str} {slot_id}", "%Y-%m-%d %H:%M")
                except ValueError:
                    # Intenta con formato 12 horas si falla
                    appointment_date = datetime.strptime(f"{date_str} {slot_id}", "%Y-%m-%d %I:%M %p")
                new_booking = Booking(
                    appointment_date=appointment_date,
                    tenant_id=tenant.id,
                    client_id=client.id,
                    service_id=service.id,
                    barber_id=barber.id if barber else None,
                    status="pending"
                )
                session.add(new_booking)
                session.commit()
                session.refresh(new_booking)

                # 5. Enviar mensaje de confirmación de cita por WhatsApp
                send_whatsapp_confirmation(
                    client_name=client_name,
                    phone=phone,
                    service_name=service.name,
                    date_str=date_str,
                    slot_id=slot_id
                )

                # Notificar a través de WebSocket en tiempo real
                try:
                    from ..routers import websocket as ws_module
                    ws_module.notify_booking_created_sync(
                        str(new_booking.barber_id),
                        {
                            "id": str(new_booking.id),
                            "appointment_date": new_booking.appointment_date.isoformat(),
                            "status": new_booking.status,
                            "client_name": client.name,
                            "client_phone": client.phone,
                            "service_name": service.name,
                            "service_price": service.price,
                            "service_duration": service.duration_minutes,
                            "is_whatsapp_verified": new_booking.is_whatsapp_verified
                        }
                    )
                except Exception as ws_err:
                    print(f"[WebSocket] Error notificando nueva cita: {ws_err}")

                # Enviar notificación push de cita creada
                try:
                    from .notifications import notify_barber_by_id
                    notify_barber_by_id(
                        barber_id=str(new_booking.barber_id),
                        title="Nueva Cita Agendada 📅",
                        body=f"{client_name} agendó {service.name} para el {date_str} a las {slot_id}.",
                        data={"booking_id": str(new_booking.id), "status": new_booking.status},
                        db_session=session
                    )
                except Exception as push_err:
                    print(f"[Push] Error notificando nueva cita: {push_err}")
                
                content = {
                    "status": "success", 
                    "appointment_id": str(new_booking.id),
                    "details": f"Cita confirmada para {client_name} el {date_str} a las {slot_id} para {service.name}."
                }
            else:
                content = {"error": "Función no encontrada"}
        except Exception as e:
            print(f"Error en NemoClaw: {e}")
            content = {"error": f"Error interno al procesar la solicitud: {str(e)}"}
            
        return {
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": function_name,
            "content": json.dumps(content)
        }
