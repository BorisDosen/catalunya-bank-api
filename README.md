# Catalunya Bank – Account Balance Voice Bot

A voice bot built on the **Enterprise Bot AIDA platform** that lets a caller authenticate and retrieve their account balance. The LLM drives the conversation agentic-style, deciding when to ask for credentials and when to invoke each tool.

---

## How it works

1. The caller asks for their account balance.
2. The AIDA agent asks for their **account number** and **4-digit PIN**.
3. The agent calls **`/verifytoken`** (POST) – validates credentials against the SQLite database and returns a short-lived token.
4. If authentication succeeds, the agent calls **`/getbalance`** (GET) – looks up the balance using the token and speaks it back in natural language.
5. Wrong credentials or invalid tokens are rejected gracefully; the agent invites the caller to try again.

---

## Tech stack

| Layer      | Choice          | Reason |
|------------|-----------------|--------|
| API        | Python + FastAPI | Minimal boilerplate, auto-generates OpenAPI docs, production-ready |
| Database   | SQLite           | Zero external dependencies; self-contained file, perfect for a demo |
| Auth method | Account number + PIN | Familiar banking UX, easy to demo over voice |
| Token store | In-memory dict  | Simplest approach that satisfies the two-tool requirement |
| Hosting    | Railway.app      | One-click GitHub deploy, persistent (no sleep), free $5 credit |

---

## Fake accounts (for testing)

| Account Number | PIN  | Customer Name     | Balance     |
|----------------|------|-------------------|-------------|
| ACC-001001     | 4821 | Sophie Turner     | EUR 3,245.67 |
| ACC-001002     | 7734 | James Harrington  | EUR 18,902.50 |
| ACC-001003     | 2296 | Elena Vasquez     | EUR 742.18  |

---

## API reference

### POST /verifytoken

Authenticate a customer.

Request body (JSON):
```json
{ "account_number": "ACC-001001", "pin": "4821" }
```

Success response:
```json
{
  "authenticated": true,
  "token": "<hex-token>",
  "auth_token": "<hex-token>",
  "customer_name": "Sophie Turner",
  "account_number": "ACC-001001"
}
```

Failure response:
```json
{ "authenticated": false }
```

---

### GET /getbalance?token=<token>

Retrieve balance for an authenticated token.

Success response:
```json
{
  "account_number": "ACC-001001",
  "customer_name": "Sophie Turner",
  "balance": 3245.67,
  "currency": "EUR"
}
```

---

## Setup & running locally

**Prerequisites:** Python 3.11+

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/catalunya-bank-api.git
cd catalunya-bank-api

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn main:app --reload
```

The API is now available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## Deploying to Railway (to get a public HTTPS URL for AIDA)

1. Push this repo to GitHub.
2. Go to [railway.app](https://railway.app) and sign up with GitHub.
3. Click **New Project** → **Deploy from GitHub repo** → select this repo.
4. Railway detects Python from `requirements.txt` and uses `Procfile` to start the server.
5. Once deployed, go to **Settings → Networking → Generate Domain**.
6. Copy your public URL, e.g. `https://catalunya-bank-api-production.up.railway.app`

Then update the AIDA tool URLs:
- **verifytoken:** `https://YOUR-RAILWAY-URL/verifytoken`
- **getbalance:** `https://YOUR-RAILWAY-URL/getbalance`

---

## What I'd improve with more time

PIN values are stored in plaintext in the database; in production I would hash them with bcrypt so a database breach doesn't expose credentials directly. Issued tokens currently live forever in an in-memory dictionary, so I would add expiry timestamps and move the store to Redis or a database table to survive server restarts. I would also add per-account rate limiting on `/verifytoken` to prevent brute-force PIN guessing. Finally, I would replace the hand-rolled hex token with a signed JWT so the token itself carries a verifiable expiry claim and the server doesn't need to store state at all.
