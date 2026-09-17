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

## 2. Architecture du projet

```text
app/
  main.py     routes FastAPI (events, ingestion, analyse, alertes)
  models.py   modeles SQLAlchemy (Event, Analysis)
  schemas.py  schemas Pydantic (validation entree/sortie)
  ai.py       appel du fournisseur IA (deepseek, ollama, mock)
  db.py       moteur SQLAlchemy et session
  config.py   configuration via variables d'environnement (.env)
tests/        tests unitaires pytest
scripts/      scripts PowerShell (import des logs Windows)
```

L'API est sans etat: chaque requete ouvre une session SQLAlchemy via `get_db`, et le fournisseur IA est resolu a l'execution depuis `AI_PROVIDER` (voir section 4).

## 3. Demonstration Swagger

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

## 4. Fournisseur IA

Le fournisseur par defaut est DeepSeek. Mettre la cle dans `DEEPSEEK_API_KEY` dans `.env` et conserver `AI_PROVIDER=deepseek`. Le modele utilise par defaut est `deepseek-chat`. Pour tester sans cle, utiliser temporairement `AI_PROVIDER=mock`. Pour Ollama, mettre `AI_PROVIDER=ollama` et verifier que le service Ollama est accessible.

## 5. Architecture reseau

Les conteneurs `api` et `db` sont sur le reseau Docker `bootcamp_net`. L'API joint PostgreSQL avec le nom de service `db`, jamais avec `localhost`. Le port PostgreSQL n'est pas expose sur l'hote; seul le port Swagger `8000` l'est.

## 6. Formats d'ingestion

`POST /ingest` accepte un JSON (objet ou liste d'objets) ou un CSV avec les colonnes `source,event_type,severity,message,ip_address,metadata`. Les lignes invalides sont rejetees sans arreter les lignes valides.

## 7. Points securite presentes

- validation stricte des champs avec Pydantic;
- limite de taille des champs texte et du parametre `limit`;
- secrets dans `.env`, ignore par Git;
- requetes SQLAlchemy parametrees;
- base non exposee directement sur l'hote;
- fournisseur IA selectionnable sans modifier le code.

## 8. Tests et qualite

Installer les dependances de developpement dans un environnement virtuel:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Lancer les tests unitaires (aucune base de donnees requise, `app.ai.mock_analysis` et les schemas Pydantic sont testes isolement):

```powershell
pytest
```

Verifier le style et les erreurs statiques avec le linter:

```powershell
ruff check .
ruff format .
```

La configuration de pytest et ruff se trouve dans `pyproject.toml`.

## 9. Brancher les logs Windows

Avec Docker demarre, lancer PowerShell dans le dossier du projet:

```powershell
.\scripts\send-windows-logs.ps1 -Count 50
```

Le script lit les 50 derniers evenements du journal Windows `System`, les convertit en JSON et les envoie a `POST /ingest`. Pour importer davantage d'evenements:

```powershell
.\scripts\send-windows-logs.ps1 -Count 200
```

L'import stocke les logs dans PostgreSQL. Pour analyser ensuite un message, utiliser `POST /analyze-text` dans Swagger. L'automatisation continue peut etre ajoutee avec le Planificateur de taches Windows.

## 10. Check-list Demo Day

Avant la demonstration:

- [ ] `docker compose up --build` demarre sans erreur et `/health` repond `{"status": "ok"}`.
- [ ] `.env` contient une cle `DEEPSEEK_API_KEY` valide, ou `AI_PROVIDER=mock` en solution de secours si pas de reseau/quota.
- [ ] `pytest` et `ruff check .` passent tous les deux.
- [ ] Le script `send-windows-logs.ps1` a ete teste au moins une fois pour avoir des donnees a montrer.
- [ ] Un jeu d'evenements de demonstration est deja importe (`POST /events` ou `POST /ingest`) pour eviter de saisir des donnees en direct.
- [ ] Le plan B est pret: si l'IA distante est indisponible pendant la demo, basculer `AI_PROVIDER=mock` et redemarrer `docker compose up -d api`.
