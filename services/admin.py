from database.db import connection


def pending_requests():
    with connection() as db:
        return (db.execute("SELECT * FROM deposit_requests WHERE status='pending' ORDER BY id LIMIT 30").fetchall(), db.execute("SELECT * FROM withdrawal_requests WHERE status='pending' ORDER BY id LIMIT 30").fetchall())


def decide_deposit(request_id, approve, reason=""):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM deposit_requests WHERE id=? AND status='pending'", (request_id,)).fetchone()
        if not row: db.execute("ROLLBACK"); return {"ok": False, "message": "الطلب غير موجود أو تمت معالجته"}
        if approve:
            user = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (row["user_id"],)).fetchone()
            if not user or user["is_banned"]: db.execute("ROLLBACK"); return {"ok": False, "message": "الحساب غير متاح"}
            db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (row["amount"], row["user_id"]))
            db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (row["user_id"], "DEPOSIT", row["amount"], user["balance"], user["balance"] + row["amount"], f"deposit:{row['id']}", reason or "قبول الشحن"))
        db.execute("UPDATE deposit_requests SET status=?,decided_at=CURRENT_TIMESTAMP WHERE id=?", ("approved" if approve else "rejected", request_id)); db.execute("COMMIT")
        return {"ok": True, "user_id": row["user_id"], "amount": row["amount"]}


def decide_withdrawal(request_id, approve, reason=""):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM withdrawal_requests WHERE id=? AND status='pending'", (request_id,)).fetchone()
        if not row: db.execute("ROLLBACK"); return {"ok": False, "message": "الطلب غير موجود أو تمت معالجته"}
        if not approve:
            user = db.execute("SELECT balance FROM users WHERE user_id=?", (row["user_id"],)).fetchone()
            if not user: db.execute("ROLLBACK"); return {"ok": False, "message": "المستخدم غير موجود"}
            db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (row["amount"], row["user_id"]))
            db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (row["user_id"], "WITHDRAW_REFUND", row["amount"], user["balance"], user["balance"] + row["amount"], f"withdraw-refund:{row['id']}", reason or "رد السحب"))
        db.execute("UPDATE withdrawal_requests SET status=?,decided_at=CURRENT_TIMESTAMP WHERE id=?", ("approved" if approve else "rejected", request_id)); db.execute("COMMIT")
        return {"ok": True, "user_id": row["user_id"], "amount": row["amount"]}
