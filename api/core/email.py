import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Envía un correo con el código OTP para la verificación del registro de barbería.
    Utiliza el servidor SMTP de Gmail con las credenciales configuradas.
    """
    if not settings.GMAIL_USER or not settings.GMAIL_PASSWORD:
        print("[Email] Error: GMAIL_USER o GMAIL_PASSWORD no están configurados.")
        return False

    sender_email = settings.GMAIL_USER
    receiver_email = to_email
    subject = "Código de Verificación - Balam Barber Platform"

    # Plantilla HTML con diseño oscuro premium
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verifica tu Email</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                background-color: #04060f;
                color: #dbe4ff;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: linear-gradient(165deg, #0d1629, #0e2345);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 42px rgba(1, 4, 20, 0.6);
            }}
            .header {{
                background: linear-gradient(90deg, #7c3aed, #2563eb);
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: 1px;
                color: #ffffff;
            }}
            .content {{
                padding: 40px 30px;
                text-align: center;
            }}
            .content p {{
                font-size: 16px;
                line-height: 1.6;
                color: #9eb0d6;
                margin-bottom: 30px;
            }}
            .otp-box {{
                display: inline-block;
                background: rgba(4, 6, 15, 0.7);
                border: 1px solid #7c3aed;
                color: #ffffff;
                font-size: 36px;
                font-weight: 700;
                letter-spacing: 8px;
                padding: 15px 30px;
                border-radius: 12px;
                margin-bottom: 30px;
                box-shadow: 0 0 15px rgba(124, 58, 237, 0.4);
            }}
            .footer {{
                background-color: rgba(4, 6, 15, 0.4);
                padding: 20px;
                text-align: center;
                border-top: 1px solid rgba(148, 163, 184, 0.1);
                font-size: 12px;
                color: #64748b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Balam Platform SaaS</h1>
            </div>
            <div class="content">
                <p>¡Hola! Estás a un paso de registrar tu barbería y formar parte de la plataforma inteligente más pro. Por favor usa el siguiente código de verificación de un solo uso (OTP) para continuar con tu proceso de pago y registro:</p>
                <div class="otp-box">{otp}</div>
                <p style="font-size: 13px; color: #64748b;">Este código vencerá en 10 minutos. Si no solicitaste este registro, puedes ignorar este correo con seguridad.</p>
            </div>
            <div class="footer">
                &copy; 2026 Balam Barber Platform. Todos los derechos reservados.
            </div>
        </div>
    </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"Balam Platform <{sender_email}>"
    message["To"] = receiver_email

    # Agregar versión de texto plano como fallback
    text_content = f"Tu código de verificación de Balam Barber es: {otp}\nEste código expira en 10 minutos."
    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    message.attach(part1)
    message.attach(part2)

    try:
        # Conectar a Gmail SMTP en el puerto 587 con TLS
        print(f"[Email] Conectando a smtp.gmail.com:587 para enviar OTP a {to_email}...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, settings.GMAIL_PASSWORD)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        print("[Email] Correo electrónico OTP enviado con éxito.")
        return True
    except Exception as e:
        print(f"[Email] Error al enviar correo electrónico: {e}")
        return False

def send_payment_receipt_email(to_email: str, owner_name: str, shop_name: str, plan_name: str, amount: float, expires_at: datetime) -> bool:
    """
    Envía un correo electrónico con el comprobante de pago de la suscripción y
    la fecha de vencimiento de la misma.
    """
    if not settings.GMAIL_USER or not settings.GMAIL_PASSWORD:
        print("[Email] Error: GMAIL_USER o GMAIL_PASSWORD no están configurados.")
        return False

    sender_email = settings.GMAIL_USER
    receiver_email = to_email
    subject = f"Comprobante de Pago - Balam Barber Platform (Plan {plan_name.upper()})"
    
    expires_str = expires_at.strftime("%d/%m/%Y a las %H:%M UTC")

    # Plantilla HTML con diseño oscuro premium para el recibo
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Comprobante de Pago</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                background-color: #04060f;
                color: #dbe4ff;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: linear-gradient(165deg, #0d1629, #0e2345);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 42px rgba(1, 4, 20, 0.6);
            }}
            .header {{
                background: linear-gradient(90deg, #7c3aed, #2563eb);
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: 1px;
                color: #ffffff;
            }}
            .content {{
                padding: 40px 30px;
                text-align: left;
            }}
            .content h2 {{
                color: #ffffff;
                font-size: 20px;
                margin-top: 0;
                margin-bottom: 20px;
                border-bottom: 1px solid rgba(148, 163, 184, 0.2);
                padding-bottom: 10px;
            }}
            .content p {{
                font-size: 15px;
                line-height: 1.6;
                color: #9eb0d6;
                margin-bottom: 16px;
            }}
            .receipt-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 25px 0;
            }}
            .receipt-table th, .receipt-table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid rgba(148, 163, 184, 0.1);
            }}
            .receipt-table th {{
                color: #ffffff;
                font-weight: 600;
            }}
            .receipt-table td {{
                color: #9eb0d6;
            }}
            .total-row {{
                font-weight: 700;
                font-size: 16px;
            }}
            .total-row td {{
                color: #60a5fa !important;
                border-top: 2px solid rgba(148, 163, 184, 0.2);
            }}
            .alert-box {{
                background: rgba(124, 58, 237, 0.1);
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 12px;
                padding: 16px;
                margin-top: 25px;
                text-align: center;
            }}
            .alert-box strong {{
                color: #ffffff;
                display: block;
                margin-bottom: 4px;
                font-size: 14px;
            }}
            .alert-box span {{
                color: #38bdf8;
                font-size: 16px;
                font-weight: 700;
            }}
            .footer {{
                background-color: rgba(4, 6, 15, 0.4);
                padding: 20px;
                text-align: center;
                border-top: 1px solid rgba(148, 163, 184, 0.1);
                font-size: 12px;
                color: #64748b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Balam Platform SaaS</h1>
            </div>
            <div class="content">
                <h2>Confirmación de Pago y Suscripción</h2>
                <p>Hola <strong>{owner_name}</strong>,</p>
                <p>¡Gracias por unirte a Balam Platform! Hemos recibido tu pago y tu barbería <strong>{shop_name}</strong> ha sido dada de alta exitosamente en nuestro directorio de servicios.</p>
                
                <table class="receipt-table">
                    <thead>
                        <tr>
                            <th>Concepto</th>
                            <th>Plan</th>
                            <th>Monto</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Registro de Barbería (Suscripción Mensual)</td>
                            <td>Plan {plan_name.capitalize()}</td>
                            <td>${amount:.2f} MXN</td>
                        </tr>
                        <tr class="total-row">
                            <td colspan="2">Total Pagado:</td>
                            <td>${amount:.2f} MXN</td>
                        </tr>
                    </tbody>
                </table>

                <div class="alert-box">
                    <strong>TU SUSCRIPCIÓN ESTÁ ACTIVA HASTA:</strong>
                    <span>{expires_str}</span>
                </div>

                <p style="margin-top: 25px; font-size: 13px; color: #64748b;">
                    Recuerda que para mantener tu listado activo, tu suscripción debe renovarse mensualmente. Al terminar este periodo, si no se registra el siguiente pago mensual, tu barbería se ocultará automáticamente del directorio y mapa.
                </p>
            </div>
            <div class="footer">
                &copy; 2026 Balam Barber Platform. Todos los derechos reservados.
            </div>
        </div>
    </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"Balam Platform <{sender_email}>"
    message["To"] = receiver_email

    text_content = f"¡Gracias por tu pago!\nBarbería: {shop_name}\nPlan: {plan_name.upper()}\nMonto: ${amount:.2f} MXN\nSuscripción activa hasta: {expires_str}"
    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    message.attach(part1)
    message.attach(part2)

    try:
        print(f"[Email] Conectando a smtp.gmail.com:587 para enviar comprobante a {to_email}...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, settings.GMAIL_PASSWORD)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        print("[Email] Correo electrónico de comprobante enviado con éxito.")
        return True
    except Exception as e:
        print(f"[Email] Error al enviar comprobante de pago: {e}")
        return False
