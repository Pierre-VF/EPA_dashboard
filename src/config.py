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


_CONFIG_FILE = os.path.join(
    pathlib.Path(os.path.dirname(__file__)).parent,
    ".streamlit/secrets.toml",
)

if os.path.exists(_CONFIG_FILE):
    with open(_CONFIG_FILE, "r") as f:
        toml_conf = toml.load(f)
    print("Configuration initialisée depuis secrets.toml")
else:
    toml_conf = dict(st.secrets)
    print("Configuration initialisée depuis les Streamlit secrets")
if "CENTRALES" in toml_conf:
    _donnees_brutes_centrales = toml_conf.pop("CENTRALES").get("mapping")
else:
    _donnees_brutes_centrales = []


SETTINGS = Settings(**toml_conf)


# ------------------------------------------------------------------------------------
# Structuration des données centrales
# ------------------------------------------------------------------------------------
class Centrale(BaseModel):
    prm: str
    debut: str
    kwc: float
    adresse: str
    nom: str | None = None

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


CENTRALES = [Centrale(**i) for i in _donnees_brutes_centrales]
