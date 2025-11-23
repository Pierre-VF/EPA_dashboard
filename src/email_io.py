import sendgrid

from src.config import PARAMETRES


def envoyer_email(msg: str, title: str, recipients: list[str]) -> None:
    if PARAMETRES.SENDGRID_API_KEY is None:
        raise EnvironmentError("SENDGRID_API_KEY requis pour envoyer des emails")
    if PARAMETRES.SENDGRID_SENDER_ADDRESS is None:
        raise EnvironmentError("SENDGRID_SENDER_ADDRESS requis pour envoyer des emails")
    if len(recipients) < 1:
        return

    sg_client = sendgrid.SendGridAPIClient(api_key=PARAMETRES.SENDGRID_API_KEY)
    data = {
        "personalizations": [
            {
                "to": [{"email": i} for i in recipients],
                "subject": title,
            }
        ],
        "from": {"email": PARAMETRES.SENDGRID_SENDER_ADDRESS},
        "content": [{"type": "text/plain", "value": msg}],
    }
    response = sg_client.client.mail.send.post(request_body=data)
    print(f" - Sendgrid status={response.status_code} - details={response.body}")
