# Outil d'Automatisation de Propositions

Cet outil permet d'automatiser la création de propositions commerciales sous forme de présentations PowerPoint (PPTX).

## Fonctionnalités

- Interface web moderne avec authentification utilisateur
- Génération automatique d'un fichier PPTX avec une slide de titre et une slide de contenu
- Stockage des propositions dans MongoDB
- Gestion des utilisateurs avec inscription/connexion
- Téléchargement direct des présentations générées

## Architecture

- **Backend** : Flask (Python) avec MongoDB, JWT pour l'authentification, python-pptx pour la génération
- **Frontend** : Vue.js 3 avec Vite, interface responsive

## Prérequis

- Python 3.8+
- Node.js 16+
- MongoDB (local ou MongoDB Atlas)
- MongoDB Compass (pour la gestion visuelle de la base de données)

## Installation

### 1. MongoDB

#### Installation locale :
- Téléchargez et installez MongoDB Community Server depuis [mongodb.com](https://www.mongodb.com/try/download/community)
- Installez MongoDB Compass depuis [mongodb.com](https://www.mongodb.com/try/download/compass)

#### Ou utilisez MongoDB Atlas (cloud) :
- Créez un compte sur [MongoDB Atlas](https://www.mongodb.com/atlas)
- Créez un cluster gratuit
- Obtenez l'URI de connexion

### 2. Backend

1. Allez dans le dossier `backend/`
2. Créez un environnement virtuel : `python -m venv virtualenv`
3. Activez l'environnement :
   - Windows : `virtualenv\Scripts\activate`
   - Linux/Mac : `source virtualenv/bin/activate`
4. Installez les dépendances : `pip install -r requirements.txt`
5. Configurez les variables d'environnement :
   - Copiez `.env.example` vers `.env`
   - Modifiez `MONGO_URI` avec votre URI MongoDB
   - Changez `JWT_SECRET_KEY` pour un secret sécurisé

### 3. Frontend

1. Allez dans le dossier `frontend/`
2. Installez les dépendances : `npm install`

## Utilisation

1. **Démarrez MongoDB** :
   - Si local : Lancez MongoDB service
   - Ouvrez MongoDB Compass et connectez-vous

2. **Lancez le backend** :
   - Dans `backend/` : `python app.py`
   - Le serveur démarre sur http://localhost:5000

3. **Lancez le frontend** :
   - Dans `frontend/` : `npm run dev`
   - Ouvrez http://localhost:5173 dans votre navigateur

4. **Utilisation de l'application** :
   - Créez un compte ou connectez-vous
   - Créez une nouvelle proposition avec titre et contenu
   - Téléchargez la présentation PPTX générée
   - Consultez vos propositions dans le dashboard

## Configuration

### Variables d'environnement (backend/.env)

```env
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/propalepptx
JWT_SECRET_KEY=votre-cle-secrete-jwt

# Email Configuration (optionnel)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=votre-email@gmail.com
MAIL_PASSWORD=votre-mot-de-passe-app
```

## API Endpoints

### Authentification
- `POST /api/auth/register` - Inscription utilisateur
- `POST /api/auth/login` - Connexion utilisateur

### Propositions
- `GET /api/proposals` - Liste des propositions de l'utilisateur (authentifié)
- `POST /api/generate_proposal` - Générer une nouvelle proposition (authentifié)

### Fichiers
- `GET /api/download/<filename>` - Télécharger un fichier PPTX

## Sécurité

- Mots de passe hashés avec bcrypt
- Authentification JWT
- Validation des entrées utilisateur
- Protection CORS

## Développement

- Le backend expose une API REST sur http://localhost:5000
- Le frontend proxy les requêtes `/api` vers le backend
- Les fichiers PPTX sont stockés dans `backend/uploads/`

## Structure de la base de données

### Collection `users`
```json
{
  "_id": "ObjectId",
  "email": "string",
  "password": "string (hashed)",
  "name": "string",
  "created_at": "datetime",
  "is_active": "boolean"
}
```

### Collection `proposals`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "title": "string",
  "content": "string",
  "pptx_url": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```