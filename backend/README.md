# InterviewMirror Backend

Backend service for the InterviewMirror application, built with Python and FastAPI using a modular monolith structure.

## Requirements

- Python 3.x
- PostgreSQL

## Setup

Navigate to the backend directory:

```powershell
cd backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Database Configuration

The backend connects to PostgreSQL using the `DATABASE_URL` environment variable.

Create a `.env` file in the `backend` directory and configure the connection string:

```text
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/interviewmirror
```

Replace `username`, `password`, and the database details with the values for your local environment.

Apply the latest database migrations before running the application:

```powershell
alembic upgrade head
```

## Run the Application

```powershell
python -m uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## Available Endpoints

- Hello: `GET /hello`
- API status: `GET /api/status`
- Screening score: `POST /api/screening/score`
- Swagger documentation: `/docs`
- OpenAPI schema: `/openapi.json`

## Screening Score & Result Persistence

The screening module implements suitability scoring and result persistence for the resume screening flow.

### 1. Suitability Score Calculation

The screening module calculates the candidate's overall suitability score based on the defined screening criteria.

The result includes:

- Category breakdown
- Overall suitability score
- Passing score
- Final screening status

The scoring logic can be evaluated independently before the result is persisted to the database.

### 2. Store Screening Results

After the suitability score and final status are calculated, the screening endpoint persists the result in PostgreSQL using SQLAlchemy.

Each screening result is stored in the `screening_results` table with:

- `candidate_id`
- `job_id`
- `category_breakdown`
- `overall_score`
- `passing_score`
- `final_status`
- `evaluated_at`

Persisting the result makes the screening data available for later use by other parts of the system.

### 3. Database Integration

The backend uses:

- PostgreSQL as the database
- SQLAlchemy as the ORM
- Psycopg as the PostgreSQL driver
- `python-dotenv` for environment configuration

The database connection and SQLAlchemy sessions are configured through the backend database module using the `DATABASE_URL` environment variable.

### 4. Database Migrations

Alembic is used with SQLAlchemy to manage database schema changes.

The screening migration defines the `screening_results` table so the schema can be created consistently across development environments.

To apply all available migrations:

```powershell
alembic upgrade head
```

Using migrations keeps database schema changes versioned alongside the backend code and makes them reproducible for the rest of the team.

### Screening Flow

```text
Resume Screening Input
        ↓
Calculate Suitability Score
        ↓
Determine Final Status
        ↓
Store Screening Result
        ↓
PostgreSQL
```
