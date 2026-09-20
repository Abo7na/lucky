import random
from database.db import user, setting, connection
from services.wallet import change_balance,buy_tickets,redeem,create_deposit,create_withdrawal,spin_wheel
from keyboards.common import home,wallet,games,lottery,nav
from config import ADMIN_IDS

def register(bot,admins):
 @bot.message_handler(commands=['start','help'])
 def start(message):
  uid=message.from_user.id;args=message.text.split();new=user(uid,message.from_user.username,message.from_user.first_name);ref=int(args[1]) if len(args)>1 and args[1].isdigit() and int(args[1])!=uid else None
  if ref and new['referred_by'] is None:
   with connection() as db:
    exists=db.execute('SELECT user_id FROM users WHERE user_id=?',(ref,)).fetchone()
    if exists: db.execute('UPDATE users SET referred_by=? WHERE user_id=?',(ref,uid));change_balance(ref,int(setting('referral_reward','200')),'REFERRAL','مكافأة إحالة',f'referral:{ref}:{uid}')
  bot.send_message(uid,'🎰 <b>مرحباً بك في Lucky</b>\nاختر من القائمة:',parse_mode='HTML',reply_markup=home(uid in admins))
 @bot.message_handler(commands=['cancel'])
 def cancel(message):bot.clear_step_handler_by_chat_id(message.chat.id);bot.send_message(message.chat.id,'✖️ تم الإلغاء.',reply_markup=home(message.from_user.id in admins))
 @bot.callback_query_handler(func=lambda c:True)
 def callbacks(call):
  uid=call.from_user.id;data=call.data;bot.answer_callback_query(call.id)
  if data in ('home','cancel'):bot.clear_step_handler_by_chat_id(uid);bot.edit_message_text('🏠 <b>القائمة الرئيسية</b>',call.message.chat.id,call.message.message_id,parse_mode='HTML',reply_markup=home(uid in admins));return
  if data=='wallet':u=user(uid);bot.edit_message_text(f'💰 رصيدك: <b>{u["balance"]}</b> نقطة',call.message.chat.id,call.message.message_id,parse_mode='HTML',reply_markup=wallet());return
  if data=='wheel':bot.edit_message_text('🎡 أدر العجلة مرة كل 24 ساعة.',call.message.chat.id,call.message.message_id,reply_markup=nav('home'));return
  if data=='spin':
   r=spin_wheel(uid);bot.edit_message_text(('🎉 ربحت '+str(r['prize'])+' نقطة' if r['ok'] else '❌ '+r['message']),call.message.chat.id,call.message.message_id,reply_markup=nav('home'));return
  if data=='referral':
   me=bot.get_me();bot.edit_message_text(f'👥 رابط الإحالة:\n<code>https://t.me/{me.username}?start={uid}</code>',call.message.chat.id,call.message.message_id,parse_mode='HTML',reply_markup=nav());return
  if data=='deposit':msg=bot.send_message(uid,'➕ أرسل: المبلغ | الطريقة | الإثبات\nأرسل /cancel للإلغاء',reply_markup=nav('wallet'));bot.register_next_step_handler(msg,deposit_input);return
  if data=='withdraw':msg=bot.send_message(uid,'➖ أرسل: المبلغ | الطريقة | الحساب',reply_markup=nav('wallet'));bot.register_next_step_handler(msg,withdraw_input);return
  if data=='games':bot.edit_message_text('🎮 اختر اللعبة\nالتكلفة: '+setting('game_cost','50'),call.message.chat.id,call.message.message_id,reply_markup=games());return
  if data in ('dice','coin'):
   cost=int(setting('game_cost','50'));reward=int(setting('game_reward','120'));won=random.randint(1,100)<=int(setting('game_chance','40'));r=change_balance(uid,reward-cost if won else -cost,'GAME',data);bot.edit_message_text(('🎉 ربحت '+str(reward)+' نقطة' if won else '❌ خسرت '+str(cost)+' نقطة') if r.get('ok') else '❌ '+r.get('message','فشلت العملية'),call.message.chat.id,call.message.message_id,reply_markup=games());return
  if data=='lottery':bot.edit_message_text('🎟️ اختر عدد التذاكر:',call.message.chat.id,call.message.message_id,reply_markup=lottery());return
  if data.startswith('ticket:'):r=buy_tickets(uid,int(data.split(':')[1]));bot.edit_message_text('✅ تمت العملية' if r['ok'] else '❌ '+r['message'],call.message.chat.id,call.message.message_id,reply_markup=lottery());return
  if data=='ticket_custom':msg=bot.send_message(uid,'أرسل عدد التذاكر أو /cancel');bot.register_next_step_handler(msg,custom_ticket);return
  if data=='gift':msg=bot.send_message(uid,'🎁 أرسل كود الهدية أو /cancel',reply_markup=nav());bot.register_next_step_handler(msg,gift_input);return
  if data=='profile':u=user(uid);bot.edit_message_text(f'👤 <b>حسابي</b>\nالمعرف: <code>{uid}</code>\nالرصيد: <b>{u["balance"]}</b>',call.message.chat.id,call.message.message_id,parse_mode='HTML',reply_markup=nav());return
  if data=='help':bot.edit_message_text('استخدم الأزرار للتنقل. الشحن والسحب يعملان بعد تعطيل TEST_MODE.',call.message.chat.id,call.message.message_id,reply_markup=nav());return
 def custom_ticket(message):
  try:r=buy_tickets(message.from_user.id,max(1,min(100,int(message.text))));bot.send_message(message.chat.id,'✅ تمت العملية' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
  except ValueError:bot.send_message(message.chat.id,'❌ أرسل رقماً صحيحاً')
 def gift_input(message):
  if message.text=='/cancel':return cancel(message)
  r=redeem(message.from_user.id,message.text);bot.send_message(message.chat.id,'✅ أضيفت '+str(r.get('points',0))+' نقطة' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
 def deposit_input(message):
  if message.text=='/cancel':return cancel(message)
  try:a,m,p=[x.strip() for x in message.text.split('|',2)];r=create_deposit(message.from_user.id,int(a),m,p)
  except (ValueError,TypeError):r={'ok':False,'message':'الصيغة: المبلغ | الطريقة | الإثبات'}
  if r['ok']:
   for admin in admins:
    try:bot.send_message(admin,f'📥 طلب شحن جديد #{r["id"]} من <code>{message.from_user.id}</code>\n/approve_deposit {r["id"]}',parse_mode='HTML')
    except Exception:pass
  bot.send_message(message.chat.id,'✅ تم إرسال الطلب' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
 def withdraw_input(message):
  if message.text=='/cancel':return cancel(message)
  try:a,m,acc=[x.strip() for x in message.text.split('|',2)];r=create_withdrawal(message.from_user.id,int(a),m,acc)
  except (ValueError,TypeError):r={'ok':False,'message':'الصيغة: المبلغ | الطريقة | الحساب'}
  if r['ok']:
   for admin in admins:
    try:bot.send_message(admin,f'📤 طلب سحب جديد #{r["id"]} من <code>{message.from_user.id}</code>\n/approve_withdraw {r["id"]}',parse_mode='HTML')
    except Exception:pass
  bot.send_message(message.chat.id,'✅ تم حجز الرصيد وإرسال الطلب' if r['ok'] else '❌ '+r['message'],reply_markup=home(message.from_user.id in admins))
