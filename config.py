# ==========================================
# config.py — إعدادات تطبيق دكّاني (آمنة)
# ==========================================

import os
import secrets

class Config:
    # ← مهم: SECRET_KEY من environment variable، مش hardcoded
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # ==========================================
    # إعدادات أمان الجلسة (Session Security)
    # ==========================================
    # تحقق إذا كنا في بيئة إنتاج (HTTPS) أو تطوير (localhost)
    _is_production = os.environ.get('DYNO') is not None or os.environ.get('RENDER') is not None
    
    SESSION_COOKIE_SECURE = _is_production  # True في الإنتاج (HTTPS)، False في التطوير
    SESSION_COOKIE_HTTPONLY = True     # منع JavaScript من الوصول للكوكيز
    SESSION_COOKIE_SAMESITE = 'Lax'    # حماية من هجمات CSRF
    
    # إعدادات إضافية للأمان
    PERMANENT_SESSION_LIFETIME = 604800  # 7 أيام بالثواني

    # معلومات التطبيق
    APP_NAME = 'دكّاني'
    APP_PHONE = os.environ.get('APP_PHONE', '0592776784')
    APP_WHATSAPP = os.environ.get('APP_WHATSAPP', '970592776784')
    APP_CITY = 'رام الله'

    # كلمة سر الأدمن ← من environment variable
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

    # إعدادات التوصيل المحدثة
    DELIVERY_PRICE_MIN   = 10  # الحد الأدنى الجديد
    DELIVERY_PRICE_MAX   = 25  # الحد الأقصى الجديد
    DELIVERY_PER_KM     = 2.5 # تكلفة الكيلومتر المحدثة

    # هامش الربح — بقالة
    PROFIT_LOW  = 1.0
    PROFIT_MID  = 1.5
    PROFIT_HIGH = 2.0

    # هامش الربح — كيلو
    PROFIT_KG_VEG  = 1.0
    PROFIT_KG_MEAT = 2.0

    # VIP
    VIP_THRESHOLD = 3

    # تنبيهات التيليجرام ← من environment variable دائماً
    TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

    # قاعدة البيانات
    _db_url = os.environ.get('DATABASE_URL', '')
    DATABASE_URL = _db_url.replace('postgres://', 'postgresql://', 1) if _db_url else None
