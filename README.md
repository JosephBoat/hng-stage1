# Stage 1 Profiles API

A REST API that accepts a name, calls three external APIs, classifies the result, stores it in a PostgreSQL database, and exposes endpoints to manage profiles.

## Live API

```
https://urgent-janella-josephboateng-d9be4c60.koyeb.app
```

## Tech Stack

- **Framework:** Django + Django REST Framework
- **Database:** PostgreSQL (Neon)
- **Deployment:** Koyeb

## Endpoints

### Create Profile
```
POST /api/profiles
Content-Type: application/json

{ "name": "john" }
```
Calls Genderize, Agify, and Nationalize APIs concurrently, classifies the result, and stores it. Returns existing profile if name already exists.

### Get All Profiles
```
GET /api/profiles
```
Optional filters: `gender`, `country_id`, `age_group` (all case-insensitive)
```
GET /api/profiles?gender=male&country_id=NG
```

### Get Single Profile
```
GET /api/profiles/{id}
```

### Delete Profile
```
DELETE /api/profiles/{id}
```
Returns 204 No Content on success.

## Error Responses

All errors follow this structure:
```json
{ "status": "error", "message": "<error message>" }
```

| Status | Meaning |
|--------|---------|
| 400 | Missing or empty name |
| 422 | name is not a string |
| 404 | Profile not found |
| 502 | External API returned invalid response |

## Classification Rules

- **Age group:** 0–12 → child, 13–19 → teenager, 20–59 → adult, 60+ → senior
- **Nationality:** country with highest probability from Nationalize API
- **IDs:** UUID v7

## Local Setup

```bash
git clone <your-repo-url>
cd stage1-profiles
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt
```

Create a `.env` file:
```
DATABASE_URL=your_neon_postgres_url
SECRET_KEY=your_secret_key
DEBUG=False
```

```bash
python manage.py migrate
python manage.py runserver
```