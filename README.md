# Bootcamp Security Logs API

API FastAPI qui valide des evenements techniques, les stocke dans PostgreSQL et produit une analyse structuree avec un fournisseur IA.

## 1. Installation

Prerequis: Docker Desktop demarre.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Ouvrir ensuite Swagger: <http://localhost:8000/docs>

Arreter les conteneurs:

```powershell
docker compose down
```

Supprimer aussi les donnees PostgreSQL:

```powershell
docker compose down -v
```

## 2. Demonstration Swagger

1. `GET /health` confirme que l'API fonctionne.
2. `POST /events` avec cet exemple:

```json
{
  "source": "web-server",
  "event_type": "failed_login",
  "severity": "high",
  "message": "Five failed login attempts for admin",
  "ip_address": "203.0.113.10",
  "metadata": {"username": "admin", "attempts": 5}
}
```

3. `POST /analyze-text` analyse directement le texte fourni et genere automatiquement l'identifiant en base.
4. `POST /analyze-recent?limit=10` analyse les 10 derniers evenements avec DeepSeek.
5. `GET /alerts` affiche les alertes persistantes.

Pour analyser directement une phrase sans connaitre d'identifiant, utiliser `POST /analyze-text` avec:

```json
{
  "text": "Plusieurs tentatives de connexion echouees depuis une adresse IP externe"
}
```

Cette route cree et conserve automatiquement l'evenement avant son analyse.

Pour analyser les derniers logs deja importes, utiliser `POST /analyze-recent` avec un parametre `limit`, par exemple `limit=20`. La limite est comprise entre 1 et 100.

Le fournisseur par defaut est DeepSeek. Mettre la cle dans `DEEPSEEK_API_KEY` dans `.env` et conserver `AI_PROVIDER=deepseek`. Le modele utilise par defaut est `deepseek-chat`. Pour tester sans cle, utiliser temporairement `AI_PROVIDER=mock`. Pour Ollama, mettre `AI_PROVIDER=ollama` et verifier que le service Ollama est accessible.

## 3. Architecture reseau

Les conteneurs `api` et `db` sont sur le reseau Docker `bootcamp_net`. L'API joint PostgreSQL avec le nom de service `db`, jamais avec `localhost`. Le port PostgreSQL n'est pas expose sur l'hote; seul le port Swagger `8000` l'est.

## 4. Formats d'ingestion

`POST /ingest` accepte un JSON (objet ou liste d'objets) ou un CSV avec les colonnes `source,event_type,severity,message,ip_address,metadata`. Les lignes invalides sont rejetees sans arreter les lignes valides.

## 5. Points securite presentes

- validation stricte des champs avec Pydantic;
- limite de taille des champs texte et du parametre `limit`;
- secrets dans `.env`, ignore par Git;
- requetes SQLAlchemy parametrees;
- base non exposee directement sur l'hote;
- fournisseur IA selectionnable sans modifier le code.

## 6. Brancher les logs Windows

Avec Docker demarre, lancer PowerShell dans le dossier du projet:

```powershell
.\scripts\send-windows-logs.ps1 -Count 50
```

Le script lit les 50 derniers evenements du journal Windows `System`, les convertit en JSON et les envoie a `POST /ingest`. Pour importer davantage d'evenements:

```powershell
.\scripts\send-windows-logs.ps1 -Count 200
```

L'import stocke les logs dans PostgreSQL. Pour analyser ensuite un message, utiliser `POST /analyze-text` dans Swagger. L'automatisation continue peut etre ajoutee avec le Planificateur de taches Windows.
