# Presidio Reimbursement Approval Tool

This project is initialized with:
- **Frontend**: React (TypeScript + Vite)
- **Backend**: FastAPI (Python + uv package manager)
- **Database**: Dedicated `database/` directory

## Folder Structure

```
├── backend/            # FastAPI Backend
│   ├── main.py         # Entry point for the FastAPI application
│   ├── pyproject.toml  # Python project dependencies managed by uv
│   └── .venv/          # Python virtual environment
├── database/           # Database schema, migrations, or SQLite files
├── frontend/           # React Frontend
│   ├── src/            # Source files (App, main, etc.)
│   ├── package.json    # Frontend dependencies
│   └── vite.config.ts  # Vite configuration
└── README.md           # This file
```

## Running the Application

### 1. Backend

Navigate to the `backend/` directory and start the FastAPI server:

```bash
cd backend
uv run uvicorn main:app --reload
```

The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).
- Interactive Docs (Swagger UI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Endpoint: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 2. Frontend

Navigate to the `frontend/` directory and start the Vite development server:

```bash
cd frontend
npm run dev
```

The frontend will be available at the URL shown in your terminal (usually [http://localhost:5173](http://localhost:5173)).
