import uuid
from database.db import connection

def _finish(db):
    db.execute('COMMIT')

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
        db.execute('INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)',(user_id,kind,int(amount),before,after,reference,description))
        _finish(db); return {'ok':True,'balance':after}

def buy_tickets(user_id, quantity):
    if not 1 <= int(quantity) <= 100: return {'ok':False,'message':'عدد التذاكر غير صالح'}
    with connection() as db:
        db.execute('BEGIN IMMEDIATE'); r=db.execute("SELECT * FROM rounds WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
        if not r: db.execute('ROLLBACK'); return {'ok':False,'message':'لا توجد جولة نشطة'}
        total=r['ticket_price']*int(quantity); u=db.execute('SELECT balance,is_banned FROM users WHERE user_id=?',(user_id,)).fetchone()
        if not u or u['is_banned'] or u['balance']<total: db.execute('ROLLBACK'); return {'ok':False,'message':'الرصيد غير كافٍ'}
        before=u['balance']; after=before-total; ref=f'ticket:{r["id"]}:{user_id}:{uuid.uuid4().hex}'
        cur=db.execute('UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?',(total,user_id,total))
        if cur.rowcount != 1: db.execute('ROLLBACK'); return {'ok':False,'message':'تعذر إتمام العملية'}
        db.executemany('INSERT INTO tickets(round_id,user_id) VALUES(?,?)',[(r['id'],user_id)]*int(quantity))
        db.execute('INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)',(user_id,'TICKET',-total,before,after,ref,f'شراء {quantity} تذكرة'))
        _finish(db); return {'ok':True,'quantity':quantity,'balance':after}

def redeem(user_id, raw_code):
    code=raw_code.strip().upper()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE'); c=db.execute('SELECT * FROM gift_codes WHERE code=?',(code,)).fetchone()
        if not c: db.execute('ROLLBACK'); return {'ok':False,'message':'الكود غير صالح'}
        if c['expires_at'] and c['expires_at'] <= __import__('datetime').datetime.utcnow().isoformat(): db.execute('ROLLBACK'); return {'ok':False,'message':'انتهت صلاحية الكود'}
        if db.execute('SELECT 1 FROM gift_redemptions WHERE user_id=? AND code=?',(user_id,code)).fetchone(): db.execute('ROLLBACK'); return {'ok':False,'message':'تم استخدام الكود مسبقاً'}
        cur=db.execute('UPDATE gift_codes SET used_count=used_count+1 WHERE code=? AND used_count<max_uses',(code,))
        if cur.rowcount != 1: db.execute('ROLLBACK'); return {'ok':False,'message':'انتهت استخدامات الكود'}
        u=db.execute('SELECT balance,is_banned FROM users WHERE user_id=?',(user_id,)).fetchone()
        if not u or u['is_banned']: db.execute('ROLLBACK'); return {'ok':False,'message':'الحساب غير متاح'}
        before=u['balance']; after=before+c['points']; ref=f'gift:{code}:{user_id}'
        db.execute('UPDATE users SET balance=? WHERE user_id=?',(after,user_id)); db.execute('INSERT INTO gift_redemptions(user_id,code) VALUES(?,?)',(user_id,code)); db.execute('INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)',(user_id,'GIFT',c['points'],before,after,ref,'استبدال كود هدية')); _finish(db); return {'ok':True,'points':c['points'],'balance':after}

def create_deposit(user_id, amount, method, proof):
    amount=int(amount)
    if amount<=0 or not method.strip() or not proof.strip(): return {'ok':False,'message':'بيانات الشحن غير صالحة'}
    with connection() as db:
        try:
            cur=db.execute('INSERT INTO deposit_requests(user_id,amount,method,proof) VALUES(?,?,?,?)',(user_id,amount,method.strip(),proof.strip()))
            return {'ok':True,'id':cur.lastrowid}
        except Exception:
            return {'ok':False,'message':'رقم الإثبات مستخدم أو الطلب غير صالح'}

def create_withdrawal(user_id, amount, method, account):
    amount=int(amount); minimum=int(setting('min_withdraw','10000')) if False else 10000
    if amount<minimum or not method.strip() or not account.strip(): return {'ok':False,'message':f'الحد الأدنى للسحب {minimum} نقطة'}
    with connection() as db:
        db.execute('BEGIN IMMEDIATE'); row=db.execute('SELECT balance,is_banned FROM users WHERE user_id=?',(user_id,)).fetchone()
        if not row or row['is_banned'] or row['balance']<amount: db.execute('ROLLBACK'); return {'ok':False,'message':'الرصيد غير كافٍ'}
        ref=f'withdraw:{uuid.uuid4().hex}'; before=row['balance']; after=before-amount
        cur=db.execute('UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?',(amount,user_id,amount))
        if cur.rowcount!=1: db.execute('ROLLBACK'); return {'ok':False,'message':'تعذر حجز الرصيد'}
        try: cur=db.execute('INSERT INTO withdrawal_requests(user_id,amount,method,account) VALUES(?,?,?,?)',(user_id,amount,method.strip(),account.strip()))
        except Exception: db.execute('ROLLBACK'); return {'ok':False,'message':'لديك طلب سحب معلق'}
        db.execute('INSERT INTO ledger(user_id,type,amount,before_balance,after_balance,reference,description) VALUES(?,?,?,?,?,?,?)',(user_id,'WITHDRAW_HOLD',-amount,before,after,ref,'حجز طلب سحب')); _finish(db); return {'ok':True,'id':cur.lastrowid}
