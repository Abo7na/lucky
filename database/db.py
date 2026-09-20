import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH

@contextmanager
def connection():
    conn = sqlite3.connect(DATABASE_PATH, timeout=20, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with connection() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance INTEGER NOT NULL DEFAULT 1000 CHECK(balance>=0), language TEXT NOT NULL DEFAULT 'ar', is_banned INTEGER NOT NULL DEFAULT 0, referred_by INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, type TEXT NOT NULL, amount INTEGER NOT NULL, before_balance INTEGER NOT NULL, after_balance INTEGER NOT NULL, reference TEXT NOT NULL UNIQUE, description TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS gift_codes(code TEXT PRIMARY KEY, points INTEGER NOT NULL CHECK(points>0), max_uses INTEGER NOT NULL CHECK(max_uses>0), used_count INTEGER NOT NULL DEFAULT 0, expires_at TEXT);
        CREATE TABLE IF NOT EXISTS gift_redemptions(user_id INTEGER NOT NULL, code TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,code));
        CREATE TABLE IF NOT EXISTS rounds(id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_price INTEGER NOT NULL CHECK(ticket_price>0), prizes TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT, round_id INTEGER NOT NULL REFERENCES rounds(id), user_id INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS games(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,game TEXT NOT NULL,cost INTEGER NOT NULL,reward INTEGER NOT NULL,won INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS deposit_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,amount INTEGER NOT NULL,method TEXT NOT NULL,proof TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,decided_at TEXT);
        CREATE TABLE IF NOT EXISTS withdrawal_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,amount INTEGER NOT NULL,method TEXT NOT NULL,account TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,decided_at TEXT);
        CREATE INDEX IF NOT EXISTS tickets_round_idx ON tickets(round_id);
        CREATE INDEX IF NOT EXISTS ledger_user_idx ON ledger(user_id,created_at);
        CREATE UNIQUE INDEX IF NOT EXISTS pending_withdrawal_user_idx ON withdrawal_requests(user_id) WHERE status='pending';
        CREATE UNIQUE INDEX IF NOT EXISTS pending_deposit_proof_idx ON deposit_requests(proof) WHERE status='pending';
        INSERT OR IGNORE INTO settings(key,value) VALUES ('game_cost','50'),('game_reward','120'),('game_chance','40'),('min_withdraw','10000');
        INSERT INTO rounds(ticket_price,prizes) SELECT 100,'5000,3000,1500' WHERE NOT EXISTS(SELECT 1 FROM rounds WHERE status='active');
        ''')

def user(user_id, username=None, first_name=None):
    with connection() as db:
        db.execute("INSERT INTO users(user_id,username,first_name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name", (user_id,username,first_name))
        return db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def setting(key, default=None):
    with connection() as db:
        row=db.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return row['value'] if row else default
