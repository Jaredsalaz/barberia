import firebase_admin
from firebase_admin import credentials, messaging
import os
from sqlmodel import Session, select
from .config import settings
from ..schemas.barber import Barber

_firebase_initialized = False

def init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return True

    import json
    cred_val = settings.FIREBASE_CREDENTIALS
    if cred_val:
        cred_val = cred_val.strip().lstrip('\ufeff')

    # 1. Intentar cargar como JSON crudo desde variable de entorno
    if cred_val and cred_val.startswith("{"):
        try:
            cred_dict = json.loads(cred_val)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            print("[Firebase] Inicializado con éxito usando JSON de FIREBASE_CREDENTIALS.")
            return True
        except Exception as e:
            print(f"[Firebase] Error inicializando con JSON de FIREBASE_CREDENTIALS: {e}")

    # 2. Intentar cargar como ruta de archivo si es un archivo que existe
    if cred_val and os.path.exists(cred_val):
        try:
            cred = credentials.Certificate(cred_val)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            print(f"[Firebase] Inicializado con éxito usando archivo: {cred_val}")
            return True
        except Exception as e:
            print(f"[Firebase] Error inicializando con archivo '{cred_val}': {e}")

    # 3. Buscar posibles ubicaciones locales
    possible_paths = ["firebase-key.json", "api/firebase-key.json", "google-services.json"]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                cred = credentials.Certificate(path)
                firebase_admin.initialize_app(cred)
                _firebase_initialized = True
                print(f"[Firebase] Inicializado con éxito usando: {path}")
                return True
            except Exception as e:
                print(f"[Firebase] Error inicializando con archivo '{path}': {e}")

    # 4. Intentar cargar usando las credenciales predeterminadas de Google Cloud
    try:
        firebase_admin.initialize_app()
        _firebase_initialized = True
        print("[Firebase] Inicializado usando credenciales por defecto de aplicación.")
        return True
    except Exception as e:
        print(f"[Firebase] No se pudo inicializar Firebase (No credentials found): {e}")
            
    return False

def send_push_notification(fcm_token: str, title: str, body: str, data: dict = None) -> bool:
    """Envía una notificación push FCM a un dispositivo."""
    if not _firebase_initialized:
        if not init_firebase():
            print("[Firebase] Saltando envío de notificación push porque Firebase no está inicializado.")
            return False
            
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"[Firebase] Notificación push enviada con éxito: {response}")
        return True
    except Exception as e:
        print(f"[Firebase] Error enviando notificación push: {e}")
        return False

def notify_barber_by_id(barber_id: str, title: str, body: str, data: dict = None, db_session = None) -> bool:
    """Busca el FCM token del barbero en la base de datos y le envía una notificación push."""
    if not barber_id or barber_id == "None":
        return False
        
    if db_session is None:
        from .db import get_engine
        engine = get_engine()
        with Session(engine) as session:
            barber = session.exec(select(Barber).where(Barber.id == barber_id)).first()
            token = barber.fcm_token if barber else None
    else:
        barber = db_session.exec(select(Barber).where(Barber.id == barber_id)).first()
        token = barber.fcm_token if barber else None

    if not token:
        print(f"[Firebase] El barbero {barber_id} no tiene un FCM token registrado.")
        return False
        
    return send_push_notification(token, title, body, data)
