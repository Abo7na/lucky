import sqlite3
from database.db import connection
from services.wallet import change_balance


def pending_requests():
    with connection() as db:
        deposits = db.execute("SELECT * FROM deposit_requests WHERE status='pending' ORDER BY id LIMIT 30").fetchall()
        withdrawals = db.execute("SELECT * FROM withdrawal_requests WHERE status='pending' ORDER BY id LIMIT 30").fetchall()
        return deposits, withdrawals


def decide_deposit(request_id, approve, reason=""):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM deposit_requests WHERE id=? AND status='pending'", (request_id,)).fetchone()
        if not row:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الطلب غير موجود أو تمت معالجته"}
        if approve:
            user = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (row["user_id"],)).fetchone()
            if not user or user["is_banned"]:
                db.execute("ROLLBACK")
                return {"ok": False, "message": "حساب المستخدم غير متاح"}
            before = user["balance"]
            after = before + row["amount"]
            reference = f"deposit:{row['id']}"
            if db.execute("SELECT 1 FROM ledger WHERE reference=?", (reference,)).fetchone():
                db.execute("ROLLBACK")
                return {"ok": False, "message": "المعاملة مسجلة مسبقاً"}
            db.execute("UPDATE users SET balance=? WHERE user_id=?", (after, row["user_id"]))
            db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)",
                       (row["user_id"], "DEPOSIT", row["amount"], before, after, reference, reason or "قبول طلب شحن"))
        db.execute("UPDATE deposit_requests SET status=?,decided_at=CURRENT_TIMESTAMP WHERE id=?", ("approved" if approve else "rejected", request_id))
        db.execute("COMMIT")
        return {"ok": True, "user_id": row["user_id"], "amount": row["amount"], "status": "approved" if approve else "rejected"}


def decide_withdrawal(request_id, approve, reason=""):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM withdrawal_requests WHERE id=? AND status='pending'", (request_id,)).fetchone()
        if not row:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الطلب غير موجود أو تمت معالجته"}
        if not approve:
            user = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (row["user_id"],)).fetchone()
            if not user:
                db.execute("ROLLBACK")
                return {"ok": False, "message": "المستخدم غير موجود"}
            before = user["balance"]
            after = before + row["amount"]
            reference = f"withdraw-refund:{row['id']}"
            db.execute("UPDATE users SET balance=? WHERE user_id=?", (after, row["user_id"]))
            db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)",
                       (row["user_id"], "WITHDRAW_REFUND", row["amount"], before, after, reference, reason or "رفض طلب السحب"))
        db.execute("UPDATE withdrawal_requests SET status=?,decided_at=CURRENT_TIMESTAMP WHERE id=?", ("approved" if approve else "rejected", request_id))
        db.execute("COMMIT")
        return {"ok": True, "user_id": row["user_id"], "amount": row["amount"], "status": "approved" if approve else "rejected"}
