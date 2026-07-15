import sys
import subprocess

# ==============================================================================
# 3- تحميل Telethon تلقائيا (فحص وتثبيت المكتبة)
# ==============================================================================
try:
    from telethon import TelegramClient, events, functions, types
    from telethon.errors import FloodWaitError, MessageIdInvalidError, MessageNotModifiedError
    from telethon.errors import PhoneNumberInvalidError, PhoneCodeInvalidError, PhoneCodeExpiredError, SessionPasswordNeededError
except ImportError:
    print("Telethon not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "telethon"])
    from telethon import TelegramClient, events, functions, types
    from telethon.errors import FloodWaitError, MessageIdInvalidError, MessageNotModifiedError
    from telethon.errors import PhoneNumberInvalidError, PhoneCodeInvalidError, PhoneCodeExpiredError, SessionPasswordNeededError

import asyncio
import os
import re
import random
import time
from datetime import datetime, timedelta

# محاولة استيراد مكتبة psutil لحساب الرام، وإذا لم توجد لا يتوقف السورس
try:
    import psutil
except ImportError:
    psutil = None

# ==============================================================================
#                      معلومات تسجيل الدخول (ثابتة داخل السورس)
# ==============================================================================
API_ID = 38917658
API_HASH = '6d506223f15fe28547533c262ce5abd1'
SOURCE_NAME = "Vergil"
START_TIME = time.time()

# ==============================================================================
#                      توكن بوت تسجيل الدخول
# ==============================================================================
BOT_TOKEN = "8866116828:AAF02rWQqS7sKO3BJVp_zc2yhad6YHOxHfU"

# ==============================================================================
#                      سترنك الجلسة (Session String)
# ==============================================================================
SESSION_STRING = "1ApWapzMBuxi9MYbulA_vWMQFykoJwgUgnEibl33vYe4Aj__14F7Ap7lp0quNCGdW1nMokuMwSNTa4XNsZitdMZ8wYDQvqBxE5w_m76MS7N38ScpwXw4OCYm6XtxufXhHaYutdNwbjoP7-wDExmayayWI5XZh_e5UJ4VhhdahwAcypOhz3MM54F2Maqdmay3bNqb7J2H88d9dFx2aLGmruQOs-4P5iYH4NNwjuMrLRV-WQm42TpPrE9z2Y9GiO9BKR-FPAhjdxJKfBTaqyNFS8YG6VsaU2vLHj_hwwAf3GGf1VecLEuRuDMhX8xYM1EvvGu5rwoccXhNQhawrtlQE1A4He_jfCA4="

# ==============================================================================
#                      متغيرات نظام تسجيل الدخول عبر البوت
# ==============================================================================
AUTH_STATES = {}
AUTH_BOT_RUNNING = False
MAIN_CLIENT_STARTED = False
ENGINES_STARTED = False

# ==============================================================================
#                      تخزن البيانات في الذاكرة (RAM ONLY)
# ==============================================================================
SHARED_VOCAB = []
VOCAB_MODE = "تسلسل" 
CURRENT_VOCAB_INDEX = 0

CHATS_CONFIG = {}
MONITOR_WATCH_LIST = {} 
FAKE_TYPING_STATUS = {} 
GLOBAL_STALK_LIST = set() 
SELECTED_CUSTOM_MSGS = {} 

# لتخزين المهام وحالات الإيقاف العام
SCHEDULED_TASKS = {} 
REPEATING_TASKS = {} 
FROZEN_STATES = {}

# ==============================================================================
#                             دوال المساعدة والمنطق
# ==============================================================================

def get_settings(chat_id):
    if chat_id not in CHATS_CONFIG:
        CHATS_CONFIG[chat_id] = {
            "targets": set(),
            "target_last_msg_id": {},
            "spam_speed": 1.0,
            "is_spamming": False,
            "is_human_typing": False,
            "transfer_on": False,
            "transfer_mode": "normal", 
            "transfer_msgs": [],
            "transfer_interval": 2.0,
            "last_transfer_time": 0,
            "auto_reply_on": False,
            "auto_reply_targets": set(),
            "auto_reply_speed": 3,
            "mute_list": set(),
            "auto_delete_on": False,
            "auto_delete_mins": 60,
            "space_symbol": "",
            "monitor": {
                "disappear_targets": set(),
                "mute": False,
                "delete": False,
                "restrict": False,
                "mass_delete": False
            },
            "scheduled_msg": None,
            "scheduled_interval": 1,
            "repeating_on": False,
            "repeating_count": 0
        }
    return CHATS_CONFIG[chat_id]

def clean_text(text):
    chars_to_remove = ['[', ']', '"', "'", ',']
    for char in chars_to_remove:
        text = text.replace(char, "")
    return text.strip()

def apply_source_spaces(text, chat_id):
    config = get_settings(chat_id)
    symbol = config["space_symbol"]
    if symbol and " " in text:
        return text.replace(" ", symbol)
    return text

async def edit_delete_action(event, text):
    """تقوم بتعديل الرسالة ثم حذفها بعد ثانية واحدة - مع معالجة الأخطاء لضمان الاستقرار"""
    try:
        await event.edit(text)
    except (MessageNotModifiedError, Exception):
        pass
    await asyncio.sleep(1)
    try:
        await event.delete()
    except:
        pass

# ==============================================================================
#                     نظام تسجيل الدخول عبر البوت (باستخدام Session String)
# ==============================================================================

# العميل الرئيسي - مع إعدادات إعادة الاتصال التلقائي باستخدام Session String
client = TelegramClient(None, API_ID, API_HASH, connection_retries=None, retry_delay=5, auto_reconnect=True)

# إنشاء بوت Telethon منفصل للتعامل مع المصادقة
bot_client = TelegramClient('auth_bot_session', API_ID, API_HASH)

async def check_session_valid():
    """التحقق من صحة Session String"""
    try:
        await client.start(session_string=SESSION_STRING)
        me = await client.get_me()
        if me:
            return True
    except:
        return False
    return False

async def start_engines():
    """تشغيل المحركات الخلفية مرة واحدة فقط"""
    global ENGINES_STARTED
    if not ENGINES_STARTED:
        ENGINES_STARTED = True
        asyncio.create_task(transfer_engine())
        asyncio.create_task(auto_delete_engine())
        asyncio.create_task(monitor_disappear_engine())
        asyncio.create_task(fake_status_engine())

async def handle_auth_bot():
    """تشغيل بوت المصادقة"""
    global AUTH_BOT_RUNNING, MAIN_CLIENT_STARTED
    AUTH_BOT_RUNNING = True
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_auth(event):
        user_id = event.sender_id
        AUTH_STATES[user_id] = {"step": "phone", "phone": None, "code": "", "password": None}
        await event.reply("🔐 مرحباً بك في نظام تسجيل الدخول.\n\nالرجاء إرسال رقم هاتفك مع رمز الدولة.\nمثال: `+9647712345678`")

    @bot_client.on(events.NewMessage)
    async def auth_step_handler(event):
        user_id = event.sender_id
        text = event.raw_text.strip()
        
        if user_id not in AUTH_STATES:
            await event.reply("❌ الرجاء إرسال /start لبدء عملية تسجيل الدخول.")
            return
        
        state = AUTH_STATES[user_id]
        
        # الخطوة 1: استقبال رقم الهاتف
        if state["step"] == "phone":
            try:
                await client.send_code_request(text)
                state["phone"] = text
                state["step"] = "code"
                state["code"] = ""
                await event.reply("✅ تم إرسال رمز التحقق إلى رقمك.\n\nالرجاء إرسال الرمز المكون من 5 أرقام (مثال: 8 8 8 8 8 أو 88888)\nيمكنك إرسال كل رقم على حدة وسيتم جمعها تلقائياً.")
            except PhoneNumberInvalidError:
                await event.reply("❌ رقم الهاتف غير صحيح. الرجاء المحاولة مرة أخرى.\nمثال: `+9647712345678`")
            except FloodWaitError as e:
                await event.reply(f"⏳ انتظر {e.seconds} ثانية قبل المحاولة مرة أخرى.")
            except Exception as e:
                await event.reply(f"❌ حدث خطأ: {str(e)}")
            return
        
        # الخطوة 2: استقبال رمز التحقق
        if state["step"] == "code":
            # إزالة المسافات وجمع الأرقام
            digits = ''.join(filter(str.isdigit, text))
            if digits:
                state["code"] += digits
            
            # التحقق من اكتمال الرمز
            if len(state["code"]) >= 5:
                code = state["code"][:5]
                try:
                    await client.sign_in(state["phone"], code)
                    
                    me = await client.get_me()
                    # حفظ Session String بعد نجاح تسجيل الدخول
                    session_string = client.session.save()
                    await event.reply(f"✅ تم تسجيل الدخول بنجاح!\n\n👤 الاسم: {me.first_name} {me.last_name or ''}\n🆔 المعرف: @{me.username or 'لا يوجد'}\n📱 الرقم: {me.phone}\n\n📁 تم إنشاء الجلسة بنجاح.\n🚀 بدء تشغيل السورس...")
                    
                    del AUTH_STATES[user_id]
                    AUTH_BOT_RUNNING = False
                    MAIN_CLIENT_STARTED = True
                    await bot_client.disconnect()
                    
                    # تحديث Session String في الكود
                    global SESSION_STRING
                    SESSION_STRING = session_string
                    
                    # بدء تشغيل السورس الرئيسي
                    await start_main_client()
                    
                except PhoneCodeInvalidError:
                    state["code"] = ""
                    await event.reply("❌ رمز التحقق غير صحيح. الرجاء المحاولة مرة أخرى.\nأرسل الرمز المكون من 5 أرقام.")
                except PhoneCodeExpiredError:
                    await event.reply("❌ انتهت صلاحية الرمز. الرجاء إعادة إرسال /start للمحاولة مرة أخرى.")
                    del AUTH_STATES[user_id]
                except SessionPasswordNeededError:
                    state["step"] = "password"
                    await event.reply("🔐 حسابك محمي بكلمة مرور التحقق بخطوتين.\nالرجاء إرسال كلمة المرور.")
                except FloodWaitError as e:
                    await event.reply(f"⏳ انتظر {e.seconds} ثانية قبل المحاولة مرة أخرى.")
                except Exception as e:
                    await event.reply(f"❌ حدث خطأ: {str(e)}")
            else:
                remaining = 5 - len(state["code"])
                await event.reply(f"📥 تم استقبال {len(state['code'])} أرقام. أرسل {remaining} أرقام أخرى لإكمال الرمز.")
            return
        
        # الخطوة 3: استقبال كلمة مرور التحقق بخطوتين
        if state["step"] == "password":
            try:
                await client.sign_in(password=text)
                
                me = await client.get_me()
                # حفظ Session String بعد نجاح تسجيل الدخول
                session_string = client.session.save()
                await event.reply(f"✅ تم تسجيل الدخول بنجاح!\n\n👤 الاسم: {me.first_name} {me.last_name or ''}\n🆔 المعرف: @{me.username or 'لا يوجد'}\n📱 الرقم: {me.phone}\n\n📁 تم إنشاء الجلسة بنجاح.\n🚀 بدء تشغيل السورس...")
                
                del AUTH_STATES[user_id]
                AUTH_BOT_RUNNING = False
                MAIN_CLIENT_STARTED = True
                await bot_client.disconnect()
                
                # تحديث Session String في الكود
                global SESSION_STRING
                SESSION_STRING = session_string
                
                await start_main_client()
                
            except Exception as e:
                await event.reply(f"❌ كلمة المرور غير صحيحة. الرجاء المحاولة مرة أخرى.\nالخطأ: {str(e)}")

    # تشغيل البوت
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ بوت المصادقة يعمل... أرسل /start للبدء.")
    await bot_client.run_until_disconnected()

async def start_main_client():
    """بدء تشغيل العميل الرئيسي مع جميع الوظائف"""
    global MAIN_CLIENT_STARTED
    try:
        # استخدام Session String لتسجيل الدخول
        await client.start(session_string=SESSION_STRING)
        
        me = await client.get_me()
        if not me:
            print("❌ فشل التحقق من الجلسة. الرجاء المحاولة مرة أخرى.")
            MAIN_CLIENT_STARTED = False
            return
        
        MAIN_CLIENT_STARTED = True
        print(f"--- Project {SOURCE_NAME} is Starting ---")
        print(f"✅ تم تسجيل الدخول باسم: {me.first_name} {me.last_name or ''}")
        
        # تشغيل المحركات الخلفية
        await start_engines()
        
        # حلقة إعادة الاتصال التلقائي - كما في السورس الأصلي
        while True:
            try:
                await client.run_until_disconnected()
            except Exception as e:
                print(f"Connection lost or Error occurred: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
                # محاولة إعادة الاتصال باستخدام Session String
                try:
                    await client.start(session_string=SESSION_STRING)
                except:
                    pass
        
    except Exception as e:
        print(f"❌ خطأ في العميل الرئيسي: {e}")
        MAIN_CLIENT_STARTED = False
        await asyncio.sleep(5)

# ==============================================================================
#                             تشغيل العميل (Client)
# ==============================================================================

# ==============================================================================
# 1- تحمل تعديل الرسائل (تحديث تتبع الرسائل عند الإرسال أو التعديل)
# ==============================================================================

@client.on(events.NewMessage(incoming=True))
@client.on(events.MessageEdited(incoming=True))
async def track_target_messages(event):
    try:
        chat_id = event.chat_id
        config = get_settings(chat_id)
        if event.sender_id in config["targets"]:
            config["target_last_msg_id"][event.sender_id] = event.id
    except Exception:
        pass

# ==============================================================================
#                            أنظمة قوائم الأوامر
# ==============================================================================

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.الاوامر$'))
async def show_main_menu(event):
    menu = (
        "ــــــــــــــــــــــــــــــــــــــــــــــــــــــــ\n"
        "Welcome to Source Vergil\n"
        "ــــــــــــــــــــــــــــــــــــــــــــــــــــــــ\n"
        "`.1` اوامر الارسال\n"
        "`.2` اوامر التحويل\n"
        "`.3` اوامر الرد التلقائي\n"
        "`.4` اوامر الكتم\n"
        "`.5` اوامر المفردات\n"
        "`.6` اوامر الحذف\n"
        "`.7` اوامر المراقبة\n"
        "`.8` اوامر الوهمي\n"
        "`.9` اوامر المسافات\n"
        "`.10` اوامر الجدولة\n"
    )
    try:
        await event.edit(menu)
    except Exception:
        pass

@client.on(events.NewMessage(outgoing=True))
async def handle_sub_menus(event):
    cmd = event.text
    chat_id = event.chat_id
    
    if cmd.startswith(".وهمي كتابه"):
        try:
            parts = cmd.split()
            if len(parts) == 3:
                mins = int(parts[2])
                FAKE_TYPING_STATUS[chat_id] = time.time() + (mins * 60)
                await edit_delete_action(event, f"تم تفعيل الوهمي كتابه لمدة {mins} دقيقة")
            else:
                FAKE_TYPING_STATUS[chat_id] = time.time() + 999999
                await edit_delete_action(event, "تم تفعيل الوهمي كتابه المستمر")
        except:
            await edit_delete_action(event, "خطأ: يرجى كتابة الأمر بشكل صحيح")

    elif cmd == ".تعطيل الوهمي":
        if chat_id in FAKE_TYPING_STATUS:
            FAKE_TYPING_STATUS.pop(chat_id)
        await edit_delete_action(event, "تم تعطيل الكتابة الوهمية")

    if cmd == ".1":
        await event.edit(
            "~ اوامر الارسال ~\n\n"
            "`.ذا الدثو` (رد على شخص)\n"
            "`.دعبل` (إلغاء شخص)\n"
            "`.يلا دي` (إلغاء الكل)\n"
            "`.بنيكك` (تفعيل الارسال)\n"
            "`.تنيك` (تسطير بشري)\n"
            "`.خلاص` (إيقاف الكل)\n"
            "`.الوقت` [رقم] (ضبط السرعة)"
        )
    elif cmd == ".2":
        await event.edit(
            "~ اوامر التحويل ~\n\n"
            "`.cec` لتعشيل التحويل\n"
            "`.ect` تشغيل تحويل الرسائل المحددة\n"
            "`.offcec` لإيقاف التحويل\n"
            "`.T` + عدد الرسائل من الرسائل المحفوظة\n"
            "`.R` + وقت الانتظار (أقل قيمة 0.1)\n"
            "`.this` حفظ الرسالة الحالية للتحويل"
        )
    elif cmd == ".3":
        await event.edit(
            "~ اوامر الرد التلقائي ~\n\n"
            "لتشغيل الرد = `.تشغيل` \n"
            "لايقاف الرد = `.إيقاف` \n"
            "للتحديد = `.ذا الفريخون` \n"
            "لتفعيل الملاحقة = `.لاحق الفريخون` \n"
            "لتعيين سرعة الرد = `.السرعه` + العدد\n"
            "لإزالة شخص محدد = `.ازالة` "
        )
    elif cmd == ".4":
        await event.edit(
            "~ اوامر الكتم ~\n\n"
            "`.ك` كتم في الخاص وحذف رسائله مباشرة\n"
            "`.ف` فك الكتم في الخاص\n"
            "`.كتم` كتم الشخص في المجموعة\n"
            "`.فك` فك كتم المجموعة\n"
            "`.مم` حذف جميع رسائل الطرف المقابل في الخاص"
        )
    elif cmd == ".5":
        await event.edit(
            "~ اوامر المفردات ~\n\n"
            "لتعيين مفردات معينة للارسال و الرد التلقائي\n"
            "ارسل ملف ثم رد على الملف بـ\n"
            "`.تخزين` \n"
            "`.الغاء التخزين` \n"
            "بعد تعيين ملف الكلمات يجب عليك اختيار:\n"
            "`.تسلسل` \n"
            "`.عشوائي` "
        )
    elif cmd == ".6":
        await event.edit(
            "~ اوامر الحذف ~\n\n"
            "`.تفعيل الحذف` تشغيل حذف الرسائل التلقائي\n"
            "`.تعطيل الحذف` إيقاف الحذف\n"
            "`.وقت الحذف` بالدقائق فقط\n"
            "`.رس` حذف جميع رسائلي في الشات الحالي"
        )
    elif cmd == ".7":
        await event.edit(
            "~ اوامر المراقبة ~\n\n"
            "`.راقبمه` مراقبة اختفاء الشخص (بالرد)\n"
            "`.راقب الكتم` مراقبة الكتم\n"
            "`.راقب الحذف` مراقبة حذف الرسائل\n"
            "`.راقب حذفه` مراقبة تصفير الشات\n"
            "`.راقب عام` تفعيل جميع أنواع المراقبة\n"
            "`.تعطيل راقب` تعطيل جميع المراقبة نهائياً"
        )
    elif cmd == ".8":
        await event.edit(
            "~ اوامر الوهمي ~\n\n"
            "لتفعيل وهمي كتابه طوال الوقت = `.وهمي كتابه` \n"
            "لتفعيل وهمي كتابه لمدة معينة = `.وهمي كتابه` + العدد بالدقائق\n"
            "`.تعطيل الوهمي` لإيقاف الكتابة الوهمية"
        )
    elif cmd == ".9":
        await event.edit(
            "~ اوامر المسافات ~\n\n"
            "لـ اختيار مسافة = `.اختر` + رقم المسافة\n"
            "1 ~ | 2 × | 3 - | 4 * | 5 = \n"
            "6 \\ | 7 / | 8 _ | 9 • | 10 +\n\n"
            "لاعادة الكتابة بدون مسافات = `.اعادة`"
        )
    elif cmd == ".10":
        await event.edit(
            "~ اوامر الجدولة ~\n\n"
            "`.للجدولة` = لتحديد الرسالة المراد جدولتها\n"
            "`.جدول` + العدد = جدولة الرسالة بالعدد لمرة واحدة\n"
            "`.كرر جدول` + العدد = سبام جدولة\n"
            "`.وقت الجدولة` + العدد = لتعيين وقت الجدولة لمرة واحدة\n\n"
            "`.إلغاء جدول` = لتعطيل الجدولة\n"
            "`.عطل جدول` = لتعطيل الجدولة"
        )

# ==============================================================================
#                             نظام المفردات (.5)
# ==============================================================================

@client.on(events.NewMessage(outgoing=True))
async def vocab_handler(event):
    global SHARED_VOCAB, VOCAB_MODE
    text = event.text
    
    if text == ".تخزين" and event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg.media and reply_msg.file:
            path = await reply_msg.download_media()
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                SHARED_VOCAB = [clean_text(line) for line in lines if line.strip()]
                os.remove(path)
                await edit_delete_action(event, f"تم تخزين {len(SHARED_VOCAB)} سطر بنجاح")
            except:
                await edit_delete_action(event, "حدث خطأ في قراءة الملف")
            
    elif text == ".الغاء التخزين":
        count = len(SHARED_VOCAB)
        SHARED_VOCAB = []
        await edit_delete_action(event, f"تم إلغاء تخزين {count} سطر بنجاح")
        
    elif text == ".تسلسل":
        VOCAB_MODE = "تسلسل"
        await edit_delete_action(event, "تم اختيار النمط: تسلسل")
        
    elif text == ".عشوائي":
        VOCAB_MODE = "عشوائي"
        await edit_delete_action(event, "تم اختيار النمط: عشوائي")

# ==============================================================================
#                             أولا: محرك الإرسال المطور (.1)
# ==============================================================================

async def get_oldest_msg(chat_id, user_id):
    config = get_settings(chat_id)
    last_id = config["target_last_msg_id"].get(user_id)
    
    if last_id:
        try:
            m = await client.get_messages(chat_id, ids=last_id)
            if m and not m.action: return last_id
        except: pass

    async for msg in client.iter_messages(chat_id, from_user=user_id, limit=1):
        config["target_last_msg_id"][user_id] = msg.id
        return msg.id
    return None

@client.on(events.NewMessage(outgoing=True))
async def sender_logic(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text

    if text == ".ذا الدثو" and event.is_reply:
        reply = await event.get_reply_message()
        config["targets"].add(reply.sender_id)
        config["target_last_msg_id"][reply.sender_id] = reply.id
        await edit_delete_action(event, "تم تحديد الشخص بنجاح")
        
    elif text == ".دعبل" and event.is_reply:
        reply = await event.get_reply_message()
        config["targets"].discard(reply.sender_id)
        config["target_last_msg_id"].pop(reply.sender_id, None)
        await edit_delete_action(event, "تم إلغاء الشخص")
        
    elif text == ".يلا دي":
        config["targets"].clear()
        config["target_last_msg_id"].clear()
        await edit_delete_action(event, "تم إلغاء الكل")
        
    elif text.startswith(".الوقت "):
        try:
            val = float(text.split()[1])
            config["spam_speed"] = max(0.1, val)
            await edit_delete_action(event, f"تم ضبط السرعة إلى {config['spam_speed']}")
        except: pass

    elif text == ".بنيكك":
        if not SHARED_VOCAB: 
            return await edit_delete_action(event, "خطأ: ملف المفردات فارغ")
        config["is_spamming"] = True
        config["is_human_typing"] = False
        await edit_delete_action(event, "تم تفعيل الارسال")
        asyncio.create_task(run_spam_engine(chat_id))

    elif text == ".تنيك":
        if not SHARED_VOCAB: 
            return await edit_delete_action(event, "خطأ: ملف المفردات فارغ")
        config["is_human_typing"] = True
        config["is_spamming"] = False
        await edit_delete_action(event, "تم تفعيل التسطير البشري")
        asyncio.create_task(run_spam_engine(chat_id, is_human=True))

    elif text == ".خلاص":
        config["is_spamming"] = False
        config["is_human_typing"] = False
        await edit_delete_action(event, "تم إيقاف الارسال والتسطير")

async def run_spam_engine(chat_id, is_human=False):
    global CURRENT_VOCAB_INDEX
    config = get_settings(chat_id)
    
    while (config["is_spamming"] if not is_human else config["is_human_typing"]):
        if not config["targets"] or not SHARED_VOCAB: break
        
        for target_id in list(config["targets"]):
            try:
                reply_id = await get_oldest_msg(chat_id, target_id)
                if not reply_id: continue

                if VOCAB_MODE == "عشوائي":
                    word = random.choice(SHARED_VOCAB)
                else:
                    word = SHARED_VOCAB[CURRENT_VOCAB_INDEX % len(SHARED_VOCAB)]
                    CURRENT_VOCAB_INDEX += 1
                
                word = apply_source_spaces(word, chat_id)
                
                if is_human:
                    async with client.action(chat_id, 'typing'):
                        delay = (len(word) * 0.05) + random.uniform(0.5, 1.0)
                        await asyncio.sleep(delay)
                
                await client.send_message(chat_id, word, reply_to=reply_id)
                await asyncio.sleep(config["spam_speed"])

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except MessageIdInvalidError:
                config["target_last_msg_id"].pop(target_id, None)
                await asyncio.sleep(0.1)
            except: 
                await asyncio.sleep(0.5)
            
        if is_human: await asyncio.sleep(random.uniform(0.5, 1))

# ==============================================================================
#                             نظام التحويل المصلح (.2)
# ==============================================================================

@client.on(events.NewMessage(outgoing=True))
async def transfer_manager(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text
    
    if text == ".cec":
        config["transfer_on"] = True
        config["transfer_mode"] = "normal"
        await edit_delete_action(event, "تم تشغيل التحويل")
    elif text == ".ect":
        config["transfer_on"] = True
        config["transfer_mode"] = "custom"
        await edit_delete_action(event, "تم تشغيل تحويل الرسائل المحددة")
    elif text == ".offcec":
        config["transfer_on"] = False
        await edit_delete_action(event, "تم إيقاف التحويل")
    elif text.startswith(".T "):
        try:
            count = int(text.split()[1])
            config["transfer_msgs"] = []
            async for m in client.iter_messages('me', limit=count):
                config["transfer_msgs"].append(m)
            await edit_delete_action(event, f"تم جلب {len(config['transfer_msgs'])} رسائل")
        except: pass
    elif text.startswith(".R "):
        try:
            val = float(text.split()[1])
            config["transfer_interval"] = max(0.1, val)
            await edit_delete_action(event, f"تم ضبط وقت التحويل إلى: {config['transfer_interval']}")
        except: pass
    elif text == ".this" and event.is_reply:
        if chat_id not in SELECTED_CUSTOM_MSGS: 
            SELECTED_CUSTOM_MSGS[chat_id] = []
        reply = await event.get_reply_message()
        SELECTED_CUSTOM_MSGS[chat_id].append(reply)
        await edit_delete_action(event, "تم حفظ الرسالة للتحويل المخصص")

async def transfer_engine():
    while True:
        try:
            for chat_id, config in list(CHATS_CONFIG.items()):
                if config["transfer_on"]:
                    if time.time() - config["last_transfer_time"] >= config["transfer_interval"]:
                        msgs = []
                        if config["transfer_mode"] == "normal": msgs = config["transfer_msgs"]
                        elif config["transfer_mode"] == "custom": msgs = SELECTED_CUSTOM_MSGS.get(chat_id, [])
                        
                        if msgs:
                            clean_batch = [m for m in msgs if not (m.text and "تنبيه مراقبة" in m.text)]
                            if clean_batch:
                                await client.forward_messages(chat_id, clean_batch)
                                config["last_transfer_time"] = time.time()
            await asyncio.sleep(0.1)
        except: await asyncio.sleep(1)

# ==============================================================================
#                            نظام الرد التلقائي (.3)
# ==============================================================================

@client.on(events.NewMessage(outgoing=False))
async def auto_reply_listener(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    is_target = False
    if event.sender_id in GLOBAL_STALK_LIST: is_target = True
    elif config["auto_reply_on"] and event.sender_id in config["auto_reply_targets"]: is_target = True
    if is_target:
        try:
            await asyncio.sleep(config["auto_reply_speed"])
            if SHARED_VOCAB:
                word = random.choice(SHARED_VOCAB)
                word = apply_source_spaces(word, chat_id)
                await event.reply(word)
        except: pass

@client.on(events.NewMessage(outgoing=True))
async def auto_reply_cmds(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text
    if text == ".تشغيل":
        config["auto_reply_on"] = True
        await edit_delete_action(event, "تم تشغيل الرد التلقائي بنجاح")
    elif text == ".إيقاف":
        config["auto_reply_on"] = False
        await edit_delete_action(event, "تم إيقاف الرد التلقائي بنجاح")
    elif text == ".ذا الفريخون" and event.is_reply:
        reply = await event.get_reply_message()
        config["auto_reply_targets"].add(reply.sender_id)
        await edit_delete_action(event, "تم تحديد الشخص للرد")
    elif text == ".لاحق الفريخون" and event.is_reply:
        reply = await event.get_reply_message()
        GLOBAL_STALK_LIST.add(reply.sender_id)
        await edit_delete_action(event, "تم تفعيل الملاحقة العالمية")
    elif text.startswith(".السرعه "):
        try:
            config["auto_reply_speed"] = int(text.split()[1])
            await edit_delete_action(event, f"سرعة الرد: {config['auto_reply_speed']}")
        except: pass
    elif text == ".ازالة" and event.is_reply:
        reply = await event.get_reply_message()
        config["auto_reply_targets"].discard(reply.sender_id)
        GLOBAL_STALK_LIST.discard(reply.sender_id)
        await edit_delete_action(event, "تمت إزالة الشخص")

# ==============================================================================
#                            نظام المسافات (.9)
# ==============================================================================

@client.on(events.NewMessage(outgoing=True))
async def spaces_logic(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text
    symbols_map = {"1": " ~ ", "2": " × ", "3": " - ", "4": " * ", "5": " = ", "6": " \\ ", "7": " / ", "8": " _ ", "9": " • ", "10": " + "}
    if text.startswith(".اختر "):
        try:
            num = text.split()[1]
            if num in symbols_map:
                config["space_symbol"] = symbols_map[num]
                await edit_delete_action(event, f"تم تفعيل المسافة رقم {num}")
        except: pass
    elif text == ".اعادة":
        config["space_symbol"] = ""
        await edit_delete_action(event, "تم إرجاع الكتابة طبيعية")

# ==============================================================================
#                            نظام الكتم (.4)
# ==============================================================================

@client.on(events.NewMessage(outgoing=False))
async def mute_watcher(event):
    config = get_settings(event.chat_id)
    if event.sender_id in config["mute_list"]:
        try: await event.delete()
        except: pass

@client.on(events.NewMessage(outgoing=True))
async def mute_commands(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text
    if text == ".ك" and event.is_reply:
        reply = await event.get_reply_message()
        config["mute_list"].add(reply.sender_id)
        await edit_delete_action(event, "تم الكتم وحذف الرسائل")
    elif text == ".ف" and event.is_reply:
        reply = await event.get_reply_message()
        config["mute_list"].discard(reply.sender_id)
        await edit_delete_action(event, "تم فك الكتم")
    elif text == ".كتم" and event.is_reply:
        reply = await event.get_reply_message()
        config["mute_list"].add(reply.sender_id)
        await edit_delete_action(event, "تم كتم الشخص بنجاح")
    elif text == ".فك" and event.is_reply:
        reply = await event.get_reply_message()
        config["mute_list"].discard(reply.sender_id)
        await edit_delete_action(event, "تم فك الكتم")
    elif text == ".مم" and event.is_private:
        async for m in client.iter_messages(chat_id, from_user=chat_id):
            await m.delete()
        await edit_delete_action(event, "تم حذف رسائل الطرف الآخر")

# ==============================================================================
#                            نظام الحذف (.6)
# ==============================================================================

@client.on(events.NewMessage(outgoing=True))
async def delete_logic(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text
    if text == ".تفعيل الحذف":
        config["auto_delete_on"] = True
        await edit_delete_action(event, "تم تفعيل الحذف التلقائي")
    elif text == ".تعطيل الحذف":
        config["auto_delete_on"] = False
        await edit_delete_action(event, "تم تعطيل الحذف التلقائي")
    elif text.startswith(".وقت الحذف "):
        try:
            parts = text.split()
            if len(parts) >= 3:
                config["auto_delete_mins"] = int(parts[2])
                await edit_delete_action(event, f"تم ضبط وقت الحذف إلى: {config['auto_delete_mins']} دقيقة")
        except: pass
    elif text == ".رس":
        async for m in client.iter_messages(chat_id, from_user='me'):
            await m.delete()

async def auto_delete_engine():
    while True:
        try:
            for chat_id, config in list(CHATS_CONFIG.items()):
                if config["auto_delete_on"]:
                    threshold = datetime.now() - timedelta(minutes=config["auto_delete_mins"])
                    async for msg in client.iter_messages(chat_id, offset_date=threshold):
                        try: await msg.delete()
                        except: pass
            await asyncio.sleep(30)
        except: await asyncio.sleep(5)

# ==============================================================================
#                            نظام المراقبة (.7)
# ==============================================================================

@client.on(events.NewMessage(outgoing=False))
async def monitor_tracker(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    if event.sender_id in config["monitor"]["disappear_targets"]:
        MONITOR_WATCH_LIST[event.sender_id] = {"time": time.time(), "chat": chat_id, "msg": event.id}

@client.on(events.ChatAction)
async def monitor_actions(event):
    try:
        me = await client.get_me()
        if event.user_id == me.id:
            config = get_settings(event.chat_id)
            if (config["monitor"]["mute"] and event.muted) or (config["monitor"]["restrict"] and (event.user_joined or event.user_left)):
                await client.send_message('me', f"تنبيه مراقبة: تم تغيير صلاحياتك في الشات {event.chat_id}")
    except: pass

@client.on(events.MessageDeleted)
async def monitor_deletions(event):
    chat_id = event.chat_id
    if not chat_id: return
    config = get_settings(chat_id)
    if config["monitor"]["mass_delete"] and len(event.deleted_ids) >= 15:
        await client.send_message('me', f"تنبيه مراقبة: تم تصفير الشات الايدي: {chat_id}")
    elif config["monitor"]["delete"]:
        await client.send_message('me', f"تنبيه مراقبة: تم حذف رسائل في الشات {chat_id}")

@client.on(events.NewMessage(outgoing=True))
async def monitor_commands(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text
    if text == ".راقبمه" and event.is_reply:
        reply = await event.get_reply_message()
        config["monitor"]["disappear_targets"].add(reply.sender_id)
        await edit_delete_action(event, "تمت إضافة الشخص لمراقبة الاختفاء")
    elif text == ".راقب الكتم":
        config["monitor"]["mute"] = True
        await edit_delete_action(event, "مراقبة الكتم: مفعل")
    elif text == ".راقب الحذف":
        config["monitor"]["delete"] = True
        await edit_delete_action(event, "مراقبة الحذف: مفعل")
    elif text == ".راقب حذفه":
        config["monitor"]["mass_delete"] = True
        await edit_delete_action(event, "مراقبة تصفير الشات: مفعل")
    elif text == ".راقب عام":
        config["monitor"]["mute"] = True
        config["monitor"]["delete"] = True
        config["monitor"]["mass_delete"] = True
        config["monitor"]["restrict"] = True
        await edit_delete_action(event, "المراقبة العامة: مفعل")
    elif text == ".تعطيل راقب":
        for cid in list(CHATS_CONFIG.keys()):
            CHATS_CONFIG[cid]["monitor"]["disappear_targets"].clear()
            CHATS_CONFIG[cid]["monitor"]["mute"] = False
            CHATS_CONFIG[cid]["monitor"]["delete"] = False
            CHATS_CONFIG[cid]["monitor"]["mass_delete"] = False
            CHATS_CONFIG[cid]["monitor"]["restrict"] = False
        await edit_delete_action(event, "تم تعطيل المراقبة")

async def monitor_disappear_engine():
    while True:
        try:
            now = time.time()
            for user_id, data in list(MONITOR_WATCH_LIST.items()):
                if now - data["time"] > 180:
                    chat_id_str = str(data['chat'])
                    msg_link = f"https://t.me/c/{chat_id_str[4:]}/{data['msg']}" if chat_id_str.startswith('-100') else "شات خاص"
                    await client.send_message('me', f"تنبيه مراقبة: اختفاء الملحود {user_id}\nالرابط: {msg_link}")
                    if user_id in MONITOR_WATCH_LIST: del MONITOR_WATCH_LIST[user_id]
            await asyncio.sleep(30)
        except: await asyncio.sleep(5)

# ==============================================================================
#                            نظام الوهمي (.8)
# ==============================================================================

async def fake_status_engine():
    while True:
        try:
            now = time.time()
            for cid, end_time in list(FAKE_TYPING_STATUS.items()):
                if now < end_time:
                    try:
                        async with client.action(cid, 'typing'):
                            await asyncio.sleep(4)
                    except:
                        pass
                else:
                    FAKE_TYPING_STATUS.pop(cid, None)
            await asyncio.sleep(1)
        except: await asyncio.sleep(5)

# ==============================================================================
#                            نظام الإيقاف العام (.ايقاف عام)
# ==============================================================================

@client.on(events.NewMessage(outgoing=True))
async def global_freeze_handler(event):
    text = event.text
    if text == ".ايقاف عام":
        for chat_id, config in CHATS_CONFIG.items():
            FROZEN_STATES[chat_id] = {
                "is_spamming": config["is_spamming"],
                "is_human_typing": config["is_human_typing"],
                "transfer_on": config["transfer_on"],
                "auto_reply_on": config["auto_reply_on"],
                "auto_delete_on": config["auto_delete_on"],
                "repeating_on": config["repeating_on"],
                "fake_typing": (chat_id in FAKE_TYPING_STATUS)
            }
            config["is_spamming"] = False
            config["is_human_typing"] = False
            config["transfer_on"] = False
            config["auto_reply_on"] = False
            config["auto_delete_on"] = False
            config["repeating_on"] = False
            if chat_id in FAKE_TYPING_STATUS: FAKE_TYPING_STATUS.pop(chat_id)
            if chat_id in REPEATING_TASKS: REPEATING_TASKS[chat_id].cancel()
            if chat_id in SCHEDULED_TASKS: SCHEDULED_TASKS[chat_id].cancel()
        await edit_delete_action(event, "تم تجميد جميع المحركات بنجاح")

    elif text == ".اعادة تشغيل":
        for chat_id, state in FROZEN_STATES.items():
            config = get_settings(chat_id)
            if state["is_spamming"]:
                config["is_spamming"] = True
                asyncio.create_task(run_spam_engine(chat_id))
            if state["is_human_typing"]:
                config["is_human_typing"] = True
                asyncio.create_task(run_spam_engine(chat_id, True))
            if state["transfer_on"]: config["transfer_on"] = True
            if state["auto_reply_on"]: config["auto_reply_on"] = True
            if state["auto_delete_on"]: config["auto_delete_on"] = True
            if state["fake_typing"]: FAKE_TYPING_STATUS[chat_id] = time.time() + 999999
            if state["repeating_on"]:
                config["repeating_on"] = True
                async def rep_engine(cid, cnt):
                    while get_settings(cid)["repeating_on"]:
                        target_t = datetime.utcnow() + timedelta(minutes=1)
                        for _ in range(cnt): 
                            await client.send_message(cid, get_settings(cid)["scheduled_msg"], schedule=target_t)
                        await asyncio.sleep(60)
                REPEATING_TASKS[chat_id] = asyncio.create_task(rep_engine(chat_id, config["repeating_count"]))
        FROZEN_STATES.clear()
        await edit_delete_action(event, "تمت استعادة المحركات التي كانت تعمل")

# ==============================================================================
#                            نظام الفحص المطور (.فحص)
# ==============================================================================

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.فحص$'))
async def status_check(event):
    me = await client.get_me()
    name = f"{me.first_name} {me.last_name or ''}".strip()
    uptime_sec = int(time.time() - START_TIME)
    d = uptime_sec // 86400
    h = (uptime_sec % 86400) // 3600
    m = (uptime_sec % 3600) // 60
    uptime_str = f"{d}D {h}H {m}M"
    start_p = time.time()
    await event.edit("...")
    ping = round((time.time() - start_p) * 1000)
    
    if psutil:
        ram = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    else:
        ram = "غير متوفر"

    active_c, targets_c, working = 0, 0, "متوقف"
    for cid, cfg in CHATS_CONFIG.items():
        targets_c += len(cfg["targets"])
        if any([cfg["is_spamming"], cfg["is_human_typing"], cfg["transfer_on"], cfg["auto_reply_on"], cfg["repeating_on"]]):
            active_c += 1
            working = "يعمل"
    
    msg = (
        "━━━━━━━━━━━━━━━━━━\n"
        "Vergil Status\n\n"
        f"● حالة السورس : {working}\n"
        f"● الاسم : {name}\n"
        f"● مدة التشغيل : {uptime_str}\n"
        f"● Ping : {ping}\n"
        f"● RAM : {ram}\n"
        f"● المفردات : {len(SHARED_VOCAB)}\n"
        f"● الكروبات : {active_c}\n"
        f"● الأشخاص المحددون : {targets_c}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "`.ايقاف عام` \n"
        "`.اعادة تشغيل` "
    )
    await event.edit(msg)

# ==============================================================================
#                            نظام الجدولة الرسمي (.10)
# ==============================================================================

@client.on(events.NewMessage(outgoing=True))
async def schedule_manager(event):
    chat_id = event.chat_id
    config = get_settings(chat_id)
    text = event.text
    if text == ".للجدولة" and event.is_reply:
        config["scheduled_msg"] = await event.get_reply_message()
        await edit_delete_action(event, "تم حفظ الرسالة للجدولة")
    elif text.startswith(".جدول "):
        if not config["scheduled_msg"]: return await edit_delete_action(event, "خطأ")
        try:
            count = int(text.split()[1])
            target_time = datetime.utcnow() + timedelta(minutes=config["scheduled_interval"])
            for _ in range(count): 
                await client.send_message(chat_id, config["scheduled_msg"], schedule=target_time)
            await edit_delete_action(event, "تمت الجدولة بنظام تيليجرام الرسمي")
        except: pass
    elif text.startswith(".كرر جدول "):
        if not config["scheduled_msg"]: return await edit_delete_action(event, "خطأ")
        try:
            config["repeating_count"] = int(text.split()[2])
            config["repeating_on"] = True
            async def repeat():
                while config["repeating_on"]:
                    target_t = datetime.utcnow() + timedelta(minutes=1)
                    for _ in range(config["repeating_count"]): 
                        await client.send_message(chat_id, config["scheduled_msg"], schedule=target_t)
                    await asyncio.sleep(60)
            if chat_id in REPEATING_TASKS: REPEATING_TASKS[chat_id].cancel()
            REPEATING_TASKS[chat_id] = asyncio.create_task(repeat())
            await edit_delete_action(event, "تم تفعيل التكرار بنظام الجدولة الرسمي")
        except: pass
    elif text.startswith(".وقت الجدولة "):
        try:
            config["scheduled_interval"] = int(text.split()[2])
            await edit_delete_action(event, "تم ضبط الوقت")
        except: pass
    elif text == ".إلغاء جدول":
        if chat_id in SCHEDULED_TASKS:
            SCHEDULED_TASKS[chat_id].cancel()
            del SCHEDULED_TASKS[chat_id]
        await edit_delete_action(event, "تم إلغاء المهام، يرجى مسح المجدولة يدوياً")
    elif text == ".عطل جدول":
        config["repeating_on"] = False
        if chat_id in REPEATING_TASKS:
            REPEATING_TASKS[chat_id].cancel()
            del REPEATING_TASKS[chat_id]
        await edit_delete_action(event, "تم تعطيل الجدولة المتكررة")

# ==============================================================================
#             نقطة التشغيل - مع نظام تسجيل الدخول عبر البوت (باستخدام Session String)
# ==============================================================================

async def main():
    """نقطة الدخول الرئيسية - التحقق من Session String أو بدء بوت المصادقة"""
    global MAIN_CLIENT_STARTED
    
    # محاولة استخدام Session String مباشرة
    print("🔍 محاولة تسجيل الدخول باستخدام Session String...")
    try:
        await client.start(session_string=SESSION_STRING)
        me = await client.get_me()
        if me:
            print(f"✅ تم تسجيل الدخول بنجاح باستخدام Session String. مرحباً {me.first_name} {me.last_name or ''}")
            
            MAIN_CLIENT_STARTED = True
            print(f"--- Project {SOURCE_NAME} is Starting ---")
            
            # تشغيل المحركات الخلفية
            await start_engines()
            
            # حلقة إعادة الاتصال التلقائي
            while True:
                try:
                    await client.run_until_disconnected()
                except Exception as e:
                    print(f"Connection lost or Error occurred: {e}. Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
                    try:
                        await client.start(session_string=SESSION_STRING)
                    except:
                        pass
            return
    except Exception as e:
        print(f"⚠️ فشل تسجيل الدخول باستخدام Session String: {e}")
        print("🔄 بدء عملية تسجيل الدخول عبر البوت...")
    
    # تشغيل بوت المصادقة
    await handle_auth_bot()

async def start_main_client():
    """بدء تشغيل العميل الرئيسي بعد نجاح المصادقة"""
    global MAIN_CLIENT_STARTED
    try:
        MAIN_CLIENT_STARTED = True
        print(f"--- Project {SOURCE_NAME} is Starting ---")
        
        # تشغيل المحركات الخلفية
        await start_engines()
        
        # حلقة إعادة الاتصال التلقائي
        while True:
            try:
                await client.run_until_disconnected()
            except Exception as e:
                print(f"Connection lost or Error occurred: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
                try:
                    await client.start(session_string=SESSION_STRING)
                except:
                    pass
        
    except Exception as e:
        print(f"❌ خطأ في العميل الرئيسي: {e}")
        MAIN_CLIENT_STARTED = False
        await asyncio.sleep(5)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف السورس")
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
