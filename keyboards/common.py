from telebot import types

def button(text,data): return types.InlineKeyboardButton(text,callback_data=data)
def nav(back='home'):
    m=types.InlineKeyboardMarkup(row_width=2); m.row(button('⬅️ رجوع',back),button('🏠 الرئيسية','home')); m.row(button('✖️ إلغاء','cancel')); return m
def home(admin=False):
    m=types.InlineKeyboardMarkup(row_width=2)
    for row in [[('💰 المحفظة','wallet'),('🎟️ اليانصيب','lottery')],[('🎮 الألعاب','games'),('🎁 كود هدية','gift')],[('👤 حسابي','profile'),('ℹ️ المساعدة','help')]]: m.row(*(button(*x) for x in row))
    if admin:m.row(button('👑 الإدارة','admin'))
    return m
def wallet():
    m=types.InlineKeyboardMarkup(row_width=2);m.row(button('➕ شحن يدوي','deposit'),button('➖ سحب يدوي','withdraw'));m.row(button('📒 السجل','ledger'));m.row(button('⬅️ رجوع','home'),button('🏠 الرئيسية','home'));return m
def games():
    m=types.InlineKeyboardMarkup(row_width=2);m.row(button('🎲 النرد','dice'),button('🪙 العملة','coin'));m.add(button('⬅️ رجوع','home'),button('🏠 الرئيسية','home'));return m
def lottery():
    m=types.InlineKeyboardMarkup(row_width=2);m.row(button('🎟️ تذكرة واحدة','ticket:1'),button('🎟️ خمس تذاكر','ticket:5'));m.add(button('✏️ كمية مخصصة','ticket_custom'));m.add(button('⬅️ رجوع','home'),button('🏠 الرئيسية','home'));return m
