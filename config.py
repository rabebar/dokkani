# ==========================================
# config.py — إعدادات تطبيق دكّاني
# ==========================================

import os

class Config:
    SECRET_KEY = 'dokkani-secret-2024'
    DEBUG = True

    # معلومات التطبيق
    APP_NAME = 'دكّاني'
    APP_PHONE = '0592776784'
    APP_WHATSAPP = '970592776784'
    APP_CITY = 'رام الله'

    # إعدادات التوصيل
    DELIVERY_PRICE_SHORT = 5    # 0-2 كم
    DELIVERY_PRICE_MID   = 8    # 2-5 كم
    DELIVERY_PRICE_FAR   = 12   # +5 كم

    # هامش الربح — بقالة
    PROFIT_LOW  = 0.5   # 1–8 ₪
    PROFIT_MID  = 1.0   # 9–19 ₪
    PROFIT_HIGH = 1.5   # 20+ ₪

    # هامش الربح — كيلو
    PROFIT_KG_VEG  = 1.0   # خضار/كيلو
    PROFIT_KG_MEAT = 2.0   # لحمة/كيلو

    # VIP
    VIP_THRESHOLD = 3   # عدد الطلبات للحصول على VIP

    # تنبيهات التيليجرام
    TELEGRAM_TOKEN   = '8301447744:AAGWbUlyEg_vYkWt9kvZKmKizTjl9ZvTuTM'
    TELEGRAM_CHAT_ID = '1921205945'

    # قاعدة البيانات (للرفع على Render مستقبلاً)
    _db_url = os.environ.get('DATABASE_URL', '')
    DATABASE_URL = _db_url.replace('postgres://', 'postgresql://', 1) if _db_url else None