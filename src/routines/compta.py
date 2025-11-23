from datetime import date, timedelta

import pandas as pd

from src.cache_io import local_disk_cache
from src.config import CENTRALES
from src.enedis_io import (
    donnees_de_production_journalieres_kwh,
)


def export_comptabilite_de_production() -> str:
    @local_disk_cache
    def _load_years_data():
        aujourdhui = date.today()
        debut_annee_precedente = date(aujourdhui.year - 1, 1, 1)
        df = donnees_de_production_journalieres_kwh(
            [i.prm for i in CENTRALES],
            debut=debut_annee_precedente,
            fin=aujourdhui,
        )
        print(df)
        return df

    df = _load_years_data()

    aujourdhui = date.today()
    t_debut_annee_passee = date(aujourdhui.year - 1, 1, 1)
    t_debut_annee_courante = date(aujourdhui.year, 1, 1)

    # Copie des donnees réindexée en heure locale
    df2 = df.copy()
    df2 = df2.tz_convert("Europe/Paris")
    df2.index = df2.index.to_series().apply(lambda x: x.date())

    df_out = pd.DataFrame(
        data=[
            {
                "prm": c.prm,
                "nom": c.identifiant,
                "debut_de_production": c.debut,
            }
            for c in CENTRALES
        ]
    ).set_index("prm")

    def _f_arrondi(s):
        try:
            x = s.round(2)
        except Exception:
            x = s
        return x

    # Statistiques annee passée
    y_annee_passee = t_debut_annee_passee.year
    df_ym1 = df2[t_debut_annee_passee : t_debut_annee_courante - timedelta(days=1)]
    df_out[f"production_kwh_{y_annee_passee}"] = _f_arrondi(df_ym1.sum(skipna=False))
    df_out[f"production_dispo_kwh_{y_annee_passee}"] = _f_arrondi(
        df_ym1.sum(skipna=True)
    )
    df_out[f"jours_manquants_{y_annee_passee}"] = df_ym1.isna().sum()

    # Statistiques annee courante
    y_annee_courante = t_debut_annee_courante.year
    df_y = df2[t_debut_annee_courante:]
    df_out[f"production_kwh_{y_annee_courante}"] = _f_arrondi(df_y.sum(skipna=False))
    df_out[f"production_dispo_kwh_{y_annee_courante}"] = _f_arrondi(
        df_y.sum(skipna=True)
    )
    df_out[f"jours_manquants_{y_annee_courante}"] = df_y.isna().sum()

    d_prod_anniversaire = dict()
    for col in df.keys():
        c = [i for i in CENTRALES if i.prm == col][0]
        t0_col = c.date_anniversaire(t_debut_annee_passee.year)
        t1_col = c.date_anniversaire(t_debut_annee_courante.year) - timedelta(days=1)
        s_col = df2[col][t0_col:t1_col].copy()
        d_prod_anniversaire[col] = {
            "nom": c.identifiant,
            "debut": t0_col,
            "fin": t1_col,
            "production_kwh": s_col.sum(skipna=False),
            "jours_manquants": s_col.isna().sum(),
            "debut_de_production": c.debut,
        }

    df_anniversaire = pd.DataFrame(d_prod_anniversaire).T

    f_out = "compta.xlsx"
    with pd.ExcelWriter(f_out) as f:
        df_out.to_excel(f, sheet_name="Par an")
        df_anniversaire.to_excel(f, sheet_name="Par anniversaire")

    print(f"Donnees de production exportées dans {f_out}")
    return f_out


if __name__ == "__main__":
    # Ce module est également executable comme script, par confort
    export_comptabilite_de_production()
