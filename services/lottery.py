import random
from database.db import connection


def draw_active_round():
    rng = random.SystemRandom()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        round_row = db.execute("SELECT * FROM rounds WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
        if not round_row:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "لا توجد جولة نشطة"}
        tickets = db.execute("SELECT id,user_id FROM tickets WHERE round_id=?", (round_row["id"],)).fetchall()
        prizes = [int(x.strip()) for x in round_row["prizes"].split(",") if x.strip()]
        if not tickets or not prizes:
            db.execute("ROLLBACK")
            return {"ok": False, "message": "لا توجد تذاكر أو جوائز"}
        winners = []
        for place, ticket in enumerate(rng.sample(tickets, min(len(tickets), len(prizes))), 1):
            prize = prizes[place - 1]
            user = db.execute("SELECT balance,is_banned FROM users WHERE user_id=?", (ticket["user_id"],)).fetchone()
            if not user or user["is_banned"]:
                continue
            before = user["balance"]
            reference = f"lottery:{round_row['id']}:{ticket['id']}"
            db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (prize, ticket["user_id"]))
            db.execute("INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)", (ticket["user_id"], "LOTTERY_PRIZE", prize, before, before + prize, reference, f"الجائزة {place} في الجولة {round_row['id']}"))
            db.execute("INSERT INTO winners(round_id,ticket_id,user_id,place,prize) VALUES(?,?,?,?,?)", (round_row["id"], ticket["id"], ticket["user_id"], place, prize))
            winners.append({"user_id": ticket["user_id"], "place": place, "prize": prize})
        db.execute("UPDATE rounds SET status='completed' WHERE id=? AND status='active'", (round_row["id"],))
        db.execute("COMMIT")
        return {"ok": True, "round_id": round_row["id"], "winners": winners}
