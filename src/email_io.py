import sendgrid

from src.config import SETTINGS

alerts_active = (len(SETTINGS.DESTINATAIRES_ALERTES) > 0) and (
    len(SETTINGS.SENDGRID_API_KEY) > 0
)
email_alerts_to = SETTINGS.DESTINATAIRES_ALERTES.split(";")


def send_email(msg: str, title: str, recipients: list[str]) -> None:
    if SETTINGS.SENDGRID_API_KEY is None:
        raise EnvironmentError("SENDGRID_API_KEY requis pour envoyer des emails")
    if SETTINGS.SENDGRID_SENDER_ADDRESS is None:
        raise EnvironmentError("SENDGRID_SENDER_ADDRESS requis pour envoyer des emails")
    if len(recipients) < 1:
        return

    sg_api_client = sendgrid.SendGridAPIClient(api_key=SETTINGS.SENDGRID_API_KEY)
    data = {
        "personalizations": [
            {
                "to": [{"email": i} for i in recipients],
                "subject": title,
            }
        ],
        "from": {"email": SETTINGS.SENDGRID_SENDER_ADDRESS},
        "content": [{"type": "text/plain", "value": msg}],
    }
    response = sg_api_client.client.mail.send.post(request_body=data)
    print(f" - Sendgrid status={response.status_code} - details={response.body}")
