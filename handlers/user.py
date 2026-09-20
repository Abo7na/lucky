import random
from database.db import user, setting
from services.wallet import change_balance, buy_tickets, redeem, create_deposit, create_withdrawal
from keyboards.common import home, wallet, games, lottery, nav


def register(bot, admins):
    @bot.message_handler(commands=['start','help'])
    def start(message):
        user(message.from_user.id,message.from_user.username,message.from_user.first_name)
        bot.send_message(message.chat.id,'🎰 <b>مرحباً بك في Lucky</b>\nاختر من القائمة:',parse_mode='HTML',reply_markup=home(message.from_user.id in admins))
    @bot.message_handler(commands=['cancel'])
    def cancel(message):
        bot.clear_step_handler_by_chat_id(message.chat.id); bot.send_message(message.chat.id,'✖️ تم الإلغاء.',reply_markup=home(message.from_user.id in admins))
    @bot.callback_query_handler(func=lambda c: True)
    def callbacks(call):
        uid=call.from_user.id; data=call.data; bot.answer_callback_query(call.id)
        if data in ('home','cancel'):
            bot.clear_step_handler_by_chat_id(call.message.chat.id); bot.edit_message_text('🏠 <b>القائمة الرئيسية</b>',call.message.chat.id,call.message.message_id,parse_mode='HTML',reply_markup=home(uid in admins)); return
        if data=='wallet':
            u=user(uid);bot.edit_message_text(f'💰 رصيدك: <b>{u["balance"]}</b> نقطة',call.message.chat.id,call.message.message_id,parse_mode='HTML',reply_markup=wallet());return
        if data=='deposit':
            msg=bot.send_message(uid,'➕ أرسل: المبلغ | الطريقة | رقم العملية\nمثال: 1000 | شام كاش | ABC123\nأرسل /cancel للإلغاء',reply_markup=nav('wallet'));bot.register_next_step_handler(msg,deposit_input);return
        if data=='withdraw':
            msg=bot.send_message(uid,'➖ أرسل: المبلغ | طريقة السحب | الحساب\nأرسل /cancel للإلغاء',reply_markup=nav('wallet'));bot.register_next_step_handler(msg,withdraw_input);return
        if data=='games':bot.edit_message_text('🎮 اختر اللعبة\nالتكلفة: '+setting('game_cost','50'),call.message.chat.id,call.message.message_id,reply_markup=games());return
        if data in ('dice','coin'):
            cost=int(setting('game_cost','50'));reward=int(setting('game_reward','120'));won=random.randint(1,100)<=int(setting('game_chance','40'));net=reward-cost if won else -cost;r=change_balance(uid,net,'GAME',data)
            bot.edit_message_text(('🎉 ربحت '+str(reward)+' نقطة' if won else '❌ خسرت '+str(cost)+' نقطة') if r.get('ok') else '❌ '+r.get('message','فشلت العملية'),call.message.chat.id,call.message.message_id,reply_markup=games());return
        if data=='lottery':bot.edit_message_text('🎟️ اختر عدد التذاكر:',call.message.chat.id,call.message.message_id,reply_markup=lottery());return
        if data.startswith('ticket:'):
            r=buy_tickets(uid,int(data.split(':')[1]));bot.edit_message_text('✅ تمت العملية' if r['ok'] else '❌ '+r['message'],call.message.chat.id,call.message.message_id,reply_markup=lottery());return
        if data=='ticket_custom':
            msg=bot.send_message(uid,'أرسل عدد التذاكر أو /cancel',reply_markup=nav('lottery'));bot.register_next_step_handler(msg,custom_ticket);return
        if data=='gift':
            msg=bot.send_message(uid,'🎁 أرسل كود الهدية أو /cancel',reply_markup=nav());bot.register_next_step_handler(msg,gift_input);return
        if data=='profile':
            u=user(uid);bot.edit_message_text(f'👤 <b>حسابي</b>\nالمعرف: <code>{uid}</code>\nالرصيد: <b>{u["balance"]}</b>',call.message.chat.id,call.message.message_id,parse_mode='HTML',reply_markup=nav());return
        if data=='help':bot.edit_message_text('استخدم الأزرار للتنقل. العمليات المالية تمر بالمراجعة الإدارية.',call.message.chat.id,call.message.message_id,reply_markup=nav());return
        if data=='admin' and uid in admins:bot.edit_message_text('👑 لوحة الإدارة\nاستخدم أوامر /stats و /backup.',call.message.chat.id,call.message.message_id,reply_markup=nav());return
    def custom_ticket(message):
        try:r=buy_tickets(message.from_user.id,max(1,min(100,int(message.text))));bot.send_message(message.chat.id,'✅ تمت العملية' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
        except ValueError:bot.send_message(message.chat.id,'❌ أرسل رقماً صحيحاً أو /cancel')
    def gift_input(message):
        if message.text=='/cancel':return cancel(message)
        r=redeem(message.from_user.id,message.text);bot.send_message(message.chat.id,'✅ أضيفت '+str(r.get('points',0))+' نقطة' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
    def deposit_input(message):
        if message.text=='/cancel':return cancel(message)
        try: amount,method,proof=[x.strip() for x in message.text.split('|',2)]; r=create_deposit(message.from_user.id,int(amount),method,proof)
        except (ValueError,TypeError): r={'ok':False,'message':'الصيغة: المبلغ | الطريقة | الإثبات'}
        bot.send_message(message.chat.id,'✅ تم إرسال طلب الشحن للمراجعة' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
    def withdraw_input(message):
        if message.text=='/cancel':return cancel(message)
        try: amount,method,account=[x.strip() for x in message.text.split('|',2)]; r=create_withdrawal(message.from_user.id,int(amount),method,account)
        except (ValueError,TypeError): r={'ok':False,'message':'الصيغة: المبلغ | الطريقة | الحساب'}
        bot.send_message(message.chat.id,'✅ تم حجز الرصيد وإرسال الطلب' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
