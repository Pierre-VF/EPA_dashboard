from datetime import datetime, timedelta

from src.config import CENTRALES
from src.email_io import email_alerts_to, send_email
from src.enedis_io import (
    donnees_de_production_horaires_kwh,
)


def verification_quotidienne():
    t_end = datetime.today().date()
    prms = [i.prm for i in CENTRALES]
    t_start = t_end - timedelta(days=1)

    df = donnees_de_production_horaires_kwh(prms, start=t_start, end=t_end)

    s_production_yesterday = df.sum()
    s_no_production = s_production_yesterday[s_production_yesterday == 0]
    s_no_data = s_production_yesterday[s_production_yesterday < 0]

    prm_to_id = {i.prm: i.identifiant for i in CENTRALES}

    msgs = []
    if len(s_no_production) > 0:
        msgs += ["Pas de production hier sur les centrales suivantes:"]
        for i in s_no_production.index.to_list():
            msgs += [f"- {prm_to_id[i]}"]
    if len(s_no_data) > 0:
        msgs += ["", "Pas de données hier sur les centrales suivantes:"]
        for i in s_no_data.index.to_list():
            msgs += [f"- {prm_to_id[i]}"]

    if len(msgs) < 1:
        print("Pas de problèmes détectés")

    else:
        msg = "\n".join(msgs)

        print("Problèmes détectés:")
        print(msg)
        print(" ")

        send_email(
            msg,
            title="Alerte production PV",
            recipients=email_alerts_to,
        )
        print("Email envoyé via Sendgrid")


if __name__ == "__main__":
    # Ce module est également executable comme script, par confort
    verification_quotidienne()
