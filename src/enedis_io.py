"""
Ce module contient les fonctions pour l'import des données depuis Enedis
"""

from datetime import date

import pandas as pd
from enedis_data_io.fr import ApiEntreprises

from src.config import PARAMETRES

api_io = ApiEntreprises(
    client_id=PARAMETRES.ENEDIS_API_USERNAME,
    client_secret=PARAMETRES.ENEDIS_API_PASSWORD,
)


def donnees_de_production_horaires_kwh(
    prms: list[str],
    debut: date,
    fin: date,
) -> pd.DataFrame:
    df = None
    c_erreurs = []
    for c in prms:
        try:
            df_c = api_io.production_par_demi_heure(prm=c, start=debut, end=fin)
            df_c[c] = df_c["production_wh"].astype(float) / 1000
            if df is None:
                df = df_c[[c]]
            else:
                df[c] = df_c[c]

        except Exception as e:
            print(f"Error with {c} : {e}")
            c_erreurs.append(c)

    # Re-ajout des colonnes manquantes (avec un -1 à l'échelle de la journée)
    for c in c_erreurs:
        df[c] = -(1 / 48)

    if df is None:
        raise RuntimeError(f"Aucune donnée disponible pour les PRMs demandés ({prms})")
    return df


def donnees_de_production_journalieres_kwh(
    prms: list[str],
    debut: date,
    fin: date,
) -> pd.DataFrame:
    df = None
    c_erreurs = []
    for c in prms:
        try:
            df_c = api_io.production_journaliere(prm=c, start=debut, end=fin)
            df_c[c] = df_c["production_wh"].astype(float) / 1000
            if df is None:
                df = df_c[[c]]
            else:
                df[c] = df_c[c]

        except Exception as e:
            print(f"Error with {c} : {e}")
            c_erreurs.append(c)

    for c in c_erreurs:
        df[c] = pd.NA

    if df is None:
        raise RuntimeError(f"Aucune donnée disponible pour les PRMs demandés ({prms})")
    return df
