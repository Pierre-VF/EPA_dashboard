from datetime import datetime, timedelta

from src.config import CENTRALES, PARAMETRES
from src.email_io import envoyer_email
from src.enedis_io import (
    donnees_de_production_horaires_kwh,
)


def verification_quotidienne():
    t_end = datetime.today().date()
    prms = [i.prm for i in CENTRALES]
    t_start = t_end - timedelta(days=1)

    df = donnees_de_production_horaires_kwh(prms, debut=t_start, fin=t_end)

    s_production_hier = df.sum()
    s_zero_production = s_production_hier[s_production_hier <= 0]
    s_zero_data = s_production_hier[s_production_hier < 0]

    prm_to_id = {i.prm: i.identifiant for i in CENTRALES}

    msgs = []
    if len(s_zero_production) > 0:
        msgs += ["Pas de production hier sur les centrales suivantes:"]
        for i in s_zero_production.index.to_list():
            msgs += [f"- {prm_to_id[i]}"]
    if len(s_zero_data) > 0:
        msgs += ["", "Pas de données hier sur les centrales suivantes:"]
        for i in s_zero_data.index.to_list():
            msgs += [f"- {prm_to_id[i]}"]

    if len(msgs) < 1:
        print("Pas de problèmes détectés")

    else:
        msg = "\n".join(msgs)

        print("Problèmes détectés:")
        print(msg)
        print(" ")

        email_alerts_to = PARAMETRES.DESTINATAIRES_ALERTES.split(";")
        envoyer_email(
            msg,
            title="Alerte production PV",
            recipients=email_alerts_to,
        )
        print("Email envoyé via Sendgrid")


if __name__ == "__main__":
    # Ce module est également executable comme script, par confort
    verification_quotidienne()
