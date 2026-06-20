"""
Catalunya Bank – Account Balance API
-------------------------------------
Two endpoints consumed by the Enterprise Bot AIDA voice agent:

  POST /verifytoken   – authenticate account_number + PIN, return a token
  GET  /getbalance    – return balance for a valid token

Database: SQLite (accounts.db), auto-created and seeded on first run.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import secrets
import os

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Catalunya Bank Account API")

# AIDA platform makes cross-origin requests, so allow all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory token store: { token_string -> account_number }
# Simple and sufficient for a demo; resets on server restart (see README for improvements).
active_tokens: dict[str, str] = {}

DB_PATH = os.getenv("DB_PATH", "accounts.db")


# ── Database ───────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Create the accounts table and seed it with three fake customers."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT    UNIQUE NOT NULL,
            pin            TEXT    NOT NULL,
            customer_name  TEXT    NOT NULL,
            balance        REAL    NOT NULL,
            currency       TEXT    NOT NULL DEFAULT 'EUR'
        )
    """)
    # INSERT OR IGNORE keeps this idempotent – safe to run on every startup.
    seed = [
        ("112233", "4821", "Sophie Turner",     3_245.67),
        ("445566", "7734", "James Harrington", 18_902.50),
        ("778899", "2296", "Elena Vasquez",       742.18),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO accounts (account_number, pin, customer_name, balance) VALUES (?, ?, ?, ?)",
        seed,
    )
    conn.commit()
    conn.close()


init_db()


# ── Request models ─────────────────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    account_number: str
    pin: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/verifytoken")
def verify_token(req: VerifyRequest):
    """
    Authenticate a customer with their account number and PIN.

    Returns:
        authenticated=True  + a short-lived token on success
        authenticated=False on wrong credentials (no HTTP error, so the LLM
        can handle the failure gracefully in natural language)
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT account_number, customer_name FROM accounts WHERE account_number = ? AND pin = ?",
        (req.account_number, req.pin),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return {"authenticated": False}

    token = secrets.token_hex(32)
    active_tokens[token] = row[0]   # map token → account_number

    return {
        "authenticated": True,
        "token":         token,
        "auth_token":    token,      # AIDA prompt references both names
        "customer_name": row[1],
        "account_number": row[0],
    }


@app.get("/getbalance")
def get_balance(
    token: str = Query(..., description="Auth token returned by /verifytoken"),
):
    """
    Return the account balance for a previously issued token.

    The AIDA getbalance tool sends `token` as a query-string parameter.
    """
    account_number = active_tokens.get(token)
    if account_number is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please authenticate again.",
        )

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT balance, currency, customer_name FROM accounts WHERE account_number = ?",
        (account_number,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    return {
        "account_number": account_number,
        "customer_name":  row[2],
        "balance":        row[0],
        "currency":       row[1],
    }


@app.get("/health")
def health():
    """Liveness check used by Railway."""
    return {"status": "ok"}
