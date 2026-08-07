# Testing

## Backend unit and API suite

From the `backend` directory:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest -v --cov=app --cov-branch --cov-report=term-missing
```

After activating the project environment, the shorter command also works:

```powershell
pytest -v
```

The isolated suite uses SQLite and a disposable Git repository. It covers the
complete policy lifecycle, customer/user/tenant mappings, multipart input,
actionable Cedar failures, exact Git-commit reads, compensating Git operations,
path safety, CORS, failure handling, and handcrafted cross-tenant upload, read,
download, and delete attempts.

## Real Cedar and Supabase integration tests

These tests use the Cedar executable and `DATABASE_URL` configured in
`backend/.env`:

```powershell
.\venv\Scripts\python.exe -m pytest -v integration_tests
```

The PostgreSQL test inserts and reads a uniquely named metadata record inside
one transaction and always rolls the transaction back. It does not leave test
rows in Supabase. `SUPABASE_TEST_DATABASE_URL` can override `DATABASE_URL` for
a dedicated test database.

## Frontend

From the `frontend` directory:

```powershell
npm ci
npm test
npm run lint
npm run build
```

The component tests verify backend-provided customer/tenant options, selection
callbacks, policy rendering, action callbacks, and the empty-list state.

## Latest verified execution

Verified on August 7, 2026:

| Check | Result |
| --- | --- |
| Backend isolated suite | 66 passed |
| Backend statement coverage | 100% |
| Backend branch coverage | 100% |
| Real Cedar CLI integration | 1 passed |
| Real Supabase/PostgreSQL integration | 1 passed; transaction rolled back |
| React component suite | 4 passed |
| Frontend ESLint | Passed |
| Frontend production build | Passed; 26 modules transformed |

## Bugs found and fixed

| Bug or gap | Fix | Verification |
| --- | --- | --- |
| `pytest -v` could not import `app` | Added the backend directory to pytest's Python path | Plain `pytest -v` passes |
| Browser uploads were not real files | Changed the API and UI to multipart file upload | Multipart lifecycle tests |
| Cedar CLI failures surfaced as a Windows process error | Added configurable `CEDAR_EXECUTABLE` handling and HTTP 503 errors | Real Cedar integration and failure tests |
| Cedar parser details were hidden | Return the parser's token and location details in the HTTP 400 response | Parser-error API and service tests |
| Users had tenants but no customer mapping | Added explicit customer IDs and tenant lists in the backend | Seeded-user API test |
| Frontend duplicated authorization data | Frontend now loads demo access mappings from `GET /api/users` | React access-panel tests |
| Metadata `git_hash` was not used for reads | Content and downloads now read the exact blob from that Git commit | Git historical-read tests and 100% coverage |
| `PUT` silently created missing policies | Replacement now returns HTTP 404 unless the policy already exists | Replacement edge-case test |
| Replacement/deletion could leave Git changed after a database failure | Added compensating commits that restore previous content | Failure and rollback tests |
| Cross-tenant content and delete behavior lacked direct tests | Added handcrafted cross-tenant upload, content, and delete requests and verified the owner's file remains | Tenant-isolation API test |
