import os
from datetime import UTC, date, datetime, timedelta
from pickle import dump, load

import numpy as np
import pandas as pd
import plotly.express as px
import pydantic_settings
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from enedis_data_io.fr import ApiEntreprises
from pytz import timezone

# ------------------------------------------------------
#  Settings and base methods
# ------------------------------------------------------

# Détails des centrales
TIMEZONE = timezone("Europe/Paris")
DETAILS_CENTRALES = {i["prm"]: i for i in st.secrets["CENTRALES"]["mapping"]}
ADRESSE_PAR_PRM = {k: v.get("adresse") for k, v in DETAILS_CENTRALES.items()}
KWC_PAR_PRM = {k: v.get("kwc") for k, v in DETAILS_CENTRALES.items()}


class Settings(pydantic_settings.BaseSettings):
    # Definis pour une application enregistrée auprès d'Enedis
    #   "https://mon-compte-entreprise.enedis.fr/vos-donnees-energetiques/vos-api"
    ENEDIS_API_USERNAME: str
    ENEDIS_API_PASSWORD: str
    MODE: str = "PRODUCTION"
    MOT_DE_PASSE: str = ""
    ROUTINES_ACTIVES: bool = False

    model_config = pydantic_settings.SettingsConfigDict(
        env_file_encoding="utf-8",
    )


# Ouverture d'une connexion vers l'API
SETTINGS = Settings()
api_io = ApiEntreprises(
    client_id=SETTINGS.ENEDIS_API_USERNAME, client_secret=SETTINGS.ENEDIS_API_PASSWORD
)


# -------------------------------------------------------------------------------------
#  Fonctions de chargement de données
# -------------------------------------------------------------------------------------
def local_disk_cache(f_in):
    if str(SETTINGS.MODE) == "PRODUCTION":
        # Short circuiting
        return f_in

    os.makedirs(".data", exist_ok=True)
    cache_file = f".data/{f_in.__name__}.pkl"

    def f_out():
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as file:
                r = load(file)
        else:
            r = f_in()
            with open(cache_file, "wb") as file:
                dump(r, file)
        return r

    return f_out


@st.cache_data(ttl=12 * 3600, max_entries=2)  # TTL en secondes
def donnees_de_production(current_day: date | None = None) -> pd.DataFrame:
    if current_day is None:
        t_end = datetime.today().date()
    else:
        t_end = current_day
    prms = list(ADRESSE_PAR_PRM.keys())
    t_start = t_end - timedelta(days=3)
    df = None
    c_erreurs = []
    for c in prms:
        try:
            df_c = api_io.production_par_demi_heure(prm=c, start=t_start, end=t_end)
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

    return df


@local_disk_cache
def data_for_plot() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    t0 = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    df = donnees_de_production(t0.date())
    df_x: pd.DataFrame = df[t0 - timedelta(hours=4 * 24) : t0].interpolate()
    df_x_norm = df_x[[]].copy()
    s_yesterday = df[t0 - timedelta(hours=24) : t0].resample("h").mean().sum()
    for k, v in KWC_PAR_PRM.items():
        df_x_norm[k] = df_x[k] / v

    # Renommage des colonnes avec les addresses des centrales
    df_x = df_x.rename(columns=ADRESSE_PAR_PRM).sort_index()
    df_x_norm = df_x_norm.rename(columns=ADRESSE_PAR_PRM).sort_index()
    s_yesterday.index = s_yesterday.index.to_series().apply(
        lambda x: ADRESSE_PAR_PRM.get(x)
    )

    x_adresse = []
    x_kwc = []
    for k, v in ADRESSE_PAR_PRM.items():
        x_adresse.append(v)
        x_kwc.append(KWC_PAR_PRM.get(k, np.nan))
    s_normaliser = pd.Series(x_kwc, index=x_adresse)

    return df_x, df_x_norm, s_yesterday, s_normaliser.astype(float)


# -------------------------------------------------------------------------------------
# Routines à executer
# -------------------------------------------------------------------------------------
if SETTINGS.ROUTINES_ACTIVES:
    s = BackgroundScheduler()

    def routine_quotidienne():
        print("I'm running a job")

    cron_trigger = CronTrigger(
        hour="*",  # Pour tester, une fois par heure pour l'instant
    )

    s.add_job(routine_quotidienne, trigger=cron_trigger)
    s.start()


# -------------------------------------------------------------------------------------
# Présentation dans Streamlit
# -------------------------------------------------------------------------------------

st.set_page_config(
    page_title="Production des centrales solaires",
    page_icon=":material/sunny:",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items=None,
)


st.title("Production énergétique des centrales d'EPA")
st.write("## Centrales actives")

# Loading data
df_x, df_x_norm, s_yesterday, s_normaliser = data_for_plot()

# Marquage des erreurs
s_yesterday.loc[s_yesterday < 0] = -1

st.write("Production pour les centrales actives:")
s_yesterday_norm = s_yesterday / s_normaliser
df_actives = s_yesterday_norm[(s_yesterday_norm > 0)].to_frame("Production [kWh/kWc]")
df_actives["Production [kWh]"] = s_yesterday[(s_yesterday > 0)]

fig_prod_kwh_per_kwc = px.line(
    df_x_norm[df_actives.index],
)
fig_prod_kwh_per_kwc.update_layout(dict(yaxis=dict(title="Production [kWh/kWc]")))
st.plotly_chart(fig_prod_kwh_per_kwc, use_container_width=True)

st.write("Production pour les centrales actives:")
st.dataframe(df_actives.round(decimals=2))


st.write("## Centrales inactives ou sans données")

st.write("Centrales avec production à zéro:")
s_no_production = s_yesterday[s_yesterday == 0]
if len(s_no_production) == 0:
    st.write("(Aucune)")
else:
    st.dataframe(
        s_no_production.index.to_series().to_frame("Adresse").reset_index(drop=True),
        hide_index=True,
    )

st.write("Centrales avec données manquantes:")
s_no_data = s_yesterday[s_yesterday < 0]
if len(s_no_data) == 0:
    st.write("(Aucune)")
else:
    st.dataframe(
        s_no_data.index.to_series().to_frame("Adresse").reset_index(drop=True),
        hide_index=True,
    )


st.write("## Production totale")

st.write("Production totale")
fig_prod_totale = px.line(
    df_x,
)
fig_prod_totale.update_layout(dict(yaxis=dict(title="Production [kWh]")))
st.plotly_chart(fig_prod_totale, use_container_width=True)


@st.dialog("Veuillez confirmer votre mot de passe")
def verifier_mot_de_passe_et_rafraichir():
    mdp = st.text_input("Mot de passe")
    if st.button("Submit"):
        if mdp == SETTINGS.MOT_DE_PASSE:
            donnees_de_production.clear()
            st.rerun()
            st.write(
                "Les données ont été rafraichies - vous pouvez fermer cette boîte de dialogue"
            )
        else:
            st.write("Mot de passe erroné")


if st.button("Rafraîchir les données"):
    verifier_mot_de_passe_et_rafraichir()
else:
    st.write(" ")
