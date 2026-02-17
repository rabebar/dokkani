# ==========================================
# database.py — قاعدة بيانات دكّاني
# ==========================================

import sqlite3
import json
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config

def get_db():
    # التحقق إذا كنا على "رندر" (وجود رابط قاعدة البيانات)
    if Config.DATABASE_URL:
        conn = psycopg2.connect(Config.DATABASE_URL)
        # لكي نعيد البيانات على شكل قاموس (Dictionary) كما في SQLite
        return conn
    else:
        # الاتصال المحلي (للعمل على جهازك فقط)
        import sqlite3
        conn = sqlite3.connect('dokkani.db')
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=()):
    conn = get_db()
    # تحويل ? إلى %s إذا كان الاتصال بـ PostgreSQL
    if Config.DATABASE_URL:
        query = query.replace('?', '%s')
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cur = conn.cursor()
    
    cur.execute(query, params)
    return conn, cur

def init_db():
    conn = get_db()
    c = conn.cursor()

    # الأقسام الرئيسية
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name    TEXT NOT NULL,
        icon    TEXT DEFAULT '🛒',
        image   TEXT,
        visible INTEGER DEFAULT 1,
        sort    INTEGER DEFAULT 0
    )''')

    # الأقسام الفرعية
    c.execute('''CREATE TABLE IF NOT EXISTS subcategories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        icon        TEXT DEFAULT '📦',
        image       TEXT,
        category_id INTEGER,
        visible     INTEGER DEFAULT 1,
        sort        INTEGER DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )''')

    # المنتجات
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT NOT NULL,
        price          REAL NOT NULL,
        image          TEXT,
        unit           TEXT DEFAULT 'حبة',
        category_id    INTEGER,
        subcategory_id INTEGER,
        visible        INTEGER DEFAULT 1,
        sort           INTEGER DEFAULT 0,
        FOREIGN KEY (category_id)    REFERENCES categories(id),
        FOREIGN KEY (subcategory_id) REFERENCES subcategories(id)
    )''')

    # الطلبات
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT,
        phone        TEXT,
        whatsapp     TEXT,
        neighborhood TEXT,
        address      TEXT,
        lat          REAL,
        lng          REAL,
        items        TEXT,
        total        REAL,
        delivery     REAL,
        profit       REAL,
        payment      TEXT DEFAULT 'cash',
        notes        TEXT,
        status       TEXT DEFAULT 'new',
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # الزبائن
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT,
        phone        TEXT UNIQUE,
        whatsapp     TEXT,
        neighborhood TEXT,
        address      TEXT,
        lat          REAL,
        lng          REAL,
        orders_count INTEGER DEFAULT 0,
        total_spent  REAL DEFAULT 0,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()

    if c.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 0:
        seed_categories(c)
    if c.execute('SELECT COUNT(*) FROM subcategories').fetchone()[0] == 0:
        seed_subcategories(c)

    conn.commit()
    conn.close()


def seed_categories(c):
    cats = [
        ('خضروات وفواكه',               '🥦',  1),
        ('مواد تموينية ومعلبات',         '🥫',  2),
        ('أرز ومعكرونة',                 '🍚',  3),
        ('زيوت وسمنة',                   '🫙',  4),
        ('لحوم ودواجن',                  '🥩',  5),
        ('سلطات وأطباق جاهزة',           '🥗',  6),
        ('ألبان وأجبان وبيض',            '🥛',  7),
        ('خبز ومعجنات',                  '🍞',  8),
        ('مياه معدنية',                  '💧',  9),
        ('مجمدات ومفرزات',               '🧊',  10),
        ('مكسرات وفواكه مجففة',          '🥜',  11),
        ('بقوليات وبذور',                '🫘',  12),
        ('بوظة ومثلجات',                 '🍦',  13),
        ('شوكولاتة وحلويات',             '🍫',  14),
        ('مشروبات غازية وعصائر',         '🧃',  15),
        ('شيبس ومسليات',                 '🍿',  16),
        ('صوص وبهارات',                  '🌶️', 17),
        ('قهوة وشاي',                    '☕',  18),
        ('أكل صحي وحبوب إفطار',          '🌾',  19),
        ('منظفات وعناية منزلية',         '🧹',  20),
        ('مستلزمات أطفال',               '👶',  21),
        ('بلاستيك وأكياس وقصدير',        '🛍️', 22),
        ('عناية شخصية',                  '🧴',  23),
        ('مستلزمات حيوانات',             '🐾',  24),
        ('صيدلية',                       '💊',  25),
        ('أخرى',                         '📦',  26),
    ]
    c.executemany(
        'INSERT INTO categories (name,icon,sort) VALUES (?,?,?)', cats
    )


def seed_subcategories(c):
    subs = [
        # خضروات وفواكه (cat 1)
        ('خضروات طازجة',    '🥬', 1),
        ('فواكه طازجة',     '🍎', 1),
        ('أعشاب وتوابل طازجة', '🌿', 1),

        # مواد تموينية (cat 2)
        ('معلبات خضار وفواكه', '🥫', 2),
        ('معلبات لحوم وأسماك', '🐟', 2),
        ('مربى وعسل',         '🍯', 2),

        # أرز ومعكرونة (cat 3)
        ('أرز',              '🍚', 3),
        ('معكرونة وشعيرية',  '🍝', 3),
        ('برغل وفريكة',      '🌾', 3),

        # زيوت وسمنة (cat 4)
        ('زيت زيتون',        '🫒', 4),
        ('زيوت نباتية',      '🫙', 4),
        ('سمنة وزبدة',       '🧈', 4),

        # لحوم ودواجن (cat 5)
        ('لحوم طازجة',       '🥩', 5),
        ('دواجن طازجة',      '🍗', 5),
        ('لحوم باردة ومدخنة','🥓', 5),
        ('أسماك ومأكولات بحرية', '🐟', 5),

        # سلطات (cat 6)
        ('سلطات جاهزة',     '🥗', 6),
        ('مقبلات وفتوش',    '🫙', 6),

        # ألبان (cat 7)
        ('حليب وكريمة',     '🥛', 7),
        ('أجبان',           '🧀', 7),
        ('زبادي ولبن',      '🥣', 7),
        ('بيض',             '🥚', 7),

        # خبز (cat 8)
        ('خبز طازج',        '🍞', 8),
        ('معجنات وكعك',     '🥐', 8),
        ('توست وخبز صناعي', '🍞', 8),

        # مياه (cat 9)
        ('مياه معدنية',     '💧', 9),
        ('مياه غازية',      '🫧', 9),

        # مجمدات (cat 10)
        ('خضار مجمدة',      '🥦', 10),
        ('لحوم مجمدة',      '🥩', 10),
        ('وجبات مجمدة',     '🍱', 10),

        # مكسرات (cat 11)
        ('مكسرات محمصة',    '🥜', 11),
        ('فواكه مجففة',     '🍇', 11),
        ('بذور',            '🌻', 11),

        # بقوليات (cat 12)
        ('عدس وحمص',        '🫘', 12),
        ('فول وفاصوليا',    '🫘', 12),

        # بوظة (cat 13)
        ('بوظة كيلو',       '🍨', 13),
        ('مثلجات فردية',    '🍦', 13),

        # شوكولاتة (cat 14)
        ('شوكولاتة',        '🍫', 14),
        ('حلوى وسكاكر',     '🍬', 14),
        ('بسكويت وكيك',     '🍪', 14),

        # مشروبات (cat 15)
        ('مشروبات غازية',   '🥤', 15),
        ('عصائر معبأة',     '🧃', 15),
        ('مشروبات طاقة',    '⚡', 15),

        # شيبس (cat 16)
        ('شيبس',            '🍿', 16),
        ('مقرمشات وبسكويت مالح', '🥨', 16),

        # صوص وبهارات (cat 17)
        ('صوص وكاتشب',      '🍅', 17),
        ('بهارات وتوابل',   '🌶️', 17),
        ('خل وليمون',       '🍋', 17),

        # قهوة (cat 18)
        ('قهوة',            '☕', 18),
        ('شاي وأعشاب',      '🍵', 18),

        # أكل صحي (cat 19)
        ('حبوب إفطار',      '🌾', 19),
        ('بروتين وفيتامينات','💪', 19),
        ('أغذية عضوية',     '🌱', 19),

        # منظفات (cat 20)
        ('منظفات مطبخ',     '🍽️', 20),
        ('منظفات أرضيات',   '🧹', 20),
        ('محارم ومناديل',   '🧻', 20),

        # أطفال (cat 21)
        ('حفاضات',          '👶', 21),
        ('طعام أطفال',      '🍼', 21),
        ('مستلزمات رضع',    '🍼', 21),

        # بلاستيك (cat 22)
        ('أكياس',           '🛍️', 22),
        ('قصدير ولفائف',    '🥫', 22),
        ('أواني بلاستيك',   '🫙', 22),

        # عناية شخصية (cat 23)
        ('شامبو وبلسم',     '🧴', 23),
        ('صابون وغسول',     '🧼', 23),
        ('عناية بالبشرة',   '✨', 23),
        ('عناية بالأسنان',  '🪥', 23),

        # حيوانات (cat 24)
        ('طعام قطط',        '🐱', 24),
        ('طعام كلاب',       '🐶', 24),
        ('مستلزمات حيوانات','🐾', 24),

        # صيدلية (cat 25)
        ('فيتامينات',       '💊', 25),
        ('مستلزمات طبية',   '🩺', 25),
        ('عناية جروح',      '🩹', 25),

        # أخرى (cat 26)
        ('متنوعات',         '📦', 26),
    ]
    c.executemany(
        'INSERT INTO subcategories (name,icon,category_id) VALUES (?,?,?)', subs
    )


# ==========================================
# دوال الأقسام الرئيسية
# ==========================================

def get_categories(visible_only=True):
    conn = get_db()
    q = 'SELECT * FROM categories'
    if visible_only: q += ' WHERE visible=1'
    q += ' ORDER BY sort,id'
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name, icon, image=None):
    conn = get_db()
    conn.execute('INSERT INTO categories (name,icon,image) VALUES (?,?,?)', (name,icon,image))
    conn.commit(); conn.close()


def update_category(cat_id, name, icon, image=None):
    conn = get_db()
    if image:
        conn.execute('UPDATE categories SET name=?,icon=?,image=? WHERE id=?', (name,icon,image,cat_id))
    else:
        conn.execute('UPDATE categories SET name=?,icon=? WHERE id=?', (name,icon,cat_id))
    conn.commit(); conn.close()


def toggle_category(cat_id):
    conn = get_db()
    conn.execute('UPDATE categories SET visible=1-visible WHERE id=?', (cat_id,))
    conn.commit(); conn.close()


def delete_category(cat_id):
    conn = get_db()
    conn.execute('DELETE FROM subcategories WHERE category_id=?', (cat_id,))
    conn.execute('DELETE FROM products WHERE category_id=?', (cat_id,))
    conn.execute('DELETE FROM categories WHERE id=?', (cat_id,))
    conn.commit(); conn.close()


# ==========================================
# دوال الأقسام الفرعية
# ==========================================

def get_subcategories(category_id=None, visible_only=True):
    conn = get_db()
    if category_id:
        q = 'SELECT * FROM subcategories WHERE category_id=?'
        params = [category_id]
        if visible_only: q += ' AND visible=1'
        q += ' ORDER BY sort,id'
        rows = conn.execute(q, params).fetchall()
    else:
        q = 'SELECT * FROM subcategories'
        if visible_only: q += ' WHERE visible=1'
        q += ' ORDER BY category_id,sort,id'
        rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_subcategory(name, icon, category_id, image=None):
    conn = get_db()
    conn.execute(
        'INSERT INTO subcategories (name,icon,category_id,image) VALUES (?,?,?,?)',
        (name,icon,category_id,image)
    )
    conn.commit(); conn.close()


def update_subcategory(sub_id, name, icon, category_id, image=None):
    conn = get_db()
    if image:
        conn.execute(
            'UPDATE subcategories SET name=?,icon=?,category_id=?,image=? WHERE id=?',
            (name,icon,category_id,image,sub_id)
        )
    else:
        conn.execute(
            'UPDATE subcategories SET name=?,icon=?,category_id=? WHERE id=?',
            (name,icon,category_id,sub_id)
        )
    conn.commit(); conn.close()


def toggle_subcategory(sub_id):
    conn = get_db()
    conn.execute('UPDATE subcategories SET visible=1-visible WHERE id=?', (sub_id,))
    conn.commit(); conn.close()


def delete_subcategory(sub_id):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE subcategory_id=?', (sub_id,))
    conn.execute('DELETE FROM subcategories WHERE id=?', (sub_id,))
    conn.commit(); conn.close()


# ==========================================
# دوال المنتجات
# ==========================================

def get_products(category_id=None, subcategory_id=None, visible_only=True):
    conn = get_db()
    q = 'SELECT * FROM products WHERE 1=1'
    params = []
    if category_id:
        q += ' AND category_id=?'; params.append(category_id)
    if subcategory_id:
        q += ' AND subcategory_id=?'; params.append(subcategory_id)
    if visible_only:
        q += ' AND visible=1'
    q += ' ORDER BY sort,id'
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_products_with_sell_price(category_id=None, subcategory_id=None, visible_only=True):
    products = get_products(category_id, subcategory_id, visible_only)
    for p in products:
        p['sell_price'] = get_selling_price(p['price'])
    return products


def add_product(name, price, unit, category_id, subcategory_id=None, image=None):
    conn = get_db()
    conn.execute(
        'INSERT INTO products (name,price,unit,category_id,subcategory_id,image) VALUES (?,?,?,?,?,?)',
        (name,price,unit,category_id,subcategory_id,image)
    )
    conn.commit(); conn.close()


def update_product(prod_id, name, price, unit, category_id, subcategory_id=None, image=None):
    conn = get_db()
    if image:
        conn.execute(
            'UPDATE products SET name=?,price=?,unit=?,category_id=?,subcategory_id=?,image=? WHERE id=?',
            (name,price,unit,category_id,subcategory_id,image,prod_id)
        )
    else:
        conn.execute(
            'UPDATE products SET name=?,price=?,unit=?,category_id=?,subcategory_id=? WHERE id=?',
            (name,price,unit,category_id,subcategory_id,prod_id)
        )
    conn.commit(); conn.close()


def toggle_product(prod_id):
    conn = get_db()
    conn.execute('UPDATE products SET visible=1-visible WHERE id=?', (prod_id,))
    conn.commit(); conn.close()


def delete_product(prod_id):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id=?', (prod_id,))
    conn.commit(); conn.close()


# ==========================================
# دوال الطلبات
# ==========================================

def add_order(data):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO orders
        (name,phone,whatsapp,neighborhood,address,lat,lng,
         items,total,delivery,profit,payment,notes,status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'new')''',
        (data.get('name'), data.get('phone'), data.get('whatsapp'),
         data.get('neighborhood'), data.get('address'),
         data.get('lat'), data.get('lng'),
         json.dumps(data.get('items',[]), ensure_ascii=False),
         data.get('total'), data.get('delivery'), data.get('profit'),
         data.get('payment'), data.get('notes'))
    )
    order_id = c.lastrowid

    existing = conn.execute(
        'SELECT id,orders_count,total_spent FROM customers WHERE phone=?',
        (data.get('phone'),)
    ).fetchone()
    if existing:
        conn.execute(
            'UPDATE customers SET orders_count=?,total_spent=?,name=? WHERE id=?',
            (existing['orders_count']+1,
             existing['total_spent']+(data.get('total') or 0),
             data.get('name'), existing['id'])
        )
    else:
        conn.execute('''INSERT INTO customers
            (name,phone,whatsapp,neighborhood,address,lat,lng,orders_count,total_spent)
            VALUES (?,?,?,?,?,?,?,1,?)''',
            (data.get('name'), data.get('phone'), data.get('whatsapp'),
             data.get('neighborhood'), data.get('address'),
             data.get('lat'), data.get('lng'), data.get('total',0))
        )

    conn.commit(); conn.close()
    return order_id + 846


def get_orders(phone=None):
    conn = get_db()
    if phone:
        rows = conn.execute(
            'SELECT * FROM orders WHERE phone=? ORDER BY created_at DESC', (phone,)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM orders ORDER BY created_at DESC'
        ).fetchall()
    conn.close()
    orders = []
    status_map = {
        'new':'🆕 جديد','prep':'⏳ تحضير',
        'delivering':'🚗 توصيل','done':'✅ تم','cancelled':'❌ ملغي'
    }
    for r in rows:
        o = dict(r)
        try: o['items'] = json.loads(o['items']) if o['items'] else []
        except: o['items'] = []
        o['status_text'] = status_map.get(o['status'], o['status'])
        orders.append(o)
    return orders


def update_order_status(order_id, status):
    conn = get_db()
    conn.execute('UPDATE orders SET status=? WHERE id=?', (status,order_id))
    conn.commit(); conn.close()


# ==========================================
# دوال الزبائن
# ==========================================

def get_customers():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM customers ORDER BY orders_count DESC'
    ).fetchall()
    conn.close()
    customers = [dict(r) for r in rows]
    for c in customers:
        c['vip'] = c['orders_count'] >= 3
    return customers


def delete_customer(phone):
    conn = get_db()
    conn.execute('DELETE FROM customers WHERE phone=?', (phone,))
    conn.commit(); conn.close()


# ==========================================
# المحاسبة
# ==========================================

def get_daily_stats():
    conn = get_db()
    orders = conn.execute('SELECT * FROM orders').fetchall()
    conn.close()
    completed = [o for o in orders if o['status']=='done']
    total_profit = sum((o['profit'] or 0)+(o['delivery'] or 0) for o in completed)
    return {
        'orders_count':    len(orders),
        'completed_count': len(completed),
        'total_sales':     round(sum(o['total'] or 0 for o in completed), 2),
        'daily_profit':    round(total_profit, 2),
        'total_expenses':  0,
        'net_profit':      round(total_profit, 2),
        'expenses': [
            {'name':'⛽ بنزين','val':0},
            {'name':'📱 إنترنت','val':0},
            {'name':'🛍️ أكياس','val':0},
        ]
    }


# ==========================================
# دوال مساعدة
# ==========================================

def calculate_profit(price):
    if price <= 8:    return 0.5
    elif price <= 19: return 1.0
    else:             return 1.5

def get_selling_price(price):
    return round(price + calculate_profit(price), 2)

def get_order_profit(items):
    total = 0
    for item in items:
        if item.get('type')=='veg':   total += 1.0*float(item.get('qty',0))
        elif item.get('type')=='meat': total += 2.0*float(item.get('qty',0))
        else: total += calculate_profit(float(item.get('price',0)))*float(item.get('qty',1))
    return round(total, 2)

def is_vip(n): return n >= 3