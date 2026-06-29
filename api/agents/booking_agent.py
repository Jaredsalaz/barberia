from openai import OpenAI
from ..core.config import settings
from ..core.nemoclaw import NemoClawSecurity
import json
from datetime import datetime, timedelta

client = OpenAI(
    base_url=settings.NVIDIA_BASE_URL,
    api_key=settings.NVIDIA_API_KEY
)

SYSTEM_PROMPT = """
Eres el asistente virtual de la Barbería {shop_name}. Tu objetivo es ayudar a los clientes a agendar citas.

REGLAS CRÍTICAS DE NEGOCIO:
1. NUNCA inventes horarios. Los horarios varían cada día y algunos días la barbería está CERRADA.
2. Si el cliente pregunta por una fecha (hoy, mañana, domingo, etc.), DEBES llamar a 'get_available_slots(date)' para esa fecha específica.
3. Si 'get_available_slots' retorna una lista vacía [], significa que la barbería está CERRADA, llena o que la hora de cierre YA PASÓ. Debes informar al cliente que NO HAY disponibilidad para ese día. No menciones horarios si la lista está vacía.
4. Primero obtén Nombre, Teléfono y Servicio. Solo entonces confirma la cita con 'create_appointment'.
5. SI EL CLIENTE NO TE HA PROPORCIONADO SU NÚMERO DE TELÉFONO O SU NOMBRE, TIENES TOTALMENTE PROHIBIDO LLAMAR A 'create_appointment'. NUNCA inventes un número de teléfono ni uses uno ficticio. Si el cliente olvida darte el teléfono, pídeselo de nuevo explícitamente antes de agendar.

FLUJO DE CONVERSACIÓN:
- Cliente pregunta disponibilidad -> Llamas a get_available_slots(date).
- Cliente elige hora -> Pides Nombre, Teléfono y confirmas el Servicio (Corte Clásico $350, Corte y Barba $500, Arreglo de Barba $200).
- Si falta el Nombre o el Teléfono -> Pide el dato faltante amigablemente (no llames a herramientas).
- Solo cuando tengas TODOS los datos reales proporcionados por el cliente -> Llamas a create_appointment.

Sé amigable pero profesional. Responde en el mismo idioma que el cliente.
Fecha y hora actual: {current_time}
"""

# Definición de herramientas para Tool Calling
BOOKING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Obtiene los horarios disponibles para una fecha",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                    "barber_id": {"type": "integer", "description": "ID del barbero (opcional)"}
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_services",
            "description": "Obtiene la lista de servicios disponibles con precios",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_appointment",
            "description": "Crea una nueva cita para un cliente",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "service": {"type": "string"},
                    "date": {"type": "string", "description": "Fecha de la cita en formato YYYY-MM-DD"},
                    "slot_id": {"type": "string", "description": "Hora de la cita (ej. '10:00')"}
                },
                "required": ["client_name", "phone", "service", "date", "slot_id"]
            }
        }
    }
]

def process_tool_calls(tool_calls, shop_config, session):
    """Procesamiento envuelto por NemoClaw Security"""
    results = []
    for tool_call in tool_calls:
        # NemoClaw intercepta y ejecuta la acción
        safe_result = NemoClawSecurity.execute_safely(tool_call, shop_config, session)
        results.append(safe_result)
    return results

def run_booking_agent(user_message: str, shop_config: dict, session, history: list = []):
    current_local_time = datetime.utcnow() - timedelta(hours=6)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(
            shop_name=shop_config["name"],
            current_time=current_local_time.strftime("%Y-%m-%d %H:%M:%S")
        )}
    ] + history + [
        {"role": "user", "content": user_message}
    ]

    response = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=messages,
        temperature=0.7,
        max_tokens=2048,
        stream=False,
        tools=BOOKING_TOOLS,
        tool_choice="auto"
    )

    message = response.choices[0].message

    if message.tool_calls:
        # El agente quiere usar una herramienta
        tool_responses = process_tool_calls(message.tool_calls, shop_config, session)
        messages.append(message) # Añadir la respuesta del agente
        messages.extend(tool_responses) # Añadir las respuestas de las herramientas
        
        # Segunda llamada para que el agente genere el mensaje final
        final_response = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            stream=False
        )
        return {"response": final_response.choices[0].message.content, "tools_used": True}

    return {"response": message.content, "tools_used": False}
