import telebot
from config import BOT_TOKEN,ADMIN_IDS
from database.db import init_db,connection
from handlers.user import register
from handlers.admin import register as register_admin
init_db();bot=telebot.TeleBot(BOT_TOKEN,parse_mode='HTML');register(bot,ADMIN_IDS);register_admin(bot)
@bot.message_handler(commands=['stats'])
def stats(message):
 if message.from_user.id not in ADMIN_IDS:return
 with connection() as db:
  u=db.execute('SELECT COUNT(*) c FROM users').fetchone()['c'];b=db.execute('SELECT COALESCE(SUM(balance),0) b FROM users').fetchone()['b'];d=db.execute("SELECT COUNT(*) c FROM deposit_requests WHERE status='pending'").fetchone()['c'];w=db.execute("SELECT COUNT(*) c FROM withdrawal_requests WHERE status='pending'").fetchone()['c']
 bot.send_message(message.chat.id,f'📊 المستخدمون: {u}\n💰 الأرصدة: {b}\n📥 شحن معلق: {d}\n📤 سحب معلق: {w}')
@bot.message_handler(commands=['backup'])
def backup_cmd(message):
 if message.from_user.id not in ADMIN_IDS:return
 from utils.backup import backup
 p=backup()
 with open(p,'rb') as f:bot.send_document(message.chat.id,f,caption='✅ نسخة احتياطية')
if __name__=='__main__':bot.infinity_polling(skip_pending=True)
