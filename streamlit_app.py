from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from pytz import timezone

from src.cache_io import local_disk_cache
from src.config import CENTRALES, PARAMETRES
from src.enedis_io import (
    donnees_de_production_horaires_kwh,
    donnees_de_production_journalieres_kwh,
)

# ------------------------------------------------------
#  Settings and base methods
# ------------------------------------------------------

# Détails des centrales
TIMEZONE = timezone("Europe/Paris")
DETAILS_CENTRALES = {i.prm: i for i in CENTRALES}
KWC_PAR_PRM = {k: v.kwc for k, v in DETAILS_CENTRALES.items()}
ID_PAR_PRM = {
    k: f"[{int(DETAILS_CENTRALES[k].kwc)} kWc] {v.identifiant}"
    for k, v in DETAILS_CENTRALES.items()
}
KWC_PAR_ID = {ID_PAR_PRM[k]: v for k, v in KWC_PAR_PRM.items()}


# -------------------------------------------------------------------------------------
#  Fonctions de chargement de données
# -------------------------------------------------------------------------------------


@st.cache_data(ttl=12 * 3600, max_entries=2)  # TTL en secondes
def donnees_de_production(
    current_day: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if current_day is None:
        t_end = datetime.today().date()
    else:
        t_end = current_day
    prms = list(ID_PAR_PRM.keys())
    t_start = t_end - timedelta(days=3)
    df_courbe_de_charge = donnees_de_production_horaires_kwh(
        prms, debut=t_start, fin=t_end
    )
    df_prod_journaliere = donnees_de_production_journalieres_kwh(
        prms, debut=t_start, fin=t_end
    )
    return df_courbe_de_charge, df_prod_journaliere


@local_disk_cache
def cached_enedis_data() -> tuple[pd.DataFrame, datetime, pd.DataFrame]:
    t0 = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    df, df_jour = donnees_de_production(t0.date())
    return df, t0, df_jour


def data_pour_plot() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.Series,
    pd.Series,
    pd.DataFrame,
]:
    df, t0, df_jour = cached_enedis_data()
    df_x: pd.DataFrame = df[t0 - timedelta(hours=4 * 24) : t0].interpolate()
    df_x_norm = df_x[[]].copy()
    s_yesterday = df[t0 - timedelta(hours=24) : t0].resample("h").sum().sum()
    for k, v in KWC_PAR_PRM.items():
        df_x_norm[k] = df_x[k] / v

    # Renommage des colonnes avec les addresses des centrales
    df_x = df_x.rename(columns=ID_PAR_PRM).sort_index()
    df_x_norm = df_x_norm.rename(columns=ID_PAR_PRM).sort_index()
    s_yesterday.index = s_yesterday.index.to_series().apply(lambda x: ID_PAR_PRM.get(x))

    x_adresse = []
    x_kwc = []
    for k, v in ID_PAR_PRM.items():
        x_adresse.append(v)
        i_kwc = KWC_PAR_PRM.get(k)
        if (i_kwc is None) or (i_kwc == 0):
            i_kwc = np.nan
        x_kwc.append(i_kwc)
    s_normaliser = pd.Series(x_kwc, index=x_adresse)

    return df_x, df_x_norm, s_yesterday, s_normaliser.astype(float), df_jour


def dataframe_vers_figure_streamlit(df: pd.DataFrame, yaxis_title: str) -> None:
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


def _trick_dataframe_print(df, hide_index: bool = False):
    st.dataframe(
        df,
        width="content",
        height="content",
        hide_index=hide_index,
    )


st.title("Production énergétique des centrales d'EPA")
st.write("## Centrales actives")

# Loading data
df_x, df_x_norm, s_hier, s_normaliser, df_jour = data_pour_plot()

# Marquage des erreurs
s_hier.loc[s_hier < 0] = -1

st.write("Production pour les centrales actives:")
s_hier_norm = s_hier / s_normaliser
df_active_hier = s_hier_norm[(s_hier_norm > 0)].to_frame("Production [kWh/kWc]")
df_active_hier["Production [kWh]"] = s_hier[(s_hier > 0)]

dataframe_vers_figure_streamlit(
    df_x_norm[df_active_hier.index],
    "Production [kWh/kWc]",
)

st.write("Production récente pour les centrales actives (kWh)")


df_jour = df_jour.rename(columns=ID_PAR_PRM)
df_jour.index = df_jour.index.to_series().apply(lambda x: x.date())
t_veille = df_jour.index.max()
df_jour_pour_ui = df_jour.sort_index(ascending=False).T.round(decimals=1)
df_jour_pour_ui["kWc"] = [float(KWC_PAR_ID[i]) for i in df_jour_pour_ui.index.to_list()]
df_jour_pour_ui[f"{t_veille}/kWc"] = (
    df_jour_pour_ui[t_veille] / df_jour_pour_ui["kWc"]
).round(decimals=1)
_trick_dataframe_print(
    df_jour_pour_ui,
)


st.write("## Centrales inactives ou sans données")

st.write("Centrales avec **production à zéro**:")
s_no_production = s_hier[s_hier == 0]
if len(s_no_production) == 0:
    st.write("(Aucune)")
else:
    _trick_dataframe_print(
        s_no_production.index.to_series().to_frame("Adresse").reset_index(drop=True),
        hide_index=True,
    )

st.write("Centrales avec **données manquantes**:")
s_no_data = s_hier[s_hier < 0]
if len(s_no_data) == 0:
    st.write("(Aucune)")
else:
    _trick_dataframe_print(
        s_no_data.index.to_series().to_frame("Adresse").reset_index(drop=True),
        hide_index=True,
    )


st.write("## Puissance moyenne produite")

# Séparation entre petites et grandes centrales (limite = 36 kWc)
c_moins_de_36kwc = [k for k, v in KWC_PAR_ID.items() if v <= 36]
c_plus_de_36kwc = [k for k, v in KWC_PAR_ID.items() if v > 36]

st.write("Production totale (> 36 kWc)")
dataframe_vers_figure_streamlit(
    df_x[c_plus_de_36kwc],
    "Production (puissance moyenne) [kW]",
)

st.write("Production totale (<= 36 kWc)")
dataframe_vers_figure_streamlit(
    df_x[c_moins_de_36kwc],
    "Production (puissance moyenne) [kW]",
)


@st.dialog("Veuillez confirmer votre mot de passe")
def verifier_mot_de_passe_et_rafraichir():
    mdp = st.text_input("Mot de passe")
    if st.button("Submit"):
        if mdp == PARAMETRES.MOT_DE_PASSE:
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
