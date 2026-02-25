# ==========================================
# app.py — المحرك الرئيسي المطور لتطبيق دكّاني
# ==========================================

import os
import time
from flask import Flask, render_template, request, jsonify, redirect
from config import Config
from telegram_notify import notify_new_order, notify_order_status
from database import (
    execute_query,
    init_db,
    get_categories, add_category, update_category, toggle_category, delete_category,
    get_subcategories, add_subcategory, update_subcategory, toggle_subcategory, delete_subcategory,
    get_products, get_products_with_sell_price, add_product, update_product, toggle_product, delete_product,
    get_orders, add_order, update_order_status,
    get_customers, delete_customer,
    get_daily_stats, get_order_profit, get_selling_price,
    calculate_delivery_fee,
    import_excel_to_db
)

app = Flask(__name__)
app.config.from_object(Config)

# ==========================================
# الحماية والأمان
# ==========================================
from functools import wraps
from flask import session, request, jsonify, redirect
from datetime import timedelta

app.permanent_session_lifetime = timedelta(hours=8)

# Rate limiting بسيط في الذاكرة
import time as _time
_rate_store = {}

def rate_limit(max_calls=10, window=60):
    """منع الطلبات المتكررة من نفس الـ IP"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            key = f"{ip}:{f.__name__}"
            now = _time.time()
            calls = [t for t in _rate_store.get(key, []) if now - t < window]
            if len(calls) >= max_calls:
                return jsonify({'success': False, 'error': 'طلبات كثيرة، انتظر قليلاً'}), 429
            calls.append(now)
            _rate_store[key] = calls
            return f(*args, **kwargs)
        return wrapped
    return decorator

def admin_required(f):
    """التحقق من تسجيل دخول الأدمن"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return wrapped

# Security Headers على كل رد
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# سجل لمنع تكرار الطلبات البرمجي
last_orders_check = {}

with app.app_context():
    init_db()

# قاموس ترجمة الأسماء العربية للإنجليزية لتحسين نتائج Unsplash
ARABIC_TO_EN = {
    # خضروات
    'بندورة': 'tomato', 'طماطم': 'tomato', 'خيار': 'cucumber',
    'بطاطا': 'potato', 'بطاطس': 'potato', 'جزر': 'carrot',
    'بصل': 'onion', 'ثوم': 'garlic', 'فلفل': 'pepper',
    'باذنجان': 'eggplant', 'كوسا': 'zucchini', 'ملفوف': 'cabbage',
    'خس': 'lettuce', 'سبانخ': 'spinach', 'بروكلي': 'broccoli',
    'قرنبيط': 'cauliflower', 'فاصولياء': 'green beans',
    'بازلاء': 'peas', 'ذرة': 'corn', 'شمندر': 'beet',
    # فواكه
    'تفاح': 'apple', 'موز': 'banana', 'برتقال': 'orange',
    'ليمون': 'lemon', 'عنب': 'grapes', 'فراولة': 'strawberry',
    'مانجو': 'mango', 'أناناس': 'pineapple', 'بطيخ': 'watermelon',
    'شمام': 'cantaloupe', 'كيوي': 'kiwi', 'خوخ': 'peach',
    'مشمش': 'apricot', 'كمثرى': 'pear', 'رمان': 'pomegranate',
    'تين': 'fig', 'زيتون': 'olive', 'تمر': 'dates',
    # ألبان وبيض
    'حليب': 'milk', 'جبنة': 'cheese', 'جبن': 'cheese',
    'زبادي': 'yogurt', 'لبن': 'yogurt', 'زبدة': 'butter',
    'قشطة': 'cream', 'كريمة': 'cream', 'بيض': 'eggs',
    # لحوم
    'دجاج': 'chicken', 'لحم': 'meat', 'سمك': 'fish',
    'تونة': 'tuna', 'لحمة': 'beef', 'كبدة': 'liver',
    # حبوب ومعكرونة
    'أرز': 'rice', 'معكرونة': 'pasta', 'باستا': 'pasta',
    'برغل': 'bulgur', 'عدس': 'lentils', 'حمص': 'chickpeas',
    'فريكة': 'freekeh', 'شعير': 'barley', 'قمح': 'wheat',
    'دقيق': 'flour', 'خبز': 'bread', 'توست': 'toast',
    # مشروبات
    'شاي': 'tea', 'قهوة': 'coffee', 'عصير': 'juice',
    'مياه': 'water', 'ماء': 'water', 'كولا': 'cola',
    'نيروز': 'water bottle', 'بيبسي': 'pepsi', 'فانتا': 'fanta',
    # زيوت وصلصات
    'زيت': 'oil', 'خل': 'vinegar', 'كاتشب': 'ketchup',
    'مايونيز': 'mayonnaise', 'مربى': 'jam', 'عسل': 'honey',
    'طحينة': 'tahini', 'ملح': 'salt', 'سكر': 'sugar',
    # منظفات
    'صابون': 'soap', 'شامبو': 'shampoo', 'منظف': 'detergent',
    'غسيل': 'laundry detergent', 'معقم': 'disinfectant',
    # حلويات وشوكولاتة
    'شوكولاتة': 'chocolate', 'بسكويت': 'biscuit', 'كيك': 'cake',
    'حلوى': 'candy', 'نوتيلا': 'nutella', 'كيت كات': 'kitkat',
    # قهوة وشاي
    'نسكافيه': 'nescafe', 'كابتشينو': 'cappuccino', 'أعشاب': 'herbal tea',
}

def translate_to_english(product_name):
    """يترجم اسم المنتج العربي للإنجليزي لتحسين نتائج البحث"""
    for ar, en in ARABIC_TO_EN.items():
        if ar in product_name:
            return en
    return product_name  # إذا لم يجد ترجمة يرجع الاسم كما هو


# --- وظيفة كشف نوع الجهاز ---
def is_mobile():
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_hints = ['android', 'iphone', 'ipad', 'mobile', 'windows phone', 'opera mini', 'blackberry']
    return any(hint in user_agent for hint in mobile_hints)

# ==========================================
# صفحات الزبون (الموبايل والكمبيوتر)
# ==========================================

@app.route('/')
def profile():
    if not is_mobile():
        return render_template('landing.html', app_name=Config.APP_NAME, app_phone=Config.APP_PHONE)
    return render_template('profile.html', app_name=Config.APP_NAME, app_phone=Config.APP_PHONE)

@app.route('/shop')
def shop():
    if not is_mobile():
        return render_template('landing.html', app_name=Config.APP_NAME, app_phone=Config.APP_PHONE)
    categories = get_categories()
    return render_template('shop.html', categories=categories, app_name=Config.APP_NAME, app_phone=Config.APP_PHONE)

@app.route('/category/<int:cat_id>')
def category_page(cat_id):
    if not is_mobile(): return redirect('/')
    cat = execute_query('SELECT * FROM categories WHERE id=?', (cat_id,), fetchone=True)
    if not cat: return redirect('/shop')
    subcats  = get_subcategories(category_id=cat_id)
    products = get_products_with_sell_price(category_id=cat_id)
    return render_template('category.html', cat=cat, subcats=subcats, products=products, app_name=Config.APP_NAME)

@app.route('/subcategory/<int:sub_id>')
def subcategory_page(sub_id):
    if not is_mobile(): return redirect('/')
    sub = execute_query('SELECT * FROM subcategories WHERE id=?', (sub_id,), fetchone=True)
    if not sub: return redirect('/shop')
    products = get_products_with_sell_price(subcategory_id=sub_id)
    cat = execute_query('SELECT * FROM categories WHERE id=?', (sub.get('category_id'),), fetchone=True)
    return render_template('subcategory.html', sub=sub, cat=cat, products=products, app_name=Config.APP_NAME)

@app.route('/cart')
def cart():
    if not is_mobile(): return redirect('/')
    return render_template('cart.html', app_name=Config.APP_NAME,
                           delivery_min=Config.DELIVERY_PRICE_MIN)

@app.route('/success')
def success():
    return render_template('success.html', app_name=Config.APP_NAME, app_phone=Config.APP_PHONE, app_whatsapp=Config.APP_WHATSAPP)

@app.route('/orders-history')
def orders_history():
    if not is_mobile(): return redirect('/')
    return render_template('orders_history.html', app_name=Config.APP_NAME, app_whatsapp=Config.APP_WHATSAPP)

@app.route('/contact')
def contact():
    return render_template('contact.html', app_name=Config.APP_NAME, app_phone=Config.APP_PHONE, app_whatsapp=Config.APP_WHATSAPP)

@app.route('/account')
def account():
    if not is_mobile(): return redirect('/')
    return render_template('account.html', app_name=Config.APP_NAME, app_phone=Config.APP_PHONE)


# ==========================================
# لوحة التحكم (إدارة المتجر)
# ==========================================

@app.route('/admin')
@admin_required
def admin():
    return render_template('dashboard.html', orders=get_orders(), stats=get_daily_stats(), app_name=Config.APP_NAME)

@app.route('/admin/products')
@admin_required
def admin_products():
    return render_template('admin_products.html',
                           categories=get_categories(visible_only=False),
                           subcategories=get_subcategories(visible_only=False),
                           products=get_products(visible_only=False),
                           app_name=Config.APP_NAME)

@app.route('/admin/accounting')
@admin_required
def admin_accounting():
    return render_template('accounting.html', stats=get_daily_stats(), orders=get_orders(), app_name=Config.APP_NAME)

@app.route('/admin/customers')
@admin_required
def admin_customers():
    return render_template('customers.html', customers=get_customers(), app_name=Config.APP_NAME)


# ==========================================
# API — الطلبات (المنطق المطور)
# ==========================================

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'products': []})
    results = execute_query(
        """SELECT p.id, p.name, p.price, p.image, p.unit, c.name as cat_name, p.category_id
           FROM products p
           LEFT JOIN categories c ON c.id = p.category_id
           WHERE p.visible=1 AND p.name LIKE ?
           LIMIT 30""",
        (f'%{q}%',), fetchall=True
    ) or []
    for p in results:
        p['sell_price'] = get_selling_price(p['price'])
    return jsonify({'products': results})


@app.route('/api/order', methods=['POST'])
@rate_limit(max_calls=10, window=60)
def place_order():
    data = request.json
    phone = data.get('phone')
    total = data.get('total')

    # منع تكرار الطلب (خلال 5 ثوانٍ لنفس الزبون والمبلغ)
    now = time.time()
    check_key = f"{phone}_{total}"
    if check_key in last_orders_check and (now - last_orders_check[check_key] < 5):
        return jsonify({'success': False, 'message': 'الطلب قيد المعالجة'})
    last_orders_check[check_key] = now

    data['delivery'] = calculate_delivery_fee(data.get('lat'), data.get('lng'))
    data['profit'] = get_order_profit(data.get('items', []))

    order_display_id = add_order(data)

    order_data_for_notify = data.copy()
    order_data_for_notify['id'] = order_display_id
    try:
        notify_new_order(order_data_for_notify)
    except Exception as e:
        app.logger.error(f"Telegram Error: {e}")

    return jsonify({'success': True, 'order_id': order_display_id})

@app.route('/api/order/<int:order_id>/status', methods=['POST'])
def update_status(order_id):
    status = request.json.get('status')
    update_order_status(order_id, status)
    try:
        notify_order_status(order_id, status)
    except Exception as e:
        app.logger.error(f"Status Update Notify Error: {e}")
    return jsonify({'success': True})

@app.route('/api/order-status/<phone>')
def get_latest_order_status(phone):
    orders = get_orders(phone=phone)
    if orders:
        return jsonify({'id': orders[0]['id'], 'status': orders[0]['status'], 'status_text': orders[0]['status_text']})
    return jsonify({'status': 'none'})

@app.route('/api/orders/by-phone', methods=['POST'])
def api_orders_by_phone():
    phone = request.json.get('phone')
    orders = get_orders(phone=phone)
    return jsonify({'orders': orders})


# ==========================================
# API — الإدارة الكاملة (Categories & Products)
# ==========================================

@app.route('/api/category', methods=['POST'])
def api_add_category():
    name  = request.form.get('name')
    icon  = request.form.get('icon', '🛒')
    image = save_upload(request.files.get('image'), 'cat')
    add_category(name, icon, image)
    return jsonify({'success': True})

@app.route('/api/category/<int:cat_id>', methods=['POST'])
def api_update_category(cat_id):
    name  = request.form.get('name')
    icon  = request.form.get('icon', '🛒')
    image = save_upload(request.files.get('image'), 'cat')
    update_category(cat_id, name, icon, image)
    return jsonify({'success': True})

@app.route('/api/category/<int:cat_id>/toggle', methods=['POST'])
def api_toggle_category(cat_id):
    toggle_category(cat_id)
    return jsonify({'success': True})

@app.route('/api/category/<int:cat_id>/delete', methods=['POST'])
def api_delete_category(cat_id):
    delete_category(cat_id)
    return jsonify({'success': True})

@app.route('/api/subcategory', methods=['POST'])
def api_add_subcategory():
    name = request.form.get('name')
    icon = request.form.get('icon', '📦')
    category_id = int(request.form.get('category_id', 1))
    image = save_upload(request.files.get('image'), 'sub')
    add_subcategory(name, icon, category_id, image)
    return jsonify({'success': True})

@app.route('/api/subcategory/<int:sub_id>', methods=['POST'])
def api_update_subcategory(sub_id):
    name = request.form.get('name')
    icon = request.form.get('icon', '📦')
    category_id = int(request.form.get('category_id', 1))
    image = save_upload(request.files.get('image'), 'sub')
    update_subcategory(sub_id, name, icon, category_id, image)
    return jsonify({'success': True})

@app.route('/api/subcategory/<int:sub_id>/toggle', methods=['POST'])
def api_toggle_subcategory(sub_id):
    toggle_subcategory(sub_id)
    return jsonify({'success': True})

@app.route('/api/subcategory/<int:sub_id>/delete', methods=['POST'])
def api_delete_subcategory(sub_id):
    delete_subcategory(sub_id)
    return jsonify({'success': True})

@app.route('/api/product', methods=['POST'])
def api_add_product():
    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    unit = request.form.get('unit', 'حبة')
    category_id = int(request.form.get('category_id', 1))
    subcategory_id = request.form.get('subcategory_id')
    subcategory_id = int(subcategory_id) if subcategory_id else None
    image = save_upload(request.files.get('image'), 'prod')
    add_product(name, price, unit, category_id, subcategory_id, image)
    return jsonify({'success': True})

@app.route('/api/product/<int:prod_id>', methods=['POST'])
def api_update_product(prod_id):
    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    unit = request.form.get('unit', 'حبة')
    category_id = int(request.form.get('category_id', 1))
    subcategory_id = request.form.get('subcategory_id')
    subcategory_id = int(subcategory_id) if subcategory_id else None
    image = save_upload(request.files.get('image'), 'prod')
    update_product(prod_id, name, price, unit, category_id, subcategory_id, image)
    return jsonify({'success': True})

@app.route('/api/product/<int:prod_id>/toggle', methods=['POST'])
def api_toggle_product(prod_id):
    toggle_product(prod_id)
    return jsonify({'success': True})

@app.route('/api/product/<int:prod_id>/delete', methods=['POST'])
def api_delete_product(prod_id):
    delete_product(prod_id)
    return jsonify({'success': True})

@app.route('/api/admin/clear-products', methods=['POST'])
def api_clear_products():
    """مسح كافة المنتجات من السيرفر"""
    from database import clear_all_products
    clear_all_products()
    return jsonify({'success': True})

@app.route('/api/admin/products/delete-bulk', methods=['POST'])
def api_delete_bulk_products():
    """مسح منتجات محددة دفعة واحدة"""
    ids = request.json.get('ids', [])
    for prod_id in ids:
        delete_product(int(prod_id))
    return jsonify({'success': True, 'deleted': len(ids)})

@app.route('/api/admin/products/move-bulk', methods=['POST'])
@admin_required
def api_move_bulk_products():
    data = request.json
    ids = data.get('ids', [])
    sub_id = data.get('sub_id')
    if not ids or not sub_id:
        return jsonify({'success': False, 'error': 'البيانات المرسلة ناقصة'})
    sub = execute_query('SELECT category_id FROM subcategories WHERE id=?', (sub_id,), fetchone=True)
    if not sub:
        return jsonify({'success': False, 'error': 'القسم الفرعي المختار غير موجود'})
    cat_id = sub['category_id']
    placeholders = ', '.join(['?'] * len(ids))
    execute_query(
        f'UPDATE products SET subcategory_id = ?, category_id = ? WHERE id IN ({placeholders})',
        [sub_id, cat_id] + ids, commit=True
    )
    return jsonify({'success': True})


@app.route('/api/subcategories-by-cat/<int:cat_id>')
def api_subs_by_cat(cat_id):
    subs = get_subcategories(category_id=cat_id, visible_only=False)
    return jsonify(subs)

@app.route('/api/customer/delete', methods=['POST'])
def api_delete_customer():
    phone = request.json.get('phone')
    if phone: delete_customer(phone)
    return jsonify({'success': True})

@app.route('/api/stats')
def api_get_stats():
    return jsonify(get_daily_stats())

@app.route('/api/get-customer/<phone>')
def api_get_customer(phone):
    from database import execute_query
    clean_phone = phone.strip()
    customer = execute_query(
        'SELECT name, phone, whatsapp, neighborhood, address, lat, lng FROM customers WHERE phone=?',
        (clean_phone,), fetchone=True
    )
    if customer:
        return jsonify({'success': True, 'customer': customer})
    else:
        return jsonify({'success': False, 'message': 'الرقم غير مسجل مسبقاً'})


# ==========================================
# API — جلب صورة منتج من Unsplash
# ==========================================

@app.route('/api/admin/fetch-image/<int:prod_id>', methods=['POST'])
def api_fetch_product_image(prod_id):
    import requests as req

    UNSPLASH_KEY = os.environ.get('UNSPLASH_KEY', '')
    if not UNSPLASH_KEY:
        return jsonify({'success': False, 'error': 'مفتاح Unsplash غير موجود في الإعدادات'})

    # ← جديد: اقرأ image_search من قاعدة البيانات
    product = execute_query('SELECT id, name, image_search FROM products WHERE id=?', (prod_id,), fetchone=True)
    if not product:
        return jsonify({'success': False, 'error': 'المنتج غير موجود'})

    product_name = product['name']
    # ← جديد: استخدم image_search إن وُجد، وإلا ترجم تلقائياً
    search_term = product.get('image_search') or translate_to_english(product_name)

    try:
        resp = req.get(
            'https://api.unsplash.com/search/photos',
            params={
                'query': search_term,
                'per_page': 1,
                'orientation': 'squarish'
            },
            headers={'Authorization': f'Client-ID {UNSPLASH_KEY}'},
            timeout=10
        )

        if resp.status_code != 200:
            return jsonify({'success': False, 'error': f'خطأ من Unsplash: {resp.status_code}'})

        results = resp.json().get('results', [])
        if not results:
            return jsonify({'success': False, 'error': f'لم يتم العثور على صورة لـ "{search_term}"'})

        image_url = results[0]['urls']['small']

        img_resp = req.get(image_url, timeout=10)
        if img_resp.status_code != 200:
            return jsonify({'success': False, 'error': 'فشل تحميل الصورة'})

        filename = f"auto_{os.urandom(6).hex()}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'wb') as f:
            f.write(img_resp.content)

        image_path = f"/static/uploads/{filename}"
        execute_query('UPDATE products SET image=? WHERE id=?', (image_path, prod_id), commit=True)

        return jsonify({'success': True, 'image': image_path, 'searched_for': search_term})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==========================================
# معالجة الصور و PWA
# ==========================================

def save_upload(file, prefix='img'):
    if not file or file.filename == '': return None
    ext = file.filename.rsplit('.', 1)[-1].lower()
    filename = f"{prefix}_{os.urandom(6).hex()}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return f"/static/uploads/{filename}"

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/service-worker.js')
def service_worker():
    from flask import Response
    with open('static/service-worker.js') as f:
        content = f.read()
    return Response(content, mimetype='application/javascript')


# ==========================================
# API — استيراد Excel
# ==========================================

@app.route('/api/admin/import-excel', methods=['POST'])
def api_import_excel():
    import threading

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'لم يتم إرسال أي ملف'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'لم يتم اختيار ملف'})

    allowed = {'xlsx', 'xls'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return jsonify({'success': False, 'error': 'صيغة الملف غير مدعومة. يُرجى رفع ملف Excel بصيغة .xlsx أو .xls'})

    temp_path = os.path.join('static', 'uploads', f'excel_import_{os.urandom(4).hex()}.{ext}')
    file.save(temp_path)

    # شغّل الاستيراد في الخلفية لتجنب Timeout على Render
    def _do_import():
        try:
            import_excel_to_db(temp_path)
        except Exception as e:
            app.logger.error(f'Import error: {e}')
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    threading.Thread(target=_do_import, daemon=True).start()

    return jsonify({
        'success': True,
        'created': 0,
        'updated': 0,
        'errors': 0,
        'images': 0,
        'message': '⏳ جاري الاستيراد في الخلفية، انتظر 30 ثانية ثم حدّث الصفحة'
    })


# ==========================================
# تسجيل دخول الأدمن
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
@rate_limit(max_calls=5, window=60)
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == app.config.get('ADMIN_PASSWORD', 'dokkani-admin-2024'):
            session.permanent = True
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            error = 'كلمة السر غلط، حاول مرة أخرى'
    return render_template('admin_login.html', error=error, app_name=Config.APP_NAME)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


# ==========================================
# صفحة الفاتورة الرقمية
# ==========================================

@app.route('/invoice/<int:order_id>')
def invoice(order_id):
    order = execute_query('SELECT * FROM orders WHERE id=?', (order_id,), fetchone=True)
    if not order:
        return redirect('/')
    import json
    if isinstance(order.get('items'), str):
        try:
            order['items'] = json.loads(order['items'])
        except:
            order['items'] = []
    # أضف سعر البيع لكل منتج
    for item in order['items']:
        price = float(item.get('price', 0))
        item['sell_price'] = get_selling_price(price)
    return render_template('invoice.html',
        order=order,
        app_whatsapp=Config.APP_WHATSAPP,
        app_phone=Config.APP_PHONE
    )


# ==========================================
# صفحة مراجعة الصور
# ==========================================

@app.route('/admin/image-review')
@admin_required
def image_review_page():
    cat_filter = request.args.get('cat', '')
    sub_filter = request.args.get('sub', '')
    page = int(request.args.get('page', 1))
    per_page = 30
    offset = (page - 1) * per_page

    where_clause = """WHERE (p.image_status IS NULL OR p.image_status < 2)
        AND (p.image IS NULL OR p.image = '' OR p.image = 'None')"""
    params = []
    if cat_filter:
        where_clause += " AND p.category_id = ?"
        params.append(cat_filter)
    if sub_filter:
        where_clause += " AND p.subcategory_id = ?"
        params.append(sub_filter)

    prods = execute_query(f'''
        SELECT p.*, c.name as cat_name FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        {where_clause}
        ORDER BY p.id LIMIT ? OFFSET ?''', params + [per_page, offset], fetchall=True)

    total_res = execute_query(f"SELECT COUNT(*) as n FROM products p {where_clause}", params, fetchone=True)
    cats = execute_query('SELECT id, name FROM categories ORDER BY sort, id', fetchall=True)
    subs = execute_query('SELECT id, name FROM subcategories WHERE category_id = ? ORDER BY id', (cat_filter,), fetchall=True) if cat_filter else []
    total_no_img = total_res['n'] if total_res else 0

    return render_template('image_review.html',
        products=prods or [],
        categories=cats or [],
        subcategories=subs or [],
        cat_filter=cat_filter,
        sub_filter=sub_filter,
        page=page,
        per_page=per_page,
        total=total_no_img,
        app_name=Config.APP_NAME)

@app.route('/api/admin/confirm-image', methods=['POST'])
@admin_required
def confirm_image():
    data = request.json
    prod_id = data.get('prod_id')
    image_url = data.get('image_url')
    if not image_url:
        return jsonify({'success': False, 'error': 'الرابط فارغ'})
    execute_query('UPDATE products SET image=?, image_status=2 WHERE id=?', (image_url, prod_id), commit=True)
    return jsonify({'success': True})

# ==========================================
# AI Assistant — مساعد الذكاء الاصطناعي (النسخة الموحدة والمحصنة)
# ==========================================

@app.route('/admin/ai-assistant')
@admin_required
def ai_assistant_page():
    return render_template('admin_ai.html', app_name=Config.APP_NAME)

@app.route('/api/admin/ai-chat', methods=['POST'])
@admin_required
def ai_chat():
    import requests as req
    import json as _json
    import re

    OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
    if not OPENAI_KEY:
        return jsonify({'success': False, 'error': 'مفتاح OpenAI مفقود'})

    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({'success': False, 'error': 'الرسالة فارغة'})

    def safe_execute(sql):
        """تنفيذ SQL مع جلب النتائج دائماً (تعديل المدير)"""
        try:
            sql = sql.strip().rstrip(';')
            forbidden = ['DROP ', 'TRUNCATE ', 'ALTER TABLE', 'GRANT ', 'CREATE ']
            if any(w in sql.upper() for w in forbidden):
                return None, 'أمر محظور أمنياً'

            is_write = any(k in sql.upper() for k in ['UPDATE ', 'DELETE ', 'INSERT '])
            
            # تنفيذ التعديل أو القراءة مع fetchall دائماً لضمان استقرار الفهرس
            res = execute_query(sql, commit=is_write, fetchall=True) or []
            
            if is_write:
                return {'status': 'success', 'message': 'تم التنفيذ بنجاح'}, None
            return {'data': res}, None
        except Exception as e:
            return None, str(e)

    def generate_sql_safe(messages):
        """توليد SQL مع تنظيف JSON (تعديل المدير)"""
        try:
            r = req.post('https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'},
                json={
                    'model': 'gpt-4o-mini',
                    'messages': messages,
                    'response_format': {'type': 'json_object'},
                    'max_tokens': 400, 'temperature': 0
                }, timeout=30)
            if r.status_code != 200: return None
            
            raw_content = r.json()['choices'][0]['message']['content']
            # تنظيف الـ JSON قبل التحليل (تعديل المدير)
            clean_raw = raw_content.strip().replace('\n', ' ').replace('\r', ' ')
            try:
                return _json.loads(clean_raw).get('sql', '').strip()
            except:
                # محاولة Regex إذا فشل JSON (تعديل المدير)
                match = re.search(r'"sql"\s*:\s*"(.*?)"(?:\s*})', clean_raw, re.DOTALL)
                return match.group(1).replace('\\"', '"').strip() if match else ''
        except: return None

    db_schema = """جداول PostgreSQL: 
    - products(id, name, price, unit, category_id, subcategory_id, image, visible)
    - categories(id, name)
    - subcategories(id, name, category_id)
    قواعد: استخدم ILIKE للبحث، استخدم visible = 1، استخدم string_agg للجمع."""

    try:
        # 1. المحاولة الأولى
        system_prompt = f"أنت خبير SQL. {db_schema}. رد بـ JSON فقط: {{\"sql\": \"SELECT ...\"}}"
        msgs = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_message}]
        
        sql_to_run = generate_sql_safe(msgs)
        if not sql_to_run:
            return jsonify({'success': False, 'error': 'فشل توليد الاستعلام'})

        result, error = safe_execute(sql_to_run)

        # 2. نظام المحاولات (Retry) في حال وجود خطأ تقني
        if error:
            msgs.append({'role': 'assistant', 'content': _json.dumps({'sql': sql_to_run})})
            msgs.append({'role': 'user', 'content': f'الاستعلام أعطى خطأ: "{error}". صححه فوراً.'})
            sql_to_run = generate_sql_safe(msgs)
            if sql_to_run:
                result, error = safe_execute(sql_to_run)

        # 3. التحقق النهائي من وجود نتيجة قبل صياغة الإجابة
        if error or result is None:
            return jsonify({'success': False, 'error': f'تعذر التنفيذ: {error}'})

        # 4. صياغة الإجابة النهائية للمدير
        r2 = req.post('https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': f"سؤال: {user_message}\nالنتائج: {_json.dumps(result, ensure_ascii=False, default=str)[:3000]}\nأجب بالعربية بدقة."}]
            }, timeout=30)
        
        if r2.status_code != 200:
            return jsonify({'success': False, 'error': 'فشل OpenAI في صياغة الإجابة'})

        final_answer = r2.json()['choices'][0]['message']['content']
        return jsonify({'success': True, 'answer': final_answer, 'sql': sql_to_run})

    except Exception as e:
        # المسار الأخير لضمان عدم عودة None أبداً
        return jsonify({'success': False, 'error': f'خطأ غير متوقع: {str(e)}'})

# ==========================================
# تشغيل السيرفر (نهاية الملف)
# ==========================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')