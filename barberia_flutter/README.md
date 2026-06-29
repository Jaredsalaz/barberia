# Balam Barber - App Flutter para Barberos

App móvil para que los barberos de **Balam Barber** gestionen sus citas en tiempo real.

## Características

✅ **Login con autenticación JWT**  
✅ **Visualizar citas por estado** (Pendientes, Confirmadas, Completadas)  
✅ **Cambiar estado de citas** (Aceptar citas, Marcar como completadas)  
✅ **Sincronización en tiempo real** vía WebSocket  
✅ **Información detallada del cliente y servicio**  

## Instalación

### Requisitos
- Flutter SDK 3.0+
- Dart 3.0+
- Android Studio / Xcode (para emulador)

### Pasos

1. Navega a la carpeta del proyecto:
```bash
cd barberia_flutter
```

2. Instala dependencias:
```bash
flutter pub get
```

3. Configura la URL del servidor en `lib/constants/api_constants.dart`:
```dart
const String API_BASE_URL = 'http://your-server-ip:8000/api/v1';
const String WS_BASE_URL = 'ws://your-server-ip:8000/api/v1';
```

4. Ejecuta la app:
```bash
flutter run
```

## Credenciales de Prueba

| Email | Contraseña |
|-------|-----------|
| arthur@balam.com | password123 |
| thomas@balam.com | password456 |

## Estructura del Proyecto

```
lib/
├── main.dart                 # Entry point
├── screens/
│   ├── login_screen.dart     # Pantalla de login
│   ├── bookings_screen.dart  # Pantalla principal con tabs
│   └── booking_detail_screen.dart # Detalle de cita
├── models/
│   ├── auth_response.dart    # Respuesta de autenticación
│   └── booking.dart          # Modelo de cita
├── services/
│   ├── api_service.dart      # Cliente HTTP
│   └── websocket_service.dart # WebSocket
├── providers/
│   ├── auth_provider.dart    # State management de auth
│   └── bookings_provider.dart # State management de citas
└── constants/
    └── api_constants.dart    # URLs y configuración
```

## Flujo de Uso

1. **Login**: Ingresa con email y contraseña
2. **Ver Citas**: Accede a los 3 tabs (Pendientes, Confirmadas, Completadas)
3. **Aceptar Cita**: En tab "Pendientes", tap en una cita y presiona "Aceptar Cita"
4. **Completar Cita**: En tab "Confirmadas", presiona "Marcar como Completada"
5. **Sincronización**: Las actualizaciones llegan en tiempo real vía WebSocket

## Actualizaciones en Tiempo Real

La app se conecta a WebSocket para recibir eventos:
- **booking_created**: Nueva cita creada por agente de IA
- **booking_updated**: Cita actualizada por otro barbero
- **booking_cancelled**: Cita cancelada
- **bookings_list**: Lista inicial de citas al conectar

## Troubleshooting

### Error "No internet connection"
- Verifica que el servidor FastAPI esté corriendo
- Configura la IP correcta en `api_constants.dart`
- En emulador Android, usa `10.0.2.2` en lugar de `localhost`

### WebSocket no conecta
- Verifica el token JWT es válido
- Revisa los logs en `adb logcat` (Android) o Xcode (iOS)

### Citas no se actualizan
- Asegúrate de que WebSocket está conectado (ver mensaje en SnackBar)
- Intenta hacer "pull down" para refrescar manualmente
- Verifica los logs del servidor FastAPI

## Desarrollo

Para agregar nuevas funcionalidades:

1. **Agregar nueva pantalla**: Crea un nuevo archivo en `lib/screens/`
2. **Agregar modelo**: Crea en `lib/models/`
3. **Agregar API call**: Agrega método en `lib/services/api_service.dart`
4. **Manejar estado**: Usa `Provider` en los providers

## API Endpoints Utilizados

- `POST /auth/login` - Login
- `GET /barbers/{barber_id}/bookings` - Obtener citas
- `PATCH /bookings/{booking_id}` - Actualizar estado
- `WS /ws/barber/{barber_id}` - WebSocket

Ver documentación completa en `api/README.md`
