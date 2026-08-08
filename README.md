# SmartVerify Policy Manager

SmartVerify stores Cedar policy content in one Git repository and keeps
tenant-scoped policy metadata in PostgreSQL. A minimal seeded-user header
provides authentication for the assessment.

- [System design and decision record](DESIGN.md)
- [Test strategy, results, and bug report](TESTING.md)

## Prerequisites

- Python 3.12+
- Node.js `^20.19.0` or `>=22.12.0`, with npm (required by Vite 8)
- A supplied Supabase/PostgreSQL connection URL; a local PostgreSQL server is
  not required when using Supabase
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

The connection URL is a secret and is intentionally excluded from Git. It must
be provided securely with the submission rather than added to this README.

The existing table is expected to match this metadata-only model:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `tenant_id` | varchar | Required |
| `filename` | varchar | Required |
| `git_hash` | varchar | Required committed Git hash |
| `created_at` | timestamptz | Creation timestamp |
| `updated_at` | timestamptz | Replacement timestamp |

`(tenant_id, filename)` is unique. Cedar content is deliberately absent from
the table.

Verify that Cedar can run:

```powershell
cedar --version
```

On Windows, use the Cedar executable's absolute path if the backend process
cannot resolve `cedar` from `PATH`:

```env
CEDAR_EXECUTABLE=C:\Users\your-name\.cargo\bin\cedar.exe
```

The tested CLI reports `cedar-policy-cli 4.12.0`. A different compatible
version may produce slightly different parser wording while preserving the
same validation behavior.

Git storage requires no setup command. The service automatically creates and
initializes `policy_data_store` on first use. Set `POLICY_REPOSITORY_PATH` only
when a different location is needed.

Start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

FastAPI documentation is available at `http://localhost:8000/docs`.
The health endpoint at `http://localhost:8000/` confirms both API startup and
database connectivity.

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

## Project structure

```text
smartverify-assessment/
|-- backend/             FastAPI application and backend tests
|-- frontend/            Modular React application and component tests
|-- demo-policies/       Valid Cedar files for the demonstration
|-- policy_data_store/   Runtime Git repository, created automatically
|-- DESIGN.md            Architecture, alternatives, and tradeoffs
|-- TESTING.md           Test commands, results, and bugs fixed
`-- README.md            Setup and usage
```

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

## API and demo examples

The UI is the simplest way to demonstrate the full workflow. The following
commands prove that the same controls are enforced when the UI is bypassed.
Run them from the project root while the backend is running.

Upload a Cedar file as multipart form data:

```powershell
curl.exe -X POST "http://localhost:8000/api/policies?tenant_id=tenant_A" `
  -H "user-id: user_1" `
  -F "file=@demo-policies/allow-policy-view.cedar;type=application/cedar"
```

List policies:

```powershell
curl.exe "http://localhost:8000/api/policies/list?tenant_id=tenant_A" `
  -H "user-id: user_1"
```

Download a policy:

```powershell
curl.exe --output downloaded-policy.cedar `
  "http://localhost:8000/api/policies/download?tenant_id=tenant_A&filename=allow-policy-view.cedar" `
  -H "user-id: user_1"
```

View the committed content as JSON:

```powershell
curl.exe `
  "http://localhost:8000/api/policies/content?tenant_id=tenant_A&filename=allow-policy-view.cedar" `
  -H "user-id: user_1"
```

View its Git history through the API:

```powershell
curl.exe `
  "http://localhost:8000/api/policies/history?tenant_id=tenant_A&filename=allow-policy-view.cedar" `
  -H "user-id: user_1"
```

Prove that `user_1` cannot access `tenant_B` with a handcrafted request:

```powershell
curl.exe -i `
  "http://localhost:8000/api/policies/list?tenant_id=tenant_B" `
  -H "user-id: user_1"
```

Expected result: HTTP `403 Forbidden`, even though the request bypasses the UI.

Prove that content is stored in a real Git repository after the upload:

```powershell
git -C policy_data_store rev-parse --is-inside-work-tree
git -C policy_data_store log --oneline -5
git -C policy_data_store show HEAD:tenant_A/allow-policy-view.cedar
```

The first command returns `true`. The latest commit hash should match the
`git_hash` stored in the Supabase `policy_metadata` row.

Delete a policy:

```powershell
curl.exe -X DELETE `
  "http://localhost:8000/api/policies?tenant_id=tenant_A&filename=allow-policy-view.cedar" `
  -H "user-id: user_1"
```

Invalid Cedar returns HTTP 400 with the parser's line, column, and error
description. A missing or unavailable Cedar executable returns HTTP 503.

The `demo-policies` directory contains five valid examples. Use the UI's
**Replace existing** action after editing a downloaded file without changing
its filename. The replacement appears as another Git commit and in the UI's
history view.

## Implemented bonus features

- Strict policy replacement with Git history.
- In-browser policy content preview.
- Commit history display.
- Configurable CORS.
- Exact commit-hash reads rather than uncommitted working-tree reads.
- Path traversal, UTF-8, and 1 MiB upload protections.
- Compensating Git commits for PostgreSQL failures.
- Real Cedar and Supabase integration tests.

Potential production extensions, including verified identity, Cedar schemas,
audit metadata, reconciliation, remote Git durability, and policy evaluation,
are discussed in [DESIGN.md](DESIGN.md).

## Tests

See [TESTING.md](TESTING.md) for test installation, execution, isolation, and
the latest verified results.
