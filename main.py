import telebot
from config import BOT_TOKEN, ADMIN_IDS
from database.db import init_db
from handlers.user import register

init_db(); bot=telebot.TeleBot(BOT_TOKEN,parse_mode='HTML'); register(bot,ADMIN_IDS)
@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id not in ADMIN_IDS:return
    from database.db import connection
    with connection() as db:
        u=db.execute('SELECT COUNT(*) c FROM users').fetchone()['c']; b=db.execute('SELECT COALESCE(SUM(balance),0) b FROM users').fetchone()['b']
    bot.send_message(message.chat.id,f'📊 المستخدمون: {u}\n💰 مجموع الأرصدة: {b}')
@bot.message_handler(commands=['backup'])
def backup_cmd(message):
    if message.from_user.id not in ADMIN_IDS:return
    from utils.backup import backup
    p=backup();bot.send_document(message.chat.id,open(p,'rb'),caption='✅ نسخة احتياطية')

if __name__=='__main__': bot.infinity_polling(skip_pending=True)
