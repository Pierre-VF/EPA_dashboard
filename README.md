# Dashboard pour coopérative de production d'énergie

Une simple application de tableau de bord pour gérer vos installations de production d'énergie renouvelable ([version en ligne ici](https://epa68-dashboards-v1.streamlit.app/)).

Notes:
- Cet outil requiert l'accès aux données de Enedis (via l'API et la bibliothèque Python disponible [ici](https://github.com/Pierre-VF/Enedis-data-io)).
- L'hébergement se fait gratuitement via [Streamlit Community Cloud](https://streamlit.io).

### Comment installer l'application localement?

1. S'assurer d'avoir UV installé localement [(détails d'installation ici)](https://docs.astral.sh/uv/getting-started/installation/).

2. Installer les dépendances dans un nouvel environnement UV.

   ```
   uv sync --all-groups
   ```

3. Créer le fichier de configuration (dans "*.streamlit/secrets.toml*").

   ```
   # Identifiants de l'API d'Enedis
   ENEDIS_API_USERNAME = "..."
   ENEDIS_API_PASSWORD = "..."

   # DEVELOPEMENT ou PRODUCTION selon l'utilisation voulue
   MODE = "DEVELOPMENT"

   # Mot de passe pour l'option de rafraichissement des données
   MOT_DE_PASSE = "..."

   # Identifiants Sendgrid pour l'envoi des emails [FACULTATIFS]
   SENDGRID_API_KEY = "..."
   SENDGRID_SENDER_ADDRESS = "..."

   # Destinataires (séparés par ";") des emails d'alertes [FACULTATIF]
   DESTINATAIRES_ALERTES = "... [séparer plusieurs entrées par ;]..."

   # Mappings des centrales à charger
   [CENTRALES]
   mapping = [
      {prm="...", adresse="...", kwc=123, debut="2014-01-01", nom="..."},
      {prm="...", adresse="...", kwc=9, debut="", nom="...", donnees_disponibles=0}
   ]
   ```

   `SENDGRID_API_KEY`, `SENDGRID_SENDER_ADDRESS` et `DESTINATAIRES_ALERTES` sont facultatifs (ils servent simplement l'envoi de mail avec [Sendgrid](https://sendgrid.com/))

   Où les données du `mapping` sont à ajuster pour vos centrales (une ligne par centrale, vous pouvez en ajouter autant que vous voulez tant que le format [TOML](https://toml.io/fr/) est respecté):
   - `prm`: numéro de compteur
   - `nom`: utilisé pour le nommage de vos installations (au choix, ceci est juste pour l'affichage)
   - `kwc`: la puissance installée de votre installation

   Note: pour passer en production, la ligne "MODE" doit être remplacée par (`MODE =  "PRODUCTION"`). Le mode développement ci-dessus utilise un cache local sur le disque pour fluidifier les appels à l'API d'Enedis.

4. Lancer l'application:

   ```
   streamlit run streamlit_app.py
   ```

### Comment déployer une copie sur Streamlit

Créer un compte sur [Streamlit Community Cloud](https://streamlit.io) et suivre les instructions (pour la gestion ultérieure, le lien est ensuite [celui-ci](https://share.streamlit.io/)). Le déploiement peut se faire directement à partir de ce Github (en ajudstant tous les paramètres dans le fichier TOML). Le fichier "*secret.toml*" à utiliser est celui créé ci-dessus.


## Crédits et contributions

Le code est gracieusement mis à disposition par la coopérative citoyenne de production d'énergie [Énergies partagées en Alsace](https://energies-partagees-alsace.coop/) et développé par
[PierreVF Consulting](https://www.pierrevf.consulting/).
