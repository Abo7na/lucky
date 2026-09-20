import random
import uuid
from database.db import connection


def draw_active_round():
    """Close the active round and pay winners selected from individual tickets."""
    rng = random.SystemRandom()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        round_row = db.execute("SELECT * FROM rounds WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
        if not round_row:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "لا توجد جولة نشطة"}
        tickets = db.execute("SELECT id,user_id FROM tickets WHERE round_id=?", (round_row["id"],)).fetchall()
        if not tickets:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "لا توجد تذاكر في الجولة"}
        prizes = [int(x.strip()) for x in round_row["prizes"].split(",") if x.strip()]
        count = min(len(prizes), len(tickets))
        selected = rng.sample(tickets, count)
        winners = []
        for place, (ticket, prize) in enumerate(zip(selected, prizes[:count]), 1):
            uid = ticket["user_id"]
            user_row = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (uid,)).fetchone()
            if not user_row or user_row["is_banned"]:
                continue
            before = user_row["balance"]
            after = before + prize
            reference = f"lottery:{round_row['id']}:{ticket['id']}"
            db.execute("UPDATE users SET balance=? WHERE user_id=?", (after, uid))
            db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)",
                       (uid, "LOTTERY_PRIZE", prize, before, after, reference, f"الجائزة {place} في الجولة {round_row['id']}"))
            db.execute("INSERT INTO winners(round_id,ticket_id,user_id,place,prize) VALUES(?,?,?,?,?)",
                       (round_row["id"], ticket["id"], uid, place, prize))
            winners.append({"user_id": uid, "ticket_id": ticket["id"], "place": place, "prize": prize})
        db.execute("UPDATE rounds SET status='completed' WHERE id=? AND status='active'", (round_row["id"],))
        db.execute("COMMIT")
        return {"ok": True, "round_id": round_row["id"], "winners": winners}
