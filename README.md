# Dashboard pour coopérative de production d'énergie

Une simple application de tableau de bord pour gérer vos installations de production d'énergie renouvelable ([version en ligne ici](https://epa68-dashboards-v1.streamlit.app/)).

Notes:
- Cet outil requiert l'accès aux données de Enedis (via l'API et la bibliothèque Python disponible [ici](https://github.com/Pierre-VF/Enedis-data-io)).
- L'hébergement se fait gratuitement via [Streamlit Community Cloud](https://streamlit.io).

### Comment installer l'application localement?

1. Créer un environnement virtuel dans Python et l'activer

2. Installer les dépendances:

   ```
   pip install -r requirements.txt
   ```

3. Créer le fichier de configuration (dans "*.streamlit/secrets.toml*").
   
   ```
   ENEDIS_API_USERNAME = "..."
   ENEDIS_API_PASSWORD = "..."

   MODE = "DEVELOPMENT"

   [CENTRALES]
   mapping = [
      {prm="...", adresse="...", kwc=123},
      {prm="...", adresse="...", kwc=456},   
   ] 
   ```

   Où les données du "mapping" sont à ajuster pour vos centrales (une ligne par centrale):
   - PRM: numéro de compteur
   - adresse: utilisé pour le nommage de vos installations (au choix, ceci est juste pour l'affichage)
   - kwc: la puissance installée de votre installation.

   Note: pour passer en production, la ligne "MODE" doit être remplacée par (MODE =  "PRODUCTION").

4. Lancer l'application:

   ```
   streamlit run streamlit_app.py
   ```

### Comment déployer une copie sur Streamlit

Créer un compte sur [Streamlit Community Cloud](https://streamlit.io) et suivre les instructions. Le déploiement peut se faire directement à partir de ce Github (en ajudstant tous les paramètres dans le fichier TOML). Le fichier "*secret.toml*" à utiliser est celui créé ci-dessus.

## Crédits et contributions

Le code est gracieusement mis à disposition par la coopérative citoyenne de production d'énergie [Énergies partagées en Alsace](https://energies-partagees-alsace.coop/) et développé par 
[PierreVF Consulting](https://www.pierrevf.consulting/).
