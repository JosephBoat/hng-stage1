# Stage 1 — Profiles API

Django + DRF service that accepts a name, enriches it via three public APIs
([Genderize](https://genderize.io), [Agify](https://agify.io),
[Nationalize](https://nationalize.io)), classifies the result, persists it to
Postgres, and exposes a small REST API over the stored profiles.

## Stack

- Python 3.12
- Django 6 + Django REST Framework
- PostgreSQL (Neon) via `dj-database-url`
- `httpx` for concurrent external calls
- `uuid6` for UUID v7 primary keys
- `whitenoise` for static files
- `gunicorn` as the WSGI server

## Endpoints

Base path: `/api`

| Method | Path                    | Description                                   |
| ------ | ----------------------- | --------------------------------------------- |
| POST   | `/api/profiles`         | Create a profile (idempotent on `name`)       |
| GET    | `/api/profiles`         | List profiles; filter by `gender`, `country_id`, `age_group` (case-insensitive) |
| GET    | `/api/profiles/{id}`    | Fetch one profile                             |
| DELETE | `/api/profiles/{id}`    | Delete one profile (204 No Content)           |

### Create

```http
POST /api/profiles
Content-Type: application/json

{ "name": "ella" }
```

Returns `201 Created` with the enriched profile, or `200 OK` with
`"Profile already exists"` if the name has been seen before.

### Age group rules

- `0-12` → `child`
- `13-19` → `teenager`
- `20-59` → `adult`
- `60+` → `senior`

### Error shape

```json
{ "status": "error", "message": "<reason>" }
```

- `400` — missing/empty name
- `422` — name is not a string
- `404` — profile not found
- `502` — upstream API returned an invalid response (per-provider message)

## Local development

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# .env
# DATABASE_URL=postgresql://...
# SECRET_KEY=...
# DEBUG=True

python manage.py migrate
python manage.py runserver
```

## Deployment (Koyeb)

Environment variables required:

- `DATABASE_URL` — Postgres connection string (Neon with `sslmode=require`)
- `SECRET_KEY` — any long random string
- `DEBUG` — `False` in production

The included `Procfile` runs `python manage.py migrate --noinput` as the
release step and starts `gunicorn core.wsgi` as the web process.
