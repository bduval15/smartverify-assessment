# SmartVerify Policy Manager

SmartVerify stores Cedar policy content in one Git repository and keeps
tenant-scoped policy metadata in PostgreSQL. A minimal seeded-user header
provides authentication for the assessment.

## Prerequisites

- Python 3.12+
- Node.js and npm
- PostgreSQL
- Git
- The Cedar CLI (`cedar`), or an absolute path supplied through
  `CEDAR_EXECUTABLE`

## Backend setup

From the repository root:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Update `backend/.env` with the supplied Supabase PostgreSQL connection URL.
The configured database already contains the `policy_metadata` table, so no
database initialization or migration command is required.

On Windows, use the Cedar executable's absolute path if the backend process
cannot resolve `cedar` from `PATH`:

```env
CEDAR_EXECUTABLE=C:\Users\your-name\.cargo\bin\cedar.exe
```

Git storage requires no setup command. The service automatically creates and
initializes `policy_data_store` on first use. Set `POLICY_REPOSITORY_PATH` only
when a different location is needed.

Start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

FastAPI documentation is available at `http://localhost:8000/docs`.

## Frontend setup

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The default allowed frontend origin is `http://localhost:5173`. Configure
multiple origins as a comma-separated `CORS_ALLOWED_ORIGINS` value.

The single-page UI loads its seeded customer/user/tenant mappings from the
backend and supports user and tenant selection, policy listing,
multipart upload, replacement, content viewing, download, Git history, and
deletion.

## Seeded users

Requests use the `user-id` header:

| User | Customer | Authorized tenants |
| --- | --- | --- |
| `user_1` | `customer_1` | `tenant_A` |
| `user_2` | `customer_1` | `tenant_A`, `tenant_B` |
| `user_3` | `customer_2` | `tenant_C` |

`GET /api/users` supplies these seeded demo mappings to the frontend. Policy
requests still require the `user-id` header, and the backend independently
enforces the requested tenant against that user's mapping.

## Storage behavior

Every accepted upload or replacement is committed to the single
`policy_data_store` Git repository. PostgreSQL stores only metadata and the
corresponding commit hash. Content views and downloads read the exact Git blob
identified by that hash rather than trusting an uncommitted working-tree file.

Replacement uses `PUT` and requires an existing metadata record; it returns
HTTP 404 instead of creating a new policy. When a PostgreSQL replacement or
deletion fails after Git has changed, the service makes a compensating Git
commit to restore the previous content.

## API examples

Upload a Cedar file as multipart form data:

```powershell
curl.exe -X POST "http://localhost:8000/api/policies?tenant_id=tenant_A" `
  -H "user-id: user_1" `
  -F "file=@example.cedar;type=application/cedar"
```

List policies:

```powershell
curl.exe "http://localhost:8000/api/policies/list?tenant_id=tenant_A" `
  -H "user-id: user_1"
```

Download a policy:

```powershell
curl.exe -OJ `
  "http://localhost:8000/api/policies/download?tenant_id=tenant_A&filename=example.cedar" `
  -H "user-id: user_1"
```

Delete a policy:

```powershell
curl.exe -X DELETE `
  "http://localhost:8000/api/policies?tenant_id=tenant_A&filename=example.cedar" `
  -H "user-id: user_1"
```

Invalid Cedar returns HTTP 400 with the parser's line, column, and error
description. A missing or unavailable Cedar executable returns HTTP 503.

## Tests

See [TESTING.md](TESTING.md) for test installation, execution, isolation, and
the latest verified results.
