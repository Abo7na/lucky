import random
import uuid
from datetime import datetime

from config import TEST_MODE
from database.db import connection, setting


def change_balance(user_id, amount, kind, description, reference=None):
    reference = reference or uuid.uuid4().hex
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM ledger WHERE reference=?", (reference,)).fetchone():
            db.execute("ROLLBACK")
            return {"ok": True, "duplicate": True}
        row = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or row["is_banned"]:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الحساب غير متاح"}
        amount = int(amount)
        before = row["balance"]
        after = before + amount
        if after < 0:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الرصيد غير كافٍ"}
        db.execute("UPDATE users SET balance=? WHERE user_id=?", (after, user_id))
        db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (user_id, kind, amount, before, after, reference, description))
        db.execute("COMMIT")
        return {"ok": True, "balance": after}


def buy_tickets(user_id, quantity):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return {"ok": False, "message": "عدد التذاكر غير صالح"}
    if not 1 <= quantity <= 100:
        return {"ok": False, "message": "عدد التذاكر غير صالح"}
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        round_row = db.execute("SELECT * FROM rounds WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
        account = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not round_row:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "لا توجد جولة نشطة"}
        total = round_row["ticket_price"] * quantity
        if not account or account["is_banned"] or account["balance"] < total:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الرصيد غير كافٍ"}
        before = account["balance"]
        after = before - total
        cur = db.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (total, user_id, total))
        if cur.rowcount != 1:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "تعذر إتمام العملية"}
        db.executemany("INSERT INTO tickets(round_id,user_id) VALUES(?,?)", [(round_row["id"], user_id)] * quantity)
        db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (user_id, "TICKET", -total, before, after, f"ticket:{round_row['id']}:{uuid.uuid4().hex}", f"شراء {quantity} تذكرة"))
        db.execute("COMMIT")
        return {"ok": True, "quantity": quantity, "balance": after}


def redeem(user_id, raw_code):
    code = (raw_code or "").strip().upper()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        gift = db.execute("SELECT * FROM gift_codes WHERE code=?", (code,)).fetchone()
        if not gift:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الكود غير صالح"}
        if gift["expires_at"] and gift["expires_at"] <= datetime.utcnow().isoformat():
            db.execute("ROLLBACK")
            return {"ok": False, "message": "انتهت صلاحية الكود"}
        if db.execute("SELECT 1 FROM gift_redemptions WHERE user_id=? AND code=?", (user_id, code)).fetchone():
            db.execute("ROLLBACK")
            return {"ok": False, "message": "تم استخدام الكود مسبقاً"}
        cur = db.execute("UPDATE gift_codes SET used_count=used_count+1 WHERE code=? AND used_count<max_uses", (code,))
        if cur.rowcount != 1:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "انتهت استخدامات الكود"}
        account = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not account or account["is_banned"]:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الحساب غير متاح"}
        before = account["balance"]
        after = before + gift["points"]
        db.execute("UPDATE users SET balance=? WHERE user_id=?", (after, user_id))
        db.execute("INSERT INTO gift_redemptions(user_id,code) VALUES(?,?)", (user_id, code))
        db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (user_id, "GIFT", gift["points"], before, after, f"gift:{code}:{user_id}", "استبدال كود هدية"))
        db.execute("COMMIT")
        return {"ok": True, "points": gift["points"], "balance": after}


def create_deposit(user_id, amount, method, proof):
    if TEST_MODE:
        return {"ok": False, "message": "الشحن معطل في وضع الاختبار"}
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return {"ok": False, "message": "المبلغ غير صالح"}
    method, proof = (method or "").strip(), (proof or "").strip()
    if amount <= 0 or not method or not proof:
        return {"ok": False, "message": "بيانات الشحن غير صالحة"}
    with connection() as db:
        try:
            cur = db.execute("INSERT INTO deposit_requests(user_id,amount,method,proof) VALUES(?,?,?,?)", (user_id, amount, method, proof))
        except Exception:
            return {"ok": False, "message": "الإثبات مستخدم أو الطلب غير صالح"}
        return {"ok": True, "id": cur.lastrowid}


def create_withdrawal(user_id, amount, method, account):
    if TEST_MODE:
        return {"ok": False, "message": "السحب معطل في وضع الاختبار"}
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return {"ok": False, "message": "المبلغ غير صالح"}
    minimum = int(setting("min_withdraw", "10000"))
    method, account = (method or "").strip(), (account or "").strip()
    if amount < minimum or not method or not account:
        return {"ok": False, "message": f"الحد الأدنى للسحب {minimum} نقطة"}
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or row["is_banned"] or row["balance"] < amount:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الرصيد غير كافٍ"}
        before, after = row["balance"], row["balance"] - amount
        cur = db.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (amount, user_id, amount))
        if cur.rowcount != 1:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "تعذر حجز الرصيد"}
        try:
            cur = db.execute("INSERT INTO withdrawal_requests(user_id,amount,method,account) VALUES(?,?,?,?)", (user_id, amount, method, account))
        except Exception:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "لديك طلب سحب معلق"}
        db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (user_id, "WITHDRAW_HOLD", -amount, before, after, f"withdraw:{uuid.uuid4().hex}", "حجز طلب سحب"))
        db.execute("COMMIT")
        return {"ok": True, "id": cur.lastrowid}


def spin_wheel(user_id):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        last = db.execute("SELECT created_at FROM wheel_spins WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        if last and (datetime.utcnow() - datetime.strptime(last["created_at"], "%Y-%m-%d %H:%M:%S")).total_seconds() < 86400:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "استخدمت العجلة اليوم"}
        raw_prizes = db.execute("SELECT value FROM settings WHERE key='wheel_prizes'").fetchone()
        prizes = [int(x.strip()) for x in (raw_prizes["value"] if raw_prizes else "25,50,100,250,500,1000").split(",") if x.strip()]
        if not prizes:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "لا توجد جوائز متاحة"}
        account = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not account or account["is_banned"]:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "الحساب غير متاح"}
        prize = random.choice(prizes)
        before, after = account["balance"], account["balance"] + prize
        db.execute("UPDATE users SET balance=? WHERE user_id=?", (after, user_id))
        db.execute("INSERT INTO wheel_spins(user_id,prize) VALUES(?,?)", (user_id, prize))
        db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (user_id, "WHEEL", prize, before, after, f"wheel:{user_id}:{uuid.uuid4().hex}", "جائزة العجلة"))
        db.execute("COMMIT")
        return {"ok": True, "prize": prize, "balance": after}
