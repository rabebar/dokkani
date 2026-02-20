# ==========================================
# database.py — النسخة الكاملة والمصححة (دكّاني)
# ==========================================

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
import math

def get_db():
    """الاتصال بقاعدة البيانات (PostgreSQL للإنتاج و SQLite للتطوير)"""
    db_url = os.environ.get('DATABASE_URL') or getattr(Config, 'DATABASE_URL', None)
    
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url)
    else:
        import sqlite3
        conn = sqlite3.connect('dokkani.db')
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=(), commit=False, fetchone=False, fetchall=False):
    """المحرك الموحد: يعيد البيانات دائماً كقواميس (Dictionaries) قابلة للتعديل"""
    conn = get_db()
    is_pg = not hasattr(conn, 'row_factory')
    
    try:
        if is_pg:
            query = query.replace('?', '%s')
            cur = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cur = conn.cursor()
        
        cur.execute(query, params)
        
        res = None
        if fetchone:
            raw = cur.fetchone()
            if raw:
                res = dict(raw)
        elif fetchall:
            raw = cur.fetchall()
            if raw:
                res = [dict(r) for r in raw]
        else:
            res = None

        if commit:
            conn.commit()
            if "INSERT" in query.upper():
                if is_pg:
                    cur.execute("SELECT lastval()")
                    res = cur.fetchone()['lastval']
                else:
                    res = cur.lastrowid
        return res
    finally:
        conn.close()

def init_db():
    """تأسيس الجداول - تعمل لمرة واحدة عند تشغيل النظام"""
    is_pg = os.environ.get('DATABASE_URL') is not None
    pk = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"

    execute_query(f'''CREATE TABLE IF NOT EXISTS categories (
        id      {pk},
        name    TEXT NOT NULL,
        icon    TEXT DEFAULT '🛒',
        image   TEXT,
        visible INTEGER DEFAULT 1,
        sort    INTEGER DEFAULT 0
    )''', commit=True)

    execute_query(f'''CREATE TABLE IF NOT EXISTS subcategories (
        id          {pk},
        name        TEXT NOT NULL,
        icon        TEXT DEFAULT '📦',
        image       TEXT,
        category_id INTEGER,
        visible     INTEGER DEFAULT 1,
        sort        INTEGER DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )''', commit=True)

    execute_query(f'''CREATE TABLE IF NOT EXISTS products (
        id             {pk},
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
    )''', commit=True)

    execute_query(f'''CREATE TABLE IF NOT EXISTS orders (
        id           {pk},
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
    )''', commit=True)

    if is_pg:
        try:
            execute_query("SELECT setval(pg_get_serial_sequence('orders', 'id'), COALESCE((SELECT MAX(id) FROM orders), 845), true)", commit=True)
        except:
            pass

    execute_query(f'''CREATE TABLE IF NOT EXISTS customers (
        id           {pk},
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
    )''', commit=True)

    check = execute_query('SELECT COUNT(*) as count FROM categories', fetchone=True)
    if check and check['count'] == 0:
        seed_categories()
        seed_subcategories()

def seed_categories():
    cats = [
        ('خضروات وفواكه', '🥦', 1), ('مواد تموينية ومعلبات', '🥫', 2),
        ('أرز ومعكرونة', '🍚', 3), ('زيوت وسمنة', '🫙', 4),
        ('لحوم ودواجن', '🥩', 5), ('سلطات وأطباق جاهزة', '🥗', 6),
        ('ألبان وأجبان وبيض', '🥛', 7), ('خبز ومعجنات', '🍞', 8),
        ('مياه معدنية', '💧', 9), ('مجمدات ومفرزات', '🧊', 10),
        ('مكسرات وفواكه مجففة', '🥜', 11), ('بقوليات وبذور', '🫘', 12),
        ('بوظة ومثلجات', '🍦', 13), ('شوكولاتة وحلويات', '🍫', 14),
        ('مشروبات غازية وعصائر', '🧃', 15), ('شيبس ومسليات', '🍿', 16),
        ('صوص وبهارات', '🌶️', 17), ('قهوة وشاي', '☕', 18),
        ('أكل صحي وحبوب إفطار', '🌾', 19), ('منظفات وعناية منزلية', '🧹', 20),
        ('مستلزمات أطفال', '👶', 21), ('بلاستيك وأكياس وقصدير', '🛍️', 22),
        ('عناية شخصية', '🧴', 23), ('مستلزمات حيوانات', '🐾', 24),
        ('صيدلية', '💊', 25), ('أخرى', '📦', 26),
    ]
    for cat in cats:
        execute_query('INSERT INTO categories (name, icon, sort) VALUES (?, ?, ?)', cat, commit=True)

def seed_subcategories():
    subs = [
        ('خضروات طازجة', '🥬', 1), ('فواكه طازجة', '🍎', 1), ('أعشاب وتوابل طازجة', '🌿', 1),
        ('معلبات خضار وفواكه', '🥫', 2), ('معلبات لحوم وأسماك', '🐟', 2), ('مربى وعسل', '🍯', 2),
        ('أرز', '🍚', 3), ('معكرونة وشعيرية', '🍝', 3), ('برغل وفريكة', '🌾', 3),
        ('زيت زيتون', '🫒', 4), ('زيوت نباتية', '🫙', 4), ('سمنة وزبدة', '🧈', 4),
        ('لحوم طازجة', '🥩', 5), ('دواجن طازجة', '🍗', 5), ('لحوم باردة ومدخنة', '🥓', 5), ('أسماك ومأكولات بحرية', '🐟', 5),
        ('سلطات جاهزة', '🥗', 6), ('مقبلات وفتوش', '🫙', 6),
        ('حليب وكريمة', '🥛', 7), ('أجبان', '🧀', 7), ('زبادي ولبن', '🥣', 7), ('بيض', '🥚', 7),
        ('خبز طازج', '🍞', 8), ('معجنات وكعك', '🥐', 8), ('توست وخبز صناعي', '🍞', 8),
        ('مياه معدنية', '💧', 9), ('مياه غازية', '🫧', 9),
        ('خضار مجمدة', '🥦', 10), ('لحوم مجمدة', '🥩', 10), ('وجبات مجمدة', '🍱', 10),
        ('مكسرات محمصة', '🥜', 11), ('فواكه مجففة', '🍇', 11), ('بذور', '🌻', 11),
        ('عدس وحمص', '🫘', 12), ('فول وفاصوليا', '🫘', 12),
        ('بوظة كيلو', '🍨', 13), ('مثلجات فردية', '🍦', 13),
        ('شوكولاتة', '🍫', 14), ('حلوى وسكاكر', '🍬', 14), ('بسكويت وكيك', '🍪', 14),
        ('مشروبات غازية', '🥤', 15), ('عصائر معبأة', '🧃', 15), ('مشروبات طاقة', '⚡', 15),
        ('شيبس', '🍿', 16), ('مقرمشات وبسكويت مالح', '🥨', 16),
        ('صوص وكاتشب', '🍅', 17), ('بهارات وتوابل', '🌶️', 17), ('خل وليمون', '🍋', 17),
        ('قهوة', '☕', 18), ('شاي وأعشاب', '🍵', 18),
        ('حبوب إفطار', '🌾', 19), ('بروتين وفيتامينات', '💪', 19), ('أغذية عضوية', '🌱', 19),
        ('منظفات مطبخ', '🍽️', 20), ('منظفات أرضيات', '🧹', 20), ('محارم ومناديل', '🧻', 20),
        ('حفاضات', '👶', 21), ('طعام أطفال', '🍼', 21), ('مستلزمات رضع', '🍼', 21),
        ('أكياس', '🛍️', 22), ('قصدير ولفائف', '🥫', 22), ('أواني بلاستيك', '🫙', 22),
        ('شامبو وبلسم', '🧴', 23), ('صابون وغسول', '🧼', 23), ('عناية بالبشرة', '✨', 23), ('عناية بالأسنان', '🪥', 23),
        ('طعام قطط', '🐱', 24), ('طعام كلاب', '🐶', 24), ('مستلزمات حيوانات', '🐾', 24),
        ('فيتامينات', '💊', 25), ('مستلزمات طبية', '🩺', 25), ('عناية جروح', '🩹', 25),
        ('متنوعات', '📦', 26),
    ]
    for sub in subs:
        execute_query('INSERT INTO subcategories (name, icon, category_id) VALUES (?, ?, ?)', sub, commit=True)

# --- دوال الأقسام الرئيسية ---
def get_categories(visible_only=True):
    q = 'SELECT * FROM categories'
    if visible_only: q += ' WHERE visible=1'
    q += ' ORDER BY sort, id'
    return execute_query(q, fetchall=True) or []

def add_category(name, icon, image=None):
    execute_query('INSERT INTO categories (name, icon, image) VALUES (?, ?, ?)', (name, icon, image), commit=True)

def update_category(cat_id, name, icon, image=None):
    if image:
        execute_query('UPDATE categories SET name=?, icon=?, image=? WHERE id=?', (name, icon, image, cat_id), commit=True)
    else:
        execute_query('UPDATE categories SET name=?, icon=? WHERE id=?', (name, icon, cat_id), commit=True)

def toggle_category(cat_id):
    execute_query('UPDATE categories SET visible=1-visible WHERE id=?', (cat_id,), commit=True)

def delete_category(cat_id):
    execute_query('DELETE FROM subcategories WHERE category_id=?', (cat_id,), commit=True)
    execute_query('DELETE FROM products WHERE category_id=?', (cat_id,), commit=True)
    execute_query('DELETE FROM categories WHERE id=?', (cat_id,), commit=True)

# --- دوال الأقسام الفرعية ---
def get_subcategories(category_id=None, visible_only=True):
    if category_id:
        q = '''
            SELECT s.*, 
            (SELECT COUNT(*) FROM products p WHERE p.subcategory_id = s.id) as product_count
            FROM subcategories s 
            WHERE s.category_id=?
        '''
        if visible_only: q += ' AND visible=1'
        q += ' ORDER BY sort, id'
        return execute_query(q, (category_id,), fetchall=True) or []
    else:
        q = '''
            SELECT s.*, 
            (SELECT COUNT(*) FROM products p WHERE p.subcategory_id = s.id) as product_count
            FROM subcategories s
        '''
        if visible_only: q += ' WHERE visible=1'
        q += ' ORDER BY category_id, sort, id'
        return execute_query(q, fetchall=True) or []

def add_subcategory(name, icon, category_id, image=None):
    execute_query('INSERT INTO subcategories (name, icon, category_id, image) VALUES (?, ?, ?, ?)', (name, icon, category_id, image), commit=True)

def update_subcategory(sub_id, name, icon, category_id, image=None):
    if image:
        execute_query('UPDATE subcategories SET name=?, icon=?, category_id=?, image=? WHERE id=?', (name, icon, category_id, image, sub_id), commit=True)
    else:
        execute_query('UPDATE subcategories SET name=?, icon=?, category_id=? WHERE id=?', (name, icon, category_id, sub_id), commit=True)

def toggle_subcategory(sub_id):
    execute_query('UPDATE subcategories SET visible=1-visible WHERE id=?', (sub_id,), commit=True)

def delete_subcategory(sub_id):
    execute_query('DELETE FROM products WHERE subcategory_id=?', (sub_id,), commit=True)
    execute_query('DELETE FROM subcategories WHERE id=?', (sub_id,), commit=True)

# --- دوال المنتجات ---
def get_products(category_id=None, subcategory_id=None, visible_only=True):
    q = 'SELECT * FROM products WHERE 1=1'
    params = []
    if category_id:
        q += ' AND category_id=?'; params.append(category_id)
    if subcategory_id:
        q += ' AND subcategory_id=?'; params.append(subcategory_id)
    if visible_only:
        q += ' AND visible=1'
    q += ' ORDER BY sort, id'
    return execute_query(q, tuple(params), fetchall=True) or []

def get_products_with_sell_price(category_id=None, subcategory_id=None, visible_only=True):
    products = get_products(category_id, subcategory_id, visible_only)
    for p in products:
        p['sell_price'] = get_selling_price(p['price'])
    return products

def add_product(name, price, unit, category_id, subcategory_id=None, image=None):
    execute_query('INSERT INTO products (name, price, unit, category_id, subcategory_id, image) VALUES (?, ?, ?, ?, ?, ?)', (name, price, unit, category_id, subcategory_id, image), commit=True)

def update_product(prod_id, name, price, unit, category_id, subcategory_id=None, image=None):
    if image:
        execute_query('UPDATE products SET name=?, price=?, unit=?, category_id=?, subcategory_id=?, image=? WHERE id=?', (name, price, unit, category_id, subcategory_id, image, prod_id), commit=True)
    else:
        execute_query('UPDATE products SET name=?, price=?, unit=?, category_id=?, subcategory_id=? WHERE id=?', (name, price, unit, category_id, subcategory_id, prod_id), commit=True)

def toggle_product(prod_id):
    execute_query('UPDATE products SET visible=1-visible WHERE id=?', (prod_id,), commit=True)

def delete_product(prod_id):
    execute_query('DELETE FROM products WHERE id=?', (prod_id,), commit=True)
    
def clear_all_products():
    """مسح كافة المنتجات من القاعدة للبدء من جديد"""
    execute_query('DELETE FROM products', commit=True)
    return True

# --- دوال الطلبات ---
def add_order(data):
    items_json = json.dumps(data.get('items', []), ensure_ascii=False)
    order_id = execute_query('''INSERT INTO orders
        (name, phone, whatsapp, neighborhood, address, lat, lng, items, total, delivery, profit, payment, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')''',
        (data.get('name'), data.get('phone'), data.get('whatsapp'),
         data.get('neighborhood'), data.get('address'),
         data.get('lat'), data.get('lng'), items_json,
         data.get('total'), data.get('delivery'), data.get('profit'),
         data.get('payment'), data.get('notes')), commit=True)

    existing = execute_query('SELECT id, orders_count, total_spent FROM customers WHERE phone=?', (data.get('phone'),), fetchone=True)
    if existing:
        new_count = (existing.get('orders_count') or 0) + 1
        new_total = (existing.get('total_spent') or 0) + (data.get('total') or 0)
        execute_query('UPDATE customers SET orders_count=?, total_spent=?, name=? WHERE id=?',
                     (new_count, new_total, data.get('name'), existing.get('id')), commit=True)
    else:
        execute_query('''INSERT INTO customers (name, phone, whatsapp, neighborhood, address, lat, lng, orders_count, total_spent)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)''',
            (data.get('name'), data.get('phone'), data.get('whatsapp'),
             data.get('neighborhood'), data.get('address'),
             data.get('lat'), data.get('lng'), data.get('total', 0)), commit=True)
    return order_id

def get_orders(phone=None):
    if phone:
        rows = execute_query('SELECT * FROM orders WHERE phone=? ORDER BY created_at DESC', (phone,), fetchall=True)
    else:
        rows = execute_query('SELECT * FROM orders ORDER BY created_at DESC', fetchall=True)

    rows = rows or []
    status_map = {'new': '🆕 جديد', 'prep': '⏳ تحضير', 'delivering': '🚗 توصيل', 'done': '✅ تم', 'cancelled': '❌ ملغي'}

    for o in rows:
        items_value = o.get('items')
        if isinstance(items_value, str):
            try:
                o['items'] = json.loads(items_value)
            except:
                o['items'] = []
        elif items_value is None:
            o['items'] = []
        o['status_text'] = status_map.get(o['status'], o['status'])
    return rows

def update_order_status(order_id, status):
    execute_query('UPDATE orders SET status=? WHERE id=?', (status, order_id), commit=True)

# --- دوال الزبائن والمحاسبة ---
def get_customers():
    rows = execute_query('SELECT * FROM customers ORDER BY orders_count DESC', fetchall=True) or []
    for c in rows: c['vip'] = (c.get('orders_count') or 0) >= 3
    return rows

def delete_customer(phone):
    execute_query('DELETE FROM customers WHERE phone=?', (phone,), commit=True)

def get_daily_stats():
    orders = execute_query('SELECT * FROM orders', fetchall=True) or []
    completed = [o for o in orders if o['status'] == 'done']
    total_profit = sum(((o.get('profit') or 0) + (o.get('delivery') or 0)) for o in completed)
    active_orders = [o for o in orders if o['status'] not in ['done', 'cancelled']]

    return {
        'orders_count':   len(active_orders),
        'completed_count': len(completed),
        'total_sales':    round(sum(o.get('total') or 0 for o in completed), 2),
        'daily_profit':   round(total_profit, 2),
        'total_expenses': 0,
        'net_profit':     round(total_profit, 2),
        'expenses': [{'name': '⛽ بنزين', 'val': 0}, {'name': '📱 إنترنت', 'val': 0}, {'name': '🛍️ أكياس', 'val': 0}]
    }

# --- دوال التسعير والمسافة ---
def calculate_profit(price):
    if price <= 8: return 1.0
    elif price <= 19: return 1.5
    else: return 2.0

def get_selling_price(price):
    return round(price + calculate_profit(price), 2)

def get_order_profit(items):
    total = 0
    for item in items:
        price = float(item.get('price', 0)); qty = float(item.get('qty', 1))
        if item.get('type') == 'veg': total += 1.0 * qty
        elif item.get('type') == 'meat': total += 2.0 * qty
        else: total += calculate_profit(price) * qty
    return round(total, 2)

def calculate_delivery_fee(lat, lng):
    if not lat or not lng: return 10.0
    store_lat, store_lng = 31.9038, 35.2034
    lat1, lon1 = math.radians(store_lat), math.radians(store_lng)
    lat2, lon2 = math.radians(float(lat)), math.radians(float(lng))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance_km = 6371 * c
    delivery = 8 + (distance_km * 2.25)
    return round(max(10, min(18, delivery)), 1)


# ==========================================
# محرك جلب الصور من Open Food Facts
# ==========================================

def fetch_product_image(product_name):
    """
    يبحث عن صورة المنتج في Open Food Facts بالاسم
    يحفظها في /static/uploads/ ويرجع المسار أو None
    لا يرمي أي استثناء — الفشل الصامت مقصود
    """
    import requests

    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    try:
        resp = requests.get(
            'https://world.openfoodfacts.org/cgi/search.pl',
            params={
                'search_terms': product_name,
                'search_simple': 1,
                'action': 'process',
                'json': 1,
                'page_size': 3,  # خفضنا من 5 إلى 3 للسرعة
                'fields': 'product_name,image_front_small_url,image_url'
            },
            timeout=3  # خفضنا من 8 إلى 3 ثواني
        )
        if resp.status_code != 200:
            return None

        products = resp.json().get('products', [])
        if not products:
            return None

        image_url = None
        for p in products:
            img = p.get('image_front_small_url') or p.get('image_url')
            if img and img.startswith('http'):
                image_url = img
                break

        if not image_url:
            return None

        img_resp = requests.get(image_url, timeout=3)  # خفضنا من 8 إلى 3 ثواني
        if img_resp.status_code != 200:
            return None

        content_type = img_resp.headers.get('Content-Type', '')
        if 'png' in content_type:
            ext = 'png'
        elif 'webp' in content_type:
            ext = 'webp'
        else:
            ext = 'jpg'

        filename = f"auto_{os.urandom(6).hex()}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        with open(filepath, 'wb') as f:
            f.write(img_resp.content)

        return f"/static/uploads/{filename}"

    except Exception:
        return None


def fetch_images_background(product_ids_names):
    """
    يجلب الصور في الخلفية بعد انتهاء الاستيراد
    product_ids_names: قائمة من [(product_id, product_name), ...]
    """
    import threading

    def _worker():
        for prod_id, prod_name in product_ids_names:
            try:
                # تحقق أن المنتج ما زال بدون صورة قبل الجلب
                existing = execute_query(
                    'SELECT image FROM products WHERE id=?',
                    (prod_id,), fetchone=True
                )
                if existing and not existing.get('image'):
                    auto_image = fetch_product_image(prod_name)
                    if auto_image:
                        execute_query(
                            'UPDATE products SET image=? WHERE id=?',
                            (auto_image, prod_id), commit=True
                        )
            except Exception:
                continue  # فشل صامت لكل منتج

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ==========================================
# محرك استيراد Excel الذكي + جلب الصور
# ==========================================

def import_excel_to_db(file_path):
    """
    يقرأ ملف Excel ويستورد المنتجات ذكياً مع:
    - مواءمة الأعمدة تلقائياً بالعربي والإنجليزي
    - إنشاء الأقسام غير الموجودة تلقائياً (Auto-Provisioning)
    - Upsert: تحديث إن وُجد، إنشاء إن كان جديداً
    - جلب الصور في الخلفية بعد الاستيراد (لتجنب Timeout)
    """
    import pandas as pd

    COLUMN_MAP = {
        'name': [
            'اسم المنتج', 'المنتج', 'اسم', 'الاسم',
            'name', 'product', 'product_name', 'item', 'title'
        ],
        'price': [
            'السعر', 'سعر الشراء', 'سعر', 'التكلفة',
            'price', 'cost', 'buy_price', 'purchase_price'
        ],
        'unit': [
            'الوحدة', 'وحدة القياس', 'وحدة',
            'unit', 'measure', 'uom'
        ],
        'category': [
            'القسم الرئيسي', 'القسم', 'قسم', 'التصنيف',
            'category', 'cat', 'section', 'department'
        ],
        'subcategory': [
            'القسم الفرعي', 'الفئة الفرعية', 'فرعي',
            'subcategory', 'sub', 'sub_category', 'subcategory_name'
        ]
    }

    def find_column(df_columns, candidates):
        df_cols_lower = {c.strip().lower(): c for c in df_columns}
        for candidate in candidates:
            if candidate.strip().lower() in df_cols_lower:
                return df_cols_lower[candidate.strip().lower()]
        return None

    # قراءة الملف
    try:
        df = pd.read_excel(file_path, dtype=str)
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
    except Exception as e:
        return {'success': False, 'error': f'فشل قراءة الملف: {str(e)}',
                'created': 0, 'updated': 0, 'errors': 0, 'images': 0}

    # تحديد الأعمدة
    col_name     = find_column(df.columns, COLUMN_MAP['name'])
    col_price    = find_column(df.columns, COLUMN_MAP['price'])
    col_unit     = find_column(df.columns, COLUMN_MAP['unit'])
    col_category = find_column(df.columns, COLUMN_MAP['category'])
    col_subcat   = find_column(df.columns, COLUMN_MAP['subcategory'])

    if not col_name or not col_price:
        missing = []
        if not col_name:  missing.append('اسم المنتج')
        if not col_price: missing.append('السعر')
        return {
            'success': False,
            'error': f'الأعمدة التالية غير موجودة: {", ".join(missing)}. الأعمدة الموجودة: {", ".join(df.columns.tolist())}',
            'created': 0, 'updated': 0, 'errors': 0, 'images': 0
        }

    def get_or_create_category(name):
        name = name.strip()
        existing = execute_query('SELECT id FROM categories WHERE name=?', (name,), fetchone=True)
        if existing:
            return existing['id']
        return execute_query('INSERT INTO categories (name, icon, visible) VALUES (?, ?, 1)', (name, '📦'), commit=True)

    def get_or_create_subcategory(name, category_id):
        name = name.strip()
        existing = execute_query('SELECT id FROM subcategories WHERE name=? AND category_id=?', (name, category_id), fetchone=True)
        if existing:
            return existing['id']
        return execute_query('INSERT INTO subcategories (name, icon, category_id, visible) VALUES (?, ?, ?, 1)', (name, '📦', category_id), commit=True)

    created    = 0
    updated    = 0
    errors     = 0
    error_rows = []
    # قائمة المنتجات التي تحتاج صور — للجلب في الخلفية
    needs_image = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            name      = str(row[col_name]).strip()  if pd.notna(row[col_name])  else ''
            price_raw = str(row[col_price]).strip() if pd.notna(row[col_price]) else ''

            if not name or not price_raw or name == 'nan':
                errors += 1
                error_rows.append(f'صف {row_num}: اسم أو سعر فارغ')
                continue

            price_clean = price_raw.replace('₪','').replace('$','').replace(',','').strip()
            try:
                price = float(price_clean)
            except:
                errors += 1
                error_rows.append(f'صف {row_num}: سعر غير صالح "{price_raw}"')
                continue

            unit = str(row[col_unit]).strip() if col_unit and pd.notna(row[col_unit]) else 'حبة'
            if unit in ('nan', ''): unit = 'حبة'

            category_id = None
            if col_category and pd.notna(row[col_category]):
                cat_name = str(row[col_category]).strip()
                if cat_name and cat_name != 'nan':
                    category_id = get_or_create_category(cat_name)
            if not category_id:
                default_cat = execute_query('SELECT id FROM categories ORDER BY id DESC', fetchone=True)
                category_id = default_cat['id'] if default_cat else 1

            subcategory_id = None
            if col_subcat and pd.notna(row[col_subcat]):
                sub_name = str(row[col_subcat]).strip()
                if sub_name and sub_name != 'nan':
                    subcategory_id = get_or_create_subcategory(sub_name, category_id)

            existing_prod = execute_query(
                'SELECT id, image FROM products WHERE name=? AND category_id=?',
                (name, category_id), fetchone=True
            )

            if existing_prod:
                execute_query(
                    'UPDATE products SET price=?, unit=?, subcategory_id=? WHERE id=?',
                    (price, unit, subcategory_id, existing_prod['id']), commit=True
                )
                # أضف للخلفية فقط إن لم تكن له صورة
                if not existing_prod.get('image'):
                    needs_image.append((existing_prod['id'], name))
                updated += 1
            else:
                new_id = execute_query(
                    'INSERT INTO products (name, price, unit, category_id, subcategory_id, visible) VALUES (?, ?, ?, ?, ?, 1)',
                    (name, price, unit, category_id, subcategory_id), commit=True
                )
                # كل منتج جديد يحتاج صورة
                needs_image.append((new_id, name))
                created += 1

        except Exception as e:
            errors += 1
            error_rows.append(f'صف {row_num}: خطأ غير متوقع — {str(e)}')
            continue

    # ابدأ جلب الصور في الخلفية بعد انتهاء الاستيراد
    if needs_image:
        fetch_images_background(needs_image)

    return {
        'success':    True,
        'created':    created,
        'updated':    updated,
        'errors':     errors,
        'images':     len(needs_image),  # عدد المنتجات التي سيُجلب لها صور
        'error_rows': error_rows[:10]
    }