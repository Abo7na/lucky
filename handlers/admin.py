from config import ADMIN_IDS
from database.db import connection
from services.admin import pending_requests, decide_deposit, decide_withdrawal
from services.lottery import draw_active_round


def register(bot):
    def allowed(message):
        return message.from_user.id in ADMIN_IDS

    @bot.message_handler(commands=["pending"])
    def pending(message):
        if not allowed(message): return
        deposits, withdrawals = pending_requests()
        lines = ["📥 <b>الطلبات المعلقة</b>"]
        lines += [f"شحن #{r['id']} — {r['amount']} نقطة — <code>{r['user_id']}</code>\n/approve_deposit {r['id']} | /reject_deposit {r['id']}" for r in deposits]
        lines += [f"سحب #{r['id']} — {r['amount']} نقطة — <code>{r['user_id']}</code>\n/approve_withdraw {r['id']} | /reject_withdraw {r['id']}" for r in withdrawals]
        bot.send_message(message.chat.id, "\n\n".join(lines), parse_mode="HTML")

    @bot.message_handler(commands=["approve_deposit", "reject_deposit", "approve_withdraw", "reject_withdraw"])
    def decide(message):
        if not allowed(message): return
        parts = message.text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            bot.send_message(message.chat.id, "الصيغة: /approve_deposit ID")
            return
        command, request_id = parts[0][1:], int(parts[1])
        approve = command.startswith("approve_")
        result = decide_deposit(request_id, approve) if "deposit" in command else decide_withdrawal(request_id, approve)
        bot.send_message(message.chat.id, "✅ تمت معالجة الطلب" if result["ok"] else f"❌ {result['message']}")
        if result.get("ok"):
            try: bot.send_message(result["user_id"], f"📌 {'تمت الموافقة' if approve else 'تم الرفض'} على طلبك #{request_id}. المبلغ: {result['amount']} نقطة")
            except Exception: pass

    @bot.message_handler(commands=["draw"])
    def draw(message):
        if not allowed(message): return
        result = draw_active_round()
        if not result["ok"]:
            bot.send_message(message.chat.id, f"❌ {result['message']}")
            return
        bot.send_message(message.chat.id, f"✅ أغلقت الجولة #{result['round_id']}؛ الفائزون: {len(result['winners'])}")
        for winner in result["winners"]:
            try: bot.send_message(winner["user_id"], f"🎉 ربحت {winner['prize']} نقطة!")
            except Exception: pass

    @bot.message_handler(commands=["ledger"])
    def ledger(message):
        if not allowed(message): return
        with connection() as db:
            rows = db.execute("SELECT user_id,type,amount,created_at FROM ledger ORDER BY id DESC LIMIT 30").fetchall()
        text = "📒 <b>آخر المعاملات</b>\n\n" + ("\n".join(f"{r['user_id']} | {r['type']} | {r['amount']} | {r['created_at']}" for r in rows) or "لا توجد معاملات")
        bot.send_message(message.chat.id, text, parse_mode="HTML")
