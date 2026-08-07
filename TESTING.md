# Testing

## Backend

From the `backend` directory:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest --cov=app --cov-branch --cov-report=term-missing
```

The suite uses an in-memory SQLite database and a disposable Git repository for
each storage test. It does not connect to Supabase or modify
`policy_data_store`.

Production startup still requires `DATABASE_URL`. Cedar validation uses
`CEDAR_EXECUTABLE` when set, otherwise it looks for `cedar` on `PATH`.
