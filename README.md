# Platefrom_coloc — Mur de photos pour événements

Application web permettant aux invités d'un événement (soirée, anniversaire, fête de coloc...) d'envoyer des photos depuis leur téléphone et de les voir apparaître en temps réel sous forme de diaporama sur une télévision ou un écran connecté. Aucun compte à créer : chacun choisit un pseudo, scanne un QR code affiché sur l'écran, et ses photos apparaissent quasi instantanément pour tout le monde.

## Présentation générale

### Comment ça marche
1. Depuis le dashboard staff, un administrateur crée ou active l'**évènement** ("soirée") du moment — chaque évènement a ses propres invités, photos et dossier Drive, et un seul est actif à la fois.
2. L'écran TV affiche la page `/tv/` avec un QR code visible en permanence, pointant vers l'évènement actif.
3. Un invité scanne le QR code avec son téléphone et arrive sur la page de choix de pseudo.
4. Il choisit un pseudo (mémorisé pour sa session, pas de mot de passe), puis peut laisser son email pour recevoir un accès en lecture au dossier Drive de la soirée (étape facultative, "Skip" possible).
5. Il accède à la page d'upload et envoie une ou plusieurs photos, prises sur le moment ou depuis sa galerie.
6. Les photos apparaissent en direct (WebSocket) sur l'écran TV : une bannière "Nouvelle photo de X" s'affiche, puis la photo rejoint le diaporama tournant. Chaque photo est aussi copiée dans le dossier Drive de l'évènement actif.
7. Les invités peuvent aussi parcourir une galerie de toutes les photos et les liker ; le top 3 des photos les plus aimées s'affiche en direct sur l'écran TV.
8. Chacun peut consulter "Mes photos" et supprimer ses propres envois.
9. Un administrateur peut ajuster la vitesse du diaporama, gérer les évènements et piloter les fonctionnalités optionnelles (Drive, partage, likes, whiteboard) depuis le dashboard staff, avec effet immédiat.
10. Si le whiteboard est activé, les invités peuvent dessiner sur un tableau collectif depuis leur téléphone ; leurs envois s'empilent sur un même tableau, affichable en direct sur l'écran TV.

> À terme, l'objectif est une app entièrement personnalisable par évènement depuis le dashboard : activer ou non le classement des likes, l'intégration Drive, un chat, un tableau blanc collectif, etc. Le classement des likes, l'intégration Drive et le whiteboard collectif sont les premières briques de ce système de fonctionnalités optionnelles ; la gestion multi-évènements en est le second étage.

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
Puis ouvrir **http://localhost:8000/setup/** et suivre l'assistant de configuration : création du
compte admin, connexion Google Drive (optionnelle, entièrement depuis le navigateur — plus besoin
d'éditer de fichier ni de lancer de commande), confirmation de l'adresse réseau, création de la
première soirée. Une fois terminé :
- Application : http://localhost:8000
- Écran TV : http://localhost:8000/tv/
- Admin Django : http://localhost:8000/admin/
- Dashboard staff : http://localhost:8000/dashboard/

L'assistant n'est accessible que tant qu'aucun compte admin n'existe (ou en étant déjà connecté en
tant qu'admin, pour reprendre une étape sautée) — personne d'autre sur le réseau ne peut le relancer
une fois la configuration faite.

<details>
<summary>Configuration manuelle (optionnelle, pour les cas non couverts par l'assistant)</summary>

Tout ce que fait l'assistant reste aussi réglable à la main si besoin :

- **Compte admin** : `docker compose exec web python manage.py createsuperuser`
- **Adresse réseau du QR code** : réglable depuis `/admin/` (modèle "Site settings"), ou en forçant
  la variable d'environnement `QR_HOST_IP` (prioritaire sur la valeur en base) dans `.env`,
  renseignée automatiquement par un script qui détecte l'IP LAN de la machine :
  - **Windows (PowerShell)** : `.\scripts\update-lan-ip.ps1` puis `docker compose up -d`, ou en une
    seule commande `.\scripts\start.ps1`
  - **macOS / Linux (bash)** : `./scripts/update-lan-ip.sh` puis `docker compose up -d`, ou en une
    seule commande `./scripts/start.sh`

  À relancer après un changement de réseau (nouvelle box, nouveau Wi-Fi, renouvellement DHCP).
- **Google Drive** : voir ci-dessous, section CLI.
</details>

### Configuration de l'intégration Google Drive (optionnelle)

L'app peut copier chaque photo envoyée vers un dossier Google Drive dédié à l'évènement actif, et
proposer aux invités de partager ce dossier vers leur email. C'est entièrement optionnel : un
évènement peut être créé/activé sans dossier Drive connecté (ses photos restent alors uniquement
sur le serveur). L'authentification se fait via **OAuth2 sur un compte Google personnel** (et non
un compte de service) : un compte de service Google n'a aucun quota de stockage Drive propre en
dehors d'un Drive Partagé, une fonctionnalité réservée aux comptes Google Workspace payants —
inutilisable avec un Gmail personnel gratuit.

**Depuis l'assistant `/setup/`** (recommandé) — l'étape "Google Drive" guide dans l'ordre :

> ⚠️ Google refuse toute adresse de redirection OAuth en `http://` non-HTTPS, sauf si l'hôte est
> exactement `localhost`/`127.0.0.1` (une IP locale comme `192.168.1.13` est rejetée même
> enregistrée à l'identique — erreur `redirect_uri_mismatch`). L'étape "Connecter mon compte
> Google" doit donc se faire depuis un navigateur **sur la machine qui héberge le serveur**
> (`http://localhost:8000/setup/drive/`), pas depuis votre téléphone — l'assistant l'indique
> automatiquement si ce n'est pas déjà le cas. Toutes les autres étapes du wizard restent
> utilisables depuis n'importe quel appareil du réseau.

1. Créer un projet sur [console.cloud.google.com](https://console.cloud.google.com) et activer
   l'**API Google Drive**.
2. Configurer l'écran de consentement OAuth (type "External", vous ajouter comme "Test user").
3. Créer des identifiants OAuth de type **Web application** (pas "Desktop app" — l'assistant utilise
   une vraie redirection web, pas un flux local) et coller l'adresse de redirection affichée par
   l'assistant (toujours basée sur `localhost`, voir avertissement ci-dessus) dans "Authorized
   redirect URIs".
4. Télécharger le fichier JSON généré et l'envoyer directement dans le formulaire de l'assistant.
5. Depuis `http://localhost:8000/setup/drive/`, cliquer "Connecter mon compte Google", puis
   choisir ou créer le dossier Drive racine — tout
   depuis le navigateur, aucun fichier à placer ni ID à copier-coller à la main.

<details>
<summary>Alternative en ligne de commande (pour qui préfère, ou pour un rattachement après coup)</summary>

Cette méthode reste disponible et fait exactement la même chose, fichiers en plus :

1. Suivre les étapes 1-2 ci-dessus, mais créer des identifiants de type **Desktop app** cette fois.
   Télécharger le JSON et le placer dans `credentials/client_secret.json` (dossier ignoré par git).
2. Créer un dossier racine dans votre Drive, récupérer son ID dans l'URL
   (`https://drive.google.com/drive/folders/<ID>`), et le renseigner dans
   `GOOGLE_DRIVE_ROOT_FOLDER_ID` (dans `.env` ou `docker-compose.yml` — prioritaire sur la valeur
   choisie via l'assistant si les deux sont définis).
3. Lancer l'autorisation, en local hors conteneur (un navigateur doit s'ouvrir) :
   ```
   pip install -r requirements.txt
   GOOGLE_OAUTH_CLIENT_SECRET_FILE=credentials/client_secret.json GOOGLE_OAUTH_TOKEN_FILE=credentials/token.json python manage.py google_drive_auth
   ```
   Écrit le refresh token dans `credentials/token.json`, monté dans le conteneur `web` et
   réutilisé/rafraîchi automatiquement ensuite.
4. Depuis le dashboard staff (`/dashboard/`), créer un évènement : son dossier Drive est
   automatiquement créé (ou retrouvé) sous le dossier racine.
</details>

## Spécification fonctionnelle

### Acteurs
- **Invité** : aucun compte, identifié uniquement par un pseudo lié à sa session navigateur **et à l'évènement actif au moment où il rejoint** — un même pseudo peut être repris à un évènement suivant
- **Écran TV** : client passif qui affiche le flux de photos de l'évènement actif en direct
- **Administrateur** : compte staff Django ; pilote les évènements et la soirée depuis le dashboard staff (`/dashboard/`) — `/admin/` reste accessible mais n'est plus l'interface utilisée au quotidien

### Parcours et écrans

#### 1. Choix du pseudo — `/pseudo/`
- Si aucun évènement n'est actif, affiche une page d'attente ("No event is live right now") au lieu du formulaire
- Formulaire à un champ (nom, 50 caractères max)
- Le pseudo doit être unique **au sein de l'évènement actif**, insensible à la casse ; en cas de conflit, message d'erreur invitant à en choisir un autre — le même pseudo redevient disponible dès qu'on change d'évènement
- Une fois validé, le pseudo est associé à la session Django et à l'évènement actif (table `UserIdentity`, liée à la clé de session + à l'évènement) et stocké en session
- Si la session correspond déjà à une identité de l'évènement actif, redirection automatique vers `/upload/` (une session d'un évènement précédent, désormais inactif, ne compte pas : le pseudo est redemandé)
- Lien direct vers la galerie sans avoir à choisir de pseudo
- Une fois le pseudo validé, redirection systématique vers l'étape de partage Drive (`/pseudo/share-drive/`) — chaque évènement a toujours un dossier Drive connecté

#### 2. Partage du dossier Drive — `/pseudo/share-drive/`
- Propose un champ email facultatif, avec un bouton "Share with me" et un bouton "Skip"
- Si un email est renseigné, l'email est toujours enregistré (`UserIdentity.email`), mais l'accès réel au dossier dépend du toggle global "Share Drive with participants" (voir dashboard) :
  - Si le partage est actuellement **activé** : l'adresse est immédiatement ajoutée en lecteur ("reader") sur le dossier Drive, avec notification par email envoyée par Google ; l'ID de la permission créée est conservé (`UserIdentity.drive_permission_id`) pour pouvoir la révoquer plus tard
  - Si le partage est actuellement **désactivé** : un test silencieux (octroi puis révocation immédiate d'une permission, sans notification) vérifie que cette adresse pourra bien être partagée le moment venu, sans lui laisser d'accès réel ; l'invité est averti en cas d'échec
- En cas d'échec de l'appel à l'API Drive (partage ou test), un message d'erreur s'affiche et l'invité peut réessayer ou continuer sans partage
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

#### 4. Whiteboard — `/whiteboard/`
- Visible depuis `/upload/` uniquement quand la fonctionnalité "Whiteboard" est activée pour l'évènement actif (bouton "🎨 Whiteboard") ; sinon la page redirige vers l'écran d'attente si on y accède directement
- Le tableau est au format 4/3 (1200×900 px en interne, affiché de façon responsive)
- Deux calques superposés : le tableau collectif actuel en arrière-plan (lecture seule, sert de repère visuel et de source pour la pipette), et un calque transparent au premier plan où l'invité dessine réellement
- Stylo à taille réglable, de 1px jusqu'à 1/10 de la largeur du tableau (120px)
- Deux modes de couleur :
  - **Simple** : 5 couleurs prédéfinies (noir, blanc, bleu, vert, rouge)
  - **Artiste** : palette complète (sélecteur de couleur natif) + pipette, qui récupère la couleur à l'endroit cliqué sur le tableau (arrière-plan + propre dessin en cours)
  - Bouton "Clear" pour effacer son dessin en cours avant envoi (sans toucher au tableau collectif)
- Le tableau collectif n'est **pas** mis à jour en direct pendant que l'invité dessine : rien n'est envoyé tant qu'il n'a pas cliqué sur "Add to the whiteboard"
- À l'envoi, seul le calque transparent (le dessin de l'invité, pas l'arrière-plan) est exporté en PNG et envoyé au serveur, qui le superpose sur le tableau collectif existant ; tous les écrans TV en mode whiteboard sont notifiés en direct via WebSocket
- Un invité doit attendre 30 secondes entre deux envois ; le bouton d'envoi affiche un compte à rebours et reste désactivé pendant ce délai

#### 5. Mes photos — `/my-photos/`
- Accessible uniquement avec un pseudo en session
- Liste, par ordre chronologique, des photos envoyées par l'utilisateur courant
- Suppression possible photo par photo ; un utilisateur ne peut supprimer que ses propres photos de son évènement (vérifié par évènement + pseudo + identifiant, pas seulement par session)
- La suppression efface le fichier physique, retire la photo de la corbeille Drive si elle y avait été copiée, et notifie l'écran TV en direct pour retirer la photo du diaporama en cours

#### 6. Écran TV — `/tv/`
- Page plein écran destinée à un téléviseur ou un moniteur connecté, sans interaction attendue
- Le rectangle principal affiche soit le diaporama photo, soit le whiteboard collectif, selon le réglage "TV layout" choisi dans le dashboard pour l'évènement actif
- **Mode diaporama** (par défaut) :
  - Au chargement, récupère la liste actuelle des photos et l'intervalle du diaporama
  - Diaporama automatique en fondu enchaîné, intervalle configurable (5 secondes par défaut)
  - Message "Waiting for photos…" tant qu'aucune photo n'a été envoyée
  - Bannière "New photo from &lt;pseudo&gt;" : à chaque upload, une superposition centrale annonce la nouvelle photo pendant 3 secondes ; les annonces sont mises en file si plusieurs photos arrivent en même temps, indépendamment du cycle du diaporama de fond
  - Classement latéral (leaderboard) du top 3 des photos les plus likées, mis à jour en direct
- **Mode whiteboard** : affiche l'image composite du tableau collectif de l'évènement actif, mise à jour en direct (sans rechargement) à chaque nouveau dessin ajouté ; message "Waiting for drawings…" tant qu'aucun dessin n'a été envoyé
- QR code permanent pointant vers `/upload/`, pour que tout nouvel invité puisse rejoindre à tout moment, quel que soit le mode affiché — accompagné, si le QR Wi-Fi est activé pour l'évènement actif (dashboard, onglet "Optional features"), d'un second QR code juste à sa gauche pour rejoindre le Wi-Fi (nécessaire de toute façon : un invité ne peut pas atteindre l'IP locale du serveur avant d'être sur le même réseau)
- Changer de layout depuis le dashboard notifie l'écran TV via WebSocket, qui réinterroge ses réglages et bascule instantanément entre les deux modes, sans rechargement de page
- Connexion WebSocket permanente, avec reconnexion automatique toutes les 3 secondes en cas de coupure

#### 7. Galerie — `/gallery/`
- Page publique, accessible sans avoir choisi de pseudo
- Affiche toutes les photos de tous les invités, les plus récentes en premier
- Chaque photo peut être likée / unlikée (cœur cliquable, bascule)
- Aimer une photo nécessite une identité de session valide (donc d'être passé par le choix de pseudo au préalable) ; sinon la tentative échoue
- Chaque like/unlike met à jour en direct le classement affiché sur l'écran TV

#### 8. QR code d'upload — `/qr/upload.png`
- Génère à la volée une image PNG encodant l'URL absolue de la page `/upload/`
- Priorité de l'adresse encodée : la variable d'environnement `QR_HOST_IP` si définie, sinon `SiteSettings.server_host` (réglé par l'assistant `/setup/` ou `/admin/`), sinon le nom d'hôte de la requête. Ce mécanisme garantit que le QR code reste scannable sur le réseau local du logement même quand le serveur tourne dans un conteneur (typiquement l'écran TV charge `/tv/` via `localhost`, ce qui donnerait un QR code inutilisable pour un téléphone sans ça).

#### 8bis. QR code Wi-Fi — `/qr/wifi.png`
- Génère à la volée une image PNG au format standard `WIFI:T:<sécurité>;S:<SSID>;P:<mot de passe>;;`, reconnu nativement par l'appareil photo d'iOS et d'Android (propose directement "Rejoindre le réseau" au scan)
- Configuré par évènement (pas globalement) depuis le dashboard staff, onglet "Optional features" : nom du réseau (SSID), mot de passe, type de sécurité (`WPA`/`WPA2`/`WPA3`, `WEP`, ou réseau ouvert), plus un interrupteur séparé pour activer/désactiver l'affichage sur l'écran TV — les infos peuvent être enregistrées sans activer le QR code tout de suite, et un aperçu du QR code s'affiche dans le dashboard une fois activé, pour vérifier qu'il est correct avant de le montrer aux invités
- Renvoie une 404 si le QR Wi-Fi n'est pas activé pour l'évènement actif (ou si aucun SSID n'est renseigné) — dans ce cas l'écran TV n'affiche que le QR code d'upload, comme avant
- Un unique QR code qui rejoindrait le Wi-Fi **puis** ouvrirait l'app n'est pas réalisable : les QR codes `WIFI:` et les QR codes URL sont deux types d'action distincts et mutuellement exclusifs pour l'appareil photo du téléphone, il n'existe pas de format standard qui enchaîne les deux. D'où deux QR codes séparés, affichés côte à côte sur `/tv/`.

#### 9. Administration — `/admin/`
- Interface Django Admin standard, gardée comme filet de secours technique — l'usage courant se fait depuis le dashboard staff (section suivante)
- **Photos** : consultation, filtrage par évènement/pseudo
- **Identités** (`UserIdentity`) : évènement, pseudo, email (si renseigné pour le partage Drive), statut de partage, session, date de création
- **Likes** : consultation des likes posés
- **Réglages du diaporama** (`SlideshowSettings`, entrée unique, global à tous les évènements) : intervalle d'affichage en secondes (de 0,1 à 100) ; toute modification est propagée en direct à l'écran TV sans rechargement
- **Events** (`Event`, une entrée par évènement) : nom, actif ou non, dossier Drive (ID en lecture seule), partage Drive, likes — les mêmes réglages que dans le dashboard, exposés ici en secours

#### 10. Dashboard staff — `/dashboard/`
Page dédiée, distincte de `/admin/`, réservée au staff (`staff_member_required` ; redirection vers l'écran de connexion Django si non authentifié). C'est le point d'entrée unique pour piloter une soirée.

La page est organisée en onglets (CSS pur, sans JavaScript) : **Events**, **Optional features**, **TV layout**, **Whiteboard**, **Guests**, **Photos**. L'onglet actif est conservé après chaque action grâce à un paramètre `?tab=` porté par la redirection qui suit chaque soumission de formulaire.

- **Events** : liste de tous les évènements créés (nom, badge ACTIVE, nombre de photos, lien vers le dossier Drive), avec un bouton "Switch to this event" pour chacun des évènements inactifs
  - **Créer un évènement** : formulaire avec un champ nom ; si Drive est configuré, son dossier est immédiatement recherché/créé sous le dossier racine configuré (voir `GOOGLE_DRIVE_ROOT_FOLDER_ID`) — sinon l'évènement est créé/activable sans dossier Drive, ses photos restant uniquement sur le serveur
  - Si un évènement du même nom existe déjà, il est réutilisé plutôt que dupliqué
- **Changer d'évènement actif — confirmation obligatoire** (`/dashboard/events/<id>/switch/`) : avant tout changement, une page de confirmation dédiée s'affiche pour éviter toute perte de données :
  - Elle affiche le nombre de photos de l'évènement actif actuel et combien d'entre elles ne sont **pas encore** sauvegardées sur Drive
  - Si des photos ne sont pas sauvegardées, le bouton de confirmation est masqué : seul un bouton "Back up the N missing photo(s) now" est proposé, qui relance l'upload Drive des photos manquantes puis réaffiche la page
  - Le changement ne devient possible qu'une fois toutes les photos de l'évènement sortant confirmées sur Drive (bandeau vert "Safe to switch")
  - Au moment du switch effectif : si l'évènement sortant a un dossier Drive connecté, ses photos locales sont **supprimées du disque et de la base** (sans danger, puisqu'elles viennent d'être confirmées sur Drive) — sinon (Drive non configuré pour cet évènement) elles sont **laissées en place**, simplement masquées tant que cet évènement n'est pas réactivé (aucune sauvegarde externe à cette exception près). Puis toutes les photos du dossier Drive du nouvel évènement actif, s'il en a un, sont **téléchargées** localement (pseudo reconstitué depuis le nom de fichier `<pseudo>_<HHhMM>_<uuid>.<ext>`) — Drive fait office de stockage durable quand il est connecté, le local reste dans tous les cas le cache de travail de l'évènement en cours
  - Rien n'est jamais perdu : la suppression locale d'un évènement sortant n'est déclenchée qu'une fois toutes ses photos confirmées sur Drive (cf. garde-fou ci-dessus), et sa copie Drive n'est elle-même jamais touchée par ce nettoyage local
  - Une fois le switch effectué, tous les écrans TV connectés sont notifiés via WebSocket et rechargent automatiquement la page pour refléter le nouvel évènement
- **Réglages de l'évènement actif** :
  - **Google Drive backup** : optionnel ; si connecté pour l'évènement actif, affiche le lien vers le dossier, ou un message d'erreur si le dossier a été supprimé/est injoignable avec un bouton pour en recréer un neuf (les photos locales non confirmées y sont aussitôt re-uploadées) ; si non connecté, un bouton permet d'en connecter un à tout moment
  - **Share Drive with participants** (toggle) :
    - Activé → tous les invités de l'évènement actif ayant renseigné un email sont ajoutés en lecteur sur le dossier (ceux qui l'ont déjà ne sont pas re-partagés)
    - Désactivé → l'accès est révoqué pour tous les invités actuellement partagés (`drive_permission_id` utilisé pour cibler la permission exacte à supprimer, puis effacé)
    - Le panneau affiche le nombre d'invités actuellement partagés sur le nombre total ayant un email
  - **Photo likes** (toggle) : le changement d'état est propagé en direct à l'écran TV via WebSocket (masque/affiche le classement sans rechargement)
  - **Whiteboard** (toggle) : active/désactive le bouton "Whiteboard" sur `/upload/` pour les invités de l'évènement actif ; le désactiver alors que l'écran TV est en mode whiteboard bascule automatiquement ce dernier en mode diaporama
- **TV layout** : deux cartes cliquables ("Photo slideshow" / "Collective whiteboard") pour choisir ce qu'affiche le rectangle principal de l'écran TV pour l'évènement actif ; la carte whiteboard est désactivée tant que la fonctionnalité Whiteboard n'est pas activée ; tout changement est propagé en direct à l'écran TV via WebSocket
- **Whiteboard** : aperçu de l'image composite actuelle du tableau collectif, et historique de tous les dessins envoyés (pseudo, heure d'envoi) avec un bouton de suppression individuel ; supprimer un dessin recalcule entièrement le tableau composite à partir des dessins restants (dans l'ordre chronologique) et notifie l'écran TV
- **Invités** : tableau pseudo / email / statut de partage Drive / date d'arrivée, filtré sur l'évènement actif uniquement
- **Photos** : grille des photos de l'évènement actif avec suppression en un clic (n'importe quelle photo, pas seulement les siennes — contrairement à "Mes photos") ; comme pour une suppression par son auteur, la photo est aussi retirée (mise à la corbeille) du dossier Drive si elle y avait été copiée

### API interne (JSON)
| Endpoint | Méthode | Description |
|---|---|---|
| `/api/photos/` | GET | Liste toutes les photos (id, url, pseudo, date, nombre de likes, statut liké pour l'utilisateur courant) |
| `/api/photos/<id>/like/` | POST | Bascule le like/unlike pour l'utilisateur de la session courante ; 403 si les likes sont désactivés |
| `/api/settings/` | GET | Intervalle du diaporama, statut des likes, layout TV actif et URL de l'image du tableau (`interval_seconds`, `likes_enabled`, `tv_layout`, `whiteboard_image_url`) |
| `/whiteboard/upload/` | POST | Envoie le calque dessiné (PNG transparent, champ `drawing`) ; 403 si le whiteboard est désactivé ou sans identité, 429 avec `retry_after` si le délai de 30s n'est pas écoulé |

### Canal temps réel — `/ws/tv/`
Un unique canal WebSocket diffuse à tous les écrans TV connectés :
- `uploaded` — nouvelle photo envoyée (données complètes)
- `deleted` — une photo a été supprimée (url concernée)
- `settings` — l'intervalle du diaporama a changé
- `liked` — le nombre de likes d'une photo a changé
- `likes_setting` — les likes ont été activés/désactivés (affiche ou masque le classement sur l'écran TV)
- `whiteboard_updated` — le tableau collectif a changé (nouveau dessin ajouté, ou dessin supprimé depuis le dashboard) ; porte la nouvelle URL de l'image composite
- `tv_layout_changed` — le layout TV de l'évènement actif a changé ; l'écran TV réinterroge `/api/settings/` et bascule entre diaporama et whiteboard sans rechargement complet
- `event_switched` — l'évènement actif a changé ; l'écran TV recharge entièrement la page pour repartir sur les nouvelles photos/réglages

### Modèle de données
- **Event** — un évènement/soirée : nom (unique), statut actif (un seul à la fois), dossier Drive (ID/lien), partage Drive actif ou non, likes activés ou non, whiteboard activé ou non, layout TV (`slideshow` ou `whiteboard`), image composite du tableau collectif, QR Wi-Fi activé ou non avec ses SSID/mot de passe/type de sécurité, date de création. Racine de tout le reste : photos, invités et dessins lui appartiennent
- **Photo** — évènement, pseudo de l'auteur, fichier image, date d'envoi, ID du fichier Drive correspondant si copié (`drive_file_id`)
- **WhiteboardDrawing** — évènement, pseudo de l'auteur, calque PNG transparent envoyé, date d'envoi ; chaque ligne est un calque individuel du tableau collectif, conservé séparément (et non fondu directement dans le composite) pour permettre la suppression ciblée d'un seul dessin
- **UserIdentity** — évènement, pseudo et clé de session (uniques *au sein de l'évènement*, pas globalement), email (facultatif, pour le partage Drive), statut de partage Drive et ID de la permission Drive accordée (`drive_permission_id`, pour pouvoir la révoquer précisément), date de création ; fait office d'identité légère sans mot de passe
- **Like** — association Photo ↔ UserIdentity (unique par paire), date
- **SlideshowSettings** — entrée unique, intervalle d'affichage du diaporama en secondes, partagé par tous les évènements

### Règles métier notables
- Aucune authentification classique : l'identité d'un invité repose entièrement sur sa session navigateur associée à un pseudo, unique au sein de l'évènement auquel il a rejoint
- Un pseudo ne peut être utilisé que par une seule session à la fois, mais redevient disponible dans un autre évènement
- Une photo ne peut être supprimée que par son auteur, dans son évènement (vérifié par évènement + pseudo + identifiant de la photo)
- Toute mutation (envoi, suppression, like, changement de réglage, changement d'évènement) est répercutée en temps réel sur l'écran TV via WebSocket, sans rechargement de page manuel
- En mode développement (`DEBUG=True`, valeur par défaut du projet), les fichiers médias sont servis directement par Django
- Un évènement ne peut pas être créé ou activé sans dossier Drive connecté ; l'upload d'une photo vers Drive est best-effort (une erreur ponctuelle est journalisée côté serveur sans jamais bloquer l'upload local ni l'affichage sur l'écran TV), mais le passage à un autre évènement est lui explicitement bloqué tant que toutes les photos de l'évènement sortant ne sont pas confirmées sur Drive — c'est le garde-fou contre la perte de données
- Changer d'évènement supprime les photos locales de l'évènement sortant (déjà confirmées sur Drive au préalable) et retélécharge celles de l'évènement entrant depuis son propre dossier Drive : le stockage local ne reflète toujours que l'évènement actif, Drive reste la copie durable de tous les évènements
- Le tableau collectif n'est jamais fusionné en une seule fois de façon définitive : chaque dessin reste un calque à part (`WhiteboardDrawing`), et l'image composite affichée est recalculée depuis zéro (tous les calques restants, du plus ancien au plus récent) à chaque suppression — c'est ce qui permet de retirer un seul dessin sans perdre les autres
- Le délai de 30 secondes entre deux envois de dessin est appliqué par pseudo et par évènement, vérifié côté serveur (pas seulement dans l'interface)

## Configuration (variables d'environnement)
| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django | clé de développement en dur dans le code |
| `DJANGO_DB_NAME` | Nom de la base PostgreSQL | `coloc_photos` |
| `DJANGO_DB_USER` | Utilisateur PostgreSQL | `coloc` |
| `DJANGO_DB_PASSWORD` | Mot de passe PostgreSQL | `coloc` |
| `DJANGO_DB_HOST` | Hôte PostgreSQL | `db` |
| `DJANGO_DB_PORT` | Port PostgreSQL | `5432` |
| `QR_HOST_IP` | IP forcée dans l'URL encodée par le QR code d'upload — prioritaire sur la valeur "Site settings" réglée par l'assistant `/setup/` ou `/admin/` | aucune (utilise "Site settings", sinon l'hôte de la requête) |
| `GOOGLE_OAUTH_CLIENT_SECRET_FILE` | Chemin vers le fichier de credentials OAuth téléchargé depuis Google Cloud Console (écrit automatiquement par l'assistant `/setup/`, ou placé à la main) | aucune |
| `GOOGLE_OAUTH_TOKEN_FILE` | Chemin vers le token OAuth (contient le refresh token), écrit par l'assistant `/setup/` ou par `manage.py google_drive_auth` | aucune |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | ID du dossier Drive racine sous lequel chaque soirée crée son sous-dossier — prioritaire sur la valeur "Site settings" choisie via l'assistant `/setup/` | aucune (Drive désactivé si ni l'un ni l'autre n'est défini) |
