import os
import pathlib
from datetime import date

import pydantic_settings
import streamlit as st
import toml
from pydantic import BaseModel

# ------------------------------------------------------------------------------------
# Structuration de la configuration
# ------------------------------------------------------------------------------------


class _Configuration(pydantic_settings.BaseSettings):
    # Definis pour une application enregistrée auprès d'Enedis
    #   "https://mon-compte-entreprise.enedis.fr/vos-donnees-energetiques/vos-api"
    ENEDIS_API_USERNAME: str
    ENEDIS_API_PASSWORD: str
    MODE: str = "PRODUCTION"
    MOT_DE_PASSE: str = ""
    SENDGRID_API_KEY: str = ""
    SENDGRID_SENDER_ADDRESS: str = ""
    DESTINATAIRES_ALERTES: str = ""  # si plusieurs, séparer par ";"

    model_config = pydantic_settings.SettingsConfigDict(
        env_file_encoding="utf-8",
    )


_FICHIER_CONFIGURATION_TOML = os.path.join(
    pathlib.Path(os.path.dirname(__file__)).parent,
    ".streamlit/secrets.toml",
)

if os.path.exists(_FICHIER_CONFIGURATION_TOML):
    with open(_FICHIER_CONFIGURATION_TOML, "r") as f:
        toml_conf = toml.load(f)
    print("Configuration initialisée depuis secrets.toml")
else:
    toml_conf = dict(st.secrets)
    print("Configuration initialisée depuis les Streamlit secrets")
if "CENTRALES" in toml_conf:
    _donnees_brutes_centrales = toml_conf.pop("CENTRALES").get("mapping")
else:
    _donnees_brutes_centrales = []


# Retrait de toutes les données de configuration inutiles
for i in ["ROUTINES_ACTIVES"]:
    if i in toml_conf:
        toml_conf.pop(i)

PARAMETRES = _Configuration(**toml_conf)


# ------------------------------------------------------------------------------------
# Structuration des données centrales
# ------------------------------------------------------------------------------------
class Centrale(BaseModel):
    prm: str
    debut: str
    kwc: float
    adresse: str
    nom: str | None = None
    donnees_disponibles: bool = True

    @property
    def identifiant(self) -> str:
        if self.nom:
            return self.nom
        else:
            return self.adresse

    def date_anniversaire(self, annee: int) -> date:
        try:
            x = date.fromisoformat(self.debut)
            x.year = annee
        except Exception:
            # Par défaut, on utilise le 1er janvier
            x = date(annee, 1, 1)
        return x

    @property
    def alertes_actives(self) -> bool:
        actives = (len(PARAMETRES.DESTINATAIRES_ALERTES) > 0) and (
            len(PARAMETRES.SENDGRID_API_KEY) > 0
        )
        return actives


# L'analyse est restreinte aux centrales pour lesquelles des données sont disponibles
CENTRALES = [
    i
    for i in [Centrale(**i) for i in _donnees_brutes_centrales]
    if i.donnees_disponibles
]
