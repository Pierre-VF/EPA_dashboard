import sendgrid

from src.config import SETTINGS

alerts_active = (len(SETTINGS.DESTINATAIRES_ALERTES) > 0) and (
    len(SETTINGS.SENDGRID_API_KEY) > 0
)
email_alerts_to = SETTINGS.DESTINATAIRES_ALERTES.split(";")
sg_api_client = sendgrid.SendGridAPIClient(api_key=SETTINGS.SENDGRID_API_KEY)


def send_email(msg: str, title: str, recipients: list[str]) -> None:
    if len(recipients) < 1:
        return
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
