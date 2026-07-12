# ==========================================
# telegram_notify.py — تنبيهات التيليجرام
# ==========================================

import requests
import os
from config import Config

ALERT_SOUND = os.path.join('static', 'alert.mp3')


def normalize_whatsapp_phone(raw, default_country='970'):
    phone = ''.join(ch for ch in str(raw or '') if ch.isdigit())
    if phone.startswith('00'):
        phone = phone[2:]
    if phone.startswith('970') or phone.startswith('972'):
        return phone
    if phone.startswith('0'):
        return default_country + phone[1:]
    if phone:
        return default_country + phone
    return ''


def send_telegram(message):
    """إرسال رسالة نصية"""
    try:
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            'chat_id':    Config.TELEGRAM_CHAT_ID,
            'text':       message,
            'parse_mode': 'HTML'
        }, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")


def send_alert_sound():
    try:
        import random
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendAudio"
        name = f"dokkani_{random.randint(1000,9999)}.mp3"
        with open(ALERT_SOUND, 'rb') as f:
            requests.post(url, data={
                'chat_id':   Config.TELEGRAM_CHAT_ID,
                'title':     '🔔 طلب جديد',
                'performer': 'دكّاني',
            }, files={
                'audio': (name, f, 'audio/mpeg')
            }, timeout=10)
    except Exception as e:
        print(f"Sound error: {e}")


def notify_new_order(order):
    """تنبيه طلب جديد — صوت + رسالة"""
    items = order.get('items', [])

    # قائمة المنتجات مع الباركود
    items_text = ''
    for item in items:
        barcode_str = f" 🔢[{item.get('barcode')}]" if item.get('barcode') else ""
        items_text += f"  • {item.get('name')} × {item.get('qty')} — {item.get('price')}₪{barcode_str}\n"

    def money(value):
        try:
            return f"{float(value):.1f}"
        except (TypeError, ValueError):
            return "0.0"

    # رابط واتساب
    phone = normalize_whatsapp_phone(order.get('whatsapp') or order.get('phone'))
    wa_link  = f"https://wa.me/{phone}" if phone else ''

    # رابط الخريطة
    lat = order.get('lat')
    lng = order.get('lng')
    map_link = f"https://www.google.com/maps?q={lat},{lng}" if lat and lng else ''

    # طريقة الدفع
    pay = '💵 كاش' if order.get('payment') == 'cash' else '📱 Reflect'

    message = (
        f"🛒 <b>طلب جديد! #{order.get('id','—')}</b>\n"
        f"{'─' * 25}\n"
        f"👤 <b>{order.get('name')}</b>\n"
        f"📞 {order.get('phone')}\n"
        f"📍 {order.get('neighborhood')} — {order.get('address')}\n"
        f"{'─' * 25}\n"
        f"🛍️ <b>المنتجات:</b>\n{items_text}"
        f"{'─' * 25}\n"
        f"💰 المنتجات: <b>{money(order.get('total'))}₪</b>\n"
        f"🚗 التوصيل: {money(order.get('delivery'))}₪\n"
        f"✅ الإجمالي النهائي: <b>{money(order.get('final_total') or ((order.get('total') or 0) + (order.get('delivery') or 0)))}₪</b>\n"
        f"{pay}\n"
        f"💚 ربح المنتجات: <b>{order.get('profit')}₪</b>\n"
    )

    if order.get('notes'):
        message += f"📝 <b>ملاحظات:</b> {order.get('notes')}\n"

    message += f"{'─' * 25}\n"

    if wa_link:
        message += f"💬 <a href='{wa_link}'>واتساب الزبون</a>   "
    if map_link:
        message += f"🗺️ <a href='{map_link}'>موقع الزبون</a>"

    # أرسل الصوت أولاً ثم الرسالة
    send_alert_sound()
    send_telegram(message)


def notify_order_status(order_id, status):
    """تنبيه تغيير حالة الطلب"""
    status_map = {
        'prep':       '⏳ جاري التحضير',
        'delivering': '🚗 المندوب في الطريق',
        'done':       '✅ تم التوصيل بنجاح',
        'cancelled':  '❌ تم إلغاء الطلب',
    }
    text = status_map.get(status)
    if text:
        send_telegram(f"{text}\nرقم الطلب: <b>#{order_id}</b>")
