import uuid
from database.db import connection

def change_balance(user_id, amount, kind, description, reference=None):
    reference = reference or uuid.uuid4().hex
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM ledger WHERE reference=?',(reference,)).fetchone():
            db.execute('ROLLBACK'); return {'ok':True,'duplicate':True}
        row=db.execute('SELECT balance,is_banned FROM users WHERE user_id=?',(user_id,)).fetchone()
        if not row or row['is_banned']:
            db.execute('ROLLBACK'); return {'ok':False,'message':'الحساب غير متاح'}
        before=row['balance']; after=before+int(amount)
        if after<0:
            db.execute('ROLLBACK'); return {'ok':False,'message':'الرصيد غير كافٍ'}
        db.execute('UPDATE users SET balance=? WHERE user_id=?',(after,user_id))
        db.execute('INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)',(user_id,kind,amount,before,after,reference,description))
        db.execute('COMMIT'); return {'ok':True,'balance':after}

def buy_tickets(user_id, quantity):
    with connection() as db:
        db.execute('BEGIN IMMEDIATE'); r=db.execute("SELECT * FROM rounds WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
        if not r: db.execute('ROLLBACK'); return {'ok':False,'message':'لا توجد جولة نشطة'}
        total=r['ticket_price']*quantity; u=db.execute('SELECT balance,is_banned FROM users WHERE user_id=?',(user_id,)).fetchone()
        if not u or u['is_banned'] or u['balance']<total: db.execute('ROLLBACK'); return {'ok':False,'message':'الرصيد غير كافٍ'}
        before=u['balance']; after=before-total; ref=f'ticket:{r["id"]}:{user_id}:{uuid.uuid4().hex}'
        db.execute('UPDATE users SET balance=? WHERE user_id=? AND balance>=?',(after,user_id,total))
        if db.total_changes != 1: db.execute('ROLLBACK'); return {'ok':False,'message':'تعذر إتمام العملية'}
        db.executemany('INSERT INTO tickets(round_id,user_id) VALUES(?,?)',[(r['id'],user_id)]*quantity)
        db.execute('INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)',(user_id,'TICKET',-total,before,after,ref,f'شراء {quantity} تذكرة'))
        db.execute('COMMIT'); return {'ok':True,'quantity':quantity,'balance':after}

def redeem(user_id, raw_code):
    code=raw_code.strip().upper()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE'); c=db.execute('SELECT * FROM gift_codes WHERE code=?',(code,)).fetchone()
        if not c: db.execute('ROLLBACK'); return {'ok':False,'message':'الكود غير صالح'}
        if db.execute('SELECT 1 FROM gift_redemptions WHERE user_id=? AND code=?',(user_id,code)).fetchone(): db.execute('ROLLBACK'); return {'ok':False,'message':'تم استخدام الكود مسبقاً'}
        db.execute('UPDATE gift_codes SET used_count=used_count+1 WHERE code=? AND used_count<max_uses',(code,))
        if db.total_changes!=1: db.execute('ROLLBACK'); return {'ok':False,'message':'انتهت استخدامات الكود'}
        u=db.execute('SELECT balance FROM users WHERE user_id=?',(user_id,)).fetchone(); before=u['balance']; after=before+c['points']
        db.execute('UPDATE users SET balance=? WHERE user_id=?',(after,user_id)); db.execute('INSERT INTO gift_redemptions(user_id,code) VALUES(?,?)',(user_id,code)); db.execute('INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)',(user_id,'GIFT',c['points'],before,after,f'gift:{code}:{user_id}','استبدال كود هدية')); db.execute('COMMIT'); return {'ok':True,'points':c['points'],'balance':after}
