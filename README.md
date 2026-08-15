# Platefrom_coloc — Mur de photos pour événements

Application web permettant aux invités d'un événement (soirée, anniversaire, fête de coloc...) d'envoyer des photos depuis leur téléphone et de les voir apparaître en temps réel sous forme de diaporama sur une télévision ou un écran connecté. Aucun compte à créer : chacun choisit un pseudo, scanne un QR code affiché sur l'écran, et ses photos apparaissent quasi instantanément pour tout le monde.

## Présentation générale

### Comment ça marche
1. L'écran TV affiche la page `/tv/` avec un QR code visible en permanence.
2. Un invité scanne le QR code avec son téléphone et arrive sur la page de choix de pseudo.
3. Il choisit un pseudo (mémorisé pour sa session, pas de mot de passe). Si l'intégration Google Drive est activée, il peut ensuite laisser son email pour recevoir un accès en lecture au dossier Drive de la soirée (étape facultative, "Skip" possible).
4. Il accède à la page d'upload et envoie une ou plusieurs photos, prises sur le moment ou depuis sa galerie.
5. Les photos apparaissent en direct (WebSocket) sur l'écran TV : une bannière "Nouvelle photo de X" s'affiche, puis la photo rejoint le diaporama tournant. Si l'intégration Drive est active, chaque photo est aussi copiée dans le dossier Drive de la soirée.
6. Les invités peuvent aussi parcourir une galerie de toutes les photos et les liker ; le top 3 des photos les plus aimées s'affiche en direct sur l'écran TV.
7. Chacun peut consulter "Mes photos" et supprimer ses propres envois.
8. Un administrateur peut ajuster la vitesse du diaporama et activer/connecter l'intégration Google Drive depuis l'admin Django, avec effet immédiat.

> À terme, l'objectif est une app entièrement personnalisable par soirée depuis l'admin : activer ou non le classement des likes, l'intégration Drive, un chat, un tableau blanc collectif, etc. Le classement des likes et l'intégration Drive sont les premières briques de ce système de fonctionnalités optionnelles.

### Stack technique
- **Backend** : Django 5 + Django Channels (WebSocket temps réel), servi en ASGI par Daphne
- **Base de données** : PostgreSQL 16
- **Frontend** : templates Django + JavaScript vanilla (pas de framework front)
- **Conteneurisation** : Docker / docker-compose (services `db` + `web`)
- **QR code** : génération à la volée avec la librairie `qrcode`

### Lancer le projet
```
docker compose up --build
```
- Application : http://localhost:8000
- Écran TV : http://localhost:8000/tv/
- Admin Django : http://localhost:8000/admin/

Au premier lancement, créer un compte admin si besoin :
```
docker compose exec web python manage.py createsuperuser
```

### Configuration de l'intégration Google Drive (optionnelle)

L'app peut copier chaque photo envoyée vers un dossier Google Drive dédié à la soirée, et proposer aux invités de partager ce dossier vers leur email. L'authentification se fait via **OAuth2 sur un compte Google personnel** (et non un compte de service) : un compte de service Google n'a aucun quota de stockage Drive propre en dehors d'un Drive Partagé, une fonctionnalité réservée aux comptes Google Workspace payants — inutilisable avec un Gmail personnel gratuit.

Mise en place, à faire une seule fois :

1. **Créer un projet Google Cloud** sur [console.cloud.google.com](https://console.cloud.google.com), puis activer l'**API Google Drive** (menu "APIs & Services" → "Enable APIs and services").
2. **Configurer l'écran de consentement OAuth** ("OAuth consent screen") : type "External", ajouter votre propre adresse Gmail comme "Test user" (suffisant tant que l'app reste en mode test, pas besoin de validation Google pour un usage personnel).
3. **Créer des identifiants OAuth** ("Credentials" → "Create credentials" → "OAuth client ID"), type d'application **Desktop app**. Télécharger le fichier JSON généré.
4. Placer ce fichier dans `credentials/client_secret.json` à la racine du projet (dossier ignoré par git).
5. **Créer un dossier racine** dans votre Drive personnel (ex. "Coloc Photos"), qui contiendra un sous-dossier par soirée. Récupérer son ID dans l'URL du dossier (`https://drive.google.com/drive/folders/<ID>`), et le renseigner dans `GOOGLE_DRIVE_ROOT_FOLDER_ID` (dans `docker-compose.yml`).
6. **Lancer l'autorisation initiale**, en local (hors conteneur, car un navigateur doit s'ouvrir) :
   ```
   pip install -r requirements.txt
   GOOGLE_OAUTH_CLIENT_SECRET_FILE=credentials/client_secret.json GOOGLE_OAUTH_TOKEN_FILE=credentials/token.json python manage.py google_drive_auth
   ```
   Cela ouvre un navigateur pour valider l'accès avec votre compte Google, puis écrit le refresh token dans `credentials/token.json`. Ce fichier est ensuite monté (lecture seule) dans le conteneur `web` et réutilisé/rafraîchi automatiquement — plus jamais besoin de repasser par cette étape sauf révocation manuelle de l'accès.
7. Dans l'admin Django (`/admin/`), ouvrir **Event settings**, cocher **Drive enabled**, ajuster si besoin le nom du dossier (par défaut la date du jour au format `DD/MM/YYYY`), puis enregistrer : le dossier est créé (ou retrouvé s'il existe déjà) automatiquement dans Drive.

## Spécification fonctionnelle

### Acteurs
- **Invité** : aucun compte, identifié uniquement par un pseudo lié à sa session navigateur
- **Écran TV** : client passif qui affiche le flux de photos en direct
- **Administrateur** : accès à l'admin Django

### Parcours et écrans

#### 1. Choix du pseudo — `/pseudo/`
- Formulaire à un champ (nom, 50 caractères max)
- Le pseudo doit être unique, insensible à la casse ; en cas de conflit, message d'erreur invitant à en choisir un autre
- Une fois validé, le pseudo est associé à la session Django (table `UserIdentity`, liée à la clé de session) et stocké en session
- Si un pseudo est déjà en session, redirection automatique vers `/upload/`
- Lien direct vers la galerie sans avoir à choisir de pseudo
- Une fois le pseudo validé : redirection vers `/upload/`, sauf si l'intégration Drive est activée et connectée, auquel cas redirection vers l'étape de partage Drive (`/pseudo/share-drive/`)

#### 2. Partage du dossier Drive — `/pseudo/share-drive/` (si Drive activé)
- N'apparaît que si l'intégration Google Drive est activée dans l'admin et qu'un dossier a bien été connecté
- Propose un champ email facultatif, avec un bouton "Share with me" et un bouton "Skip"
- Si un email est renseigné : ajoute cette adresse en lecteur ("reader") sur le dossier Drive de la soirée via l'API, avec notification par email envoyée par Google ; l'email est aussi enregistré sur l'identité de session (`UserIdentity.email`)
- En cas d'échec de l'appel à l'API Drive, un message d'erreur s'affiche et l'invité peut réessayer ou continuer sans partage
- Dans tous les cas (email renseigné, skip, ou après un partage réussi), redirection vers `/upload/`

#### 3. Upload de photos — `/upload/`
- Accessible uniquement avec un pseudo en session (sinon redirection vers `/pseudo/`)
- Deux façons de choisir une image :
  - **Choisir une photo** : sélection classique depuis la galerie du téléphone (plusieurs fichiers possibles)
  - **Prendre une photo** : ouvre directement l'appareil photo (`capture="environment"`) ; une photo prise remplace toute sélection précédente
- Le bouton Upload change d'état visuellement dès qu'un fichier est sélectionné
- Tentative de soumission sans fichier : le message de statut affiche une animation de refus (shake), pas d'envoi
- À la soumission, chaque image est enregistrée en base (modèle `Photo`) avec le pseudo de l'auteur ; le fichier est stocké sous `photos/<pseudo>_<HHhMM>_<id-unique>.<ext>`
- Chaque photo envoyée est aussitôt diffusée à tous les écrans TV connectés via WebSocket
- Si l'intégration Drive est active et connectée, chaque photo est aussi copiée dans le dossier Drive de la soirée (upload best-effort : une erreur Drive est journalisée côté serveur mais ne bloque jamais l'envoi ni l'affichage sur l'écran TV)
- Message "Upload successful" affiché puis retour automatique à l'état vide après 3 secondes
- Liens rapides vers "Mes photos" et "Gallery"

#### 4. Mes photos — `/my-photos/`
- Accessible uniquement avec un pseudo en session
- Liste, par ordre chronologique, des photos envoyées par l'utilisateur courant
- Suppression possible photo par photo ; un utilisateur ne peut supprimer que ses propres photos (vérifié par pseudo + identifiant, pas seulement par session)
- La suppression efface le fichier physique et notifie l'écran TV en direct pour retirer la photo du diaporama en cours

#### 5. Écran TV — `/tv/`
- Page plein écran destinée à un téléviseur ou un moniteur connecté, sans interaction attendue
- Au chargement, récupère la liste actuelle des photos et l'intervalle du diaporama
- Diaporama automatique en fondu enchaîné, intervalle configurable (5 secondes par défaut)
- Message "Waiting for photos…" tant qu'aucune photo n'a été envoyée
- QR code permanent pointant vers `/upload/`, pour que tout nouvel invité puisse rejoindre à tout moment
- Bannière "New photo from &lt;pseudo&gt;" : à chaque upload, une superposition centrale annonce la nouvelle photo pendant 3 secondes ; les annonces sont mises en file si plusieurs photos arrivent en même temps, indépendamment du cycle du diaporama de fond
- Classement latéral (leaderboard) du top 3 des photos les plus likées, mis à jour en direct
- Connexion WebSocket permanente, avec reconnexion automatique toutes les 3 secondes en cas de coupure

#### 6. Galerie — `/gallery/`
- Page publique, accessible sans avoir choisi de pseudo
- Affiche toutes les photos de tous les invités, les plus récentes en premier
- Chaque photo peut être likée / unlikée (cœur cliquable, bascule)
- Aimer une photo nécessite une identité de session valide (donc d'être passé par le choix de pseudo au préalable) ; sinon la tentative échoue
- Chaque like/unlike met à jour en direct le classement affiché sur l'écran TV

#### 7. QR code d'upload — `/qr/upload.png`
- Génère à la volée une image PNG encodant l'URL absolue de la page `/upload/`
- Si la variable d'environnement `QR_HOST_IP` est définie, cette IP est utilisée à la place du nom d'hôte de la requête — utile pour garantir que le QR code reste scannable sur le réseau local du logement même quand le serveur tourne dans un conteneur

#### 8. Administration — `/admin/`
- Interface Django Admin standard
- **Photos** : consultation, filtrage par pseudo
- **Identités** (`UserIdentity`) : pseudo, email (si renseigné pour le partage Drive), statut de partage, session, date de création
- **Likes** : consultation des likes posés
- **Réglages du diaporama** (`SlideshowSettings`, entrée unique) : intervalle d'affichage en secondes (de 0,1 à 100) ; toute modification est propagée en direct à l'écran TV sans rechargement
- **Réglages de l'événement** (`EventSettings`, entrée unique) :
  - `drive_enabled` : active/désactive toute l'intégration Google Drive (upload des photos + étape de partage par email)
  - `drive_folder_name` : nom du dossier Drive de la soirée, pré-rempli à la date du jour (`DD/MM/YYYY`) mais modifiable
  - À chaque enregistrement avec `drive_enabled` coché, le dossier correspondant est automatiquement recherché (et réutilisé s'il existe déjà sous le dossier racine configuré) ou créé, puis son ID et son lien sont stockés en lecture seule (`drive_folder_id`, `drive_folder_url`)
  - En cas d'échec (credentials manquants/expirés, dossier racine introuvable...), un message d'erreur explicite s'affiche dans l'admin sans bloquer l'enregistrement des autres réglages

### API interne (JSON)
| Endpoint | Méthode | Description |
|---|---|---|
| `/api/photos/` | GET | Liste toutes les photos (id, url, pseudo, date, nombre de likes, statut liké pour l'utilisateur courant) |
| `/api/photos/<id>/like/` | POST | Bascule le like/unlike pour l'utilisateur de la session courante |
| `/api/settings/` | GET | Intervalle courant du diaporama |

### Canal temps réel — `/ws/tv/`
Un unique canal WebSocket diffuse à tous les écrans TV connectés :
- `uploaded` — nouvelle photo envoyée (données complètes)
- `deleted` — une photo a été supprimée (url concernée)
- `settings` — l'intervalle du diaporama a changé
- `liked` — le nombre de likes d'une photo a changé

### Modèle de données
- **Photo** — pseudo de l'auteur, fichier image, date d'envoi
- **UserIdentity** — pseudo (unique), clé de session (unique), email (facultatif, pour le partage Drive), statut de partage Drive, date de création ; fait office d'identité légère sans mot de passe
- **Like** — association Photo ↔ UserIdentity (unique par paire), date
- **SlideshowSettings** — entrée unique, intervalle d'affichage du diaporama en secondes
- **EventSettings** — entrée unique, réglages de l'intégration Drive (activée ou non, nom/ID/lien du dossier de la soirée) ; vocation à accueillir les futurs interrupteurs de fonctionnalités (chat, tableau blanc...)

### Règles métier notables
- Aucune authentification classique : l'identité d'un invité repose entièrement sur sa session navigateur associée à un pseudo unique
- Un pseudo ne peut être utilisé que par une seule session à la fois
- Une photo ne peut être supprimée que par son auteur (vérifié par pseudo + identifiant de la photo)
- Toute mutation (envoi, suppression, like, changement de réglage) est répercutée en temps réel sur l'écran TV via WebSocket, sans rechargement de page
- En mode développement (`DEBUG=True`, valeur par défaut du projet), les fichiers médias sont servis directement par Django
- L'intégration Drive est entièrement optionnelle et best-effort : si elle échoue (credentials expirés, quota, réseau...), l'upload local de la photo et l'affichage sur l'écran TV ne sont jamais bloqués ; seule l'étape de partage par email affiche un message d'erreur visible par l'invité, puisqu'elle est une action explicite de sa part

## Configuration (variables d'environnement)
| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django | clé de développement en dur dans le code |
| `DJANGO_DB_NAME` | Nom de la base PostgreSQL | `coloc_photos` |
| `DJANGO_DB_USER` | Utilisateur PostgreSQL | `coloc` |
| `DJANGO_DB_PASSWORD` | Mot de passe PostgreSQL | `coloc` |
| `DJANGO_DB_HOST` | Hôte PostgreSQL | `db` |
| `DJANGO_DB_PORT` | Port PostgreSQL | `5432` |
| `QR_HOST_IP` | IP forcée dans l'URL encodée par le QR code d'upload | aucune (utilise l'hôte de la requête) |
| `GOOGLE_OAUTH_CLIENT_SECRET_FILE` | Chemin vers le fichier de credentials OAuth (Desktop app) téléchargé depuis Google Cloud Console | aucune |
| `GOOGLE_OAUTH_TOKEN_FILE` | Chemin vers le token OAuth généré par `manage.py google_drive_auth` (contient le refresh token) | aucune |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | ID du dossier Drive racine sous lequel chaque soirée crée son sous-dossier | aucune (obligatoire si Drive activé) |
