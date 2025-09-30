import os
from datetime import UTC, date, datetime, timedelta
from pickle import dump, load

import numpy as np
import pandas as pd
import plotly.express as px
import pydantic_settings
import sendgrid
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
KWC_PAR_ADDRESSE = {ADRESSE_PAR_PRM[k]: v for k, v in KWC_PAR_PRM.items()}


class Settings(pydantic_settings.BaseSettings):
    # Definis pour une application enregistrée auprès d'Enedis
    #   "https://mon-compte-entreprise.enedis.fr/vos-donnees-energetiques/vos-api"
    ENEDIS_API_USERNAME: str
    ENEDIS_API_PASSWORD: str
    MODE: str = "PRODUCTION"
    MOT_DE_PASSE: str = ""
    ROUTINES_ACTIVES: bool = False
    SENDGRID_API_KEY: str = ""
    SENDGRID_SENDER_ADDRESS: str = ""
    DESTINATAIRES_ALERTES: str = ""  # si plusieurs, séparer par ";"

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
        i_kwc = KWC_PAR_PRM.get(k)
        if (i_kwc is None) or (i_kwc == 0):
            i_kwc = np.nan
        x_kwc.append(i_kwc)
    s_normaliser = pd.Series(x_kwc, index=x_adresse)

    return df_x, df_x_norm, s_yesterday, s_normaliser.astype(float)


# -------------------------------------------------------------------------------------
# Routines à executer
# -------------------------------------------------------------------------------------

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


if SETTINGS.ROUTINES_ACTIVES and False:
    # NOTE : this seems to run every time a loading of the page is made
    # (it's therefore going to result in spamming if activated)
    # Therefore it's disabled with "and False" for now
    print("Running with active routines")
    s = BackgroundScheduler()

    def routine_quotidienne():
        donnees_de_production.clear()
        __, __, s_production_yesterday, __ = data_for_plot()
        s_no_production = s_production_yesterday[s_production_yesterday == 0]
        s_no_data = s_production_yesterday[s_production_yesterday < 0]
        if alerts_active:
            msgs = []
            if len(s_no_production) > 0:
                msgs += ["Pas de production hier sur les centrales suivantes:"]
                for i in s_no_production.index.to_list():
                    msgs += [f"- {i}"]
            if len(s_no_data) > 0:
                msgs += ["", "Pas de données hier sur les centrales suivantes:"]
                for i in s_no_data.index.to_list():
                    msgs += [f"- {i}"]

            if len(msgs) > 0:
                msg = "\n".join(msgs)
                send_email(
                    msg,
                    title="Alerte production PV",
                    recipients=email_alerts_to,
                )

            print("Sent out warnings via Sendgrid")

    cron_trigger = CronTrigger(
        day="*",
        hour=5,
        minute=10,
    )

    s.add_job(routine_quotidienne, trigger=cron_trigger)
    s.start()


def show_dataframe_as_figure_in_streamlit(df: pd.DataFrame, yaxis_title: str) -> None:
    tickvals = pd.date_range(
        start=df.index[0].floor("D") + pd.Timedelta(hours=12),
        end=df.index[-1].ceil("D") + pd.Timedelta(hours=12),
        freq="24h",
    )

    fig = px.line(df)

    fig.update_layout(
        xaxis=dict(
            tickvals=tickvals,
            tickformat="%Y-%m-%d\n%H:%M",
        ),
        yaxis=dict(title=yaxis_title),
        # Affichage de la légende sous le graphique
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
        ),
        # width=900,
    )
    st.plotly_chart(
        fig,
        # use_container_width=False
    )


# -------------------------------------------------------------------------------------
# Présentation dans Streamlit
# -------------------------------------------------------------------------------------

# Pour permettre l'impression (e.g. rapports etc)# Custom CSS for print
st.html(
    """
    <style>
    @media print {
        .main {
            width: 20cm;
            padding: 0;
            margin: 0;
        }
        .stApp {
            max-width: 18cm;
        }
        .print-container {
            width: 15cm;
            margin: 0 auto; /* Center the container */
            padding: 10px;
        }
        .stPlotlyChart, .stDataFrame, table {
            max-width: 19cm !important;
            width: 100% !important;
            overflow: show
            /* overflow: hidden !important; */
        }
    }
    </style>
    """,
)


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
df_active_yesterday = s_yesterday_norm[(s_yesterday_norm > 0)].to_frame(
    "Production [kWh/kWc]"
)
df_active_yesterday["Production [kWh]"] = s_yesterday[(s_yesterday > 0)]

show_dataframe_as_figure_in_streamlit(
    df_x_norm[df_active_yesterday.index],
    "Production [kWh/kWc]",
)

st.write("Production de la veille pour les centrales actives:")


df_active_yesterday["kWc"] = [
    KWC_PAR_ADDRESSE[i] for i in df_active_yesterday.index.to_list()
]
st.dataframe(
    df_active_yesterday.round(decimals=2).sort_values("Production [kWh/kWc]"),
    width="content",
)


st.write("## Centrales inactives ou sans données")

st.write("Centrales avec **production à zéro**:")
s_no_production = s_yesterday[s_yesterday == 0]
if len(s_no_production) == 0:
    st.write("(Aucune)")
else:
    st.dataframe(
        s_no_production.index.to_series().to_frame("Adresse").reset_index(drop=True),
        hide_index=True,
        width="content",
    )

st.write("Centrales avec **données manquantes**:")
s_no_data = s_yesterday[s_yesterday < 0]
if len(s_no_data) == 0:
    st.write("(Aucune)")
else:
    st.dataframe(
        s_no_data.index.to_series().to_frame("Adresse").reset_index(drop=True),
        hide_index=True,
        width="content",
    )


st.write("## Production totale")

# Séparation entre petites et grandes centrales (limite = 36 kWc)
c_under_36kwc = [k for k, v in KWC_PAR_ADDRESSE.items() if v <= 36]
c_over_36kwc = [k for k, v in KWC_PAR_ADDRESSE.items() if v > 36]

st.write("Production totale (> 36 kWc)")
show_dataframe_as_figure_in_streamlit(
    df_x[c_over_36kwc],
    "Production [kWh]",
)

st.write("Production totale (<= 36 kWc)")
show_dataframe_as_figure_in_streamlit(
    df_x[c_under_36kwc],
    "Production [kWh]",
)


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
