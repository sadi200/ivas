import os
import re
import json
import time
import uuid
import shutil
import requests
import threading
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

# ================= Configuration =================
BOT_TOKEN = "8867778383:AAEGVqNMr0GMrPcghX8DmBGkbpJXJPaObwU"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILE_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}/"

OWNER_IDS = [903018274, 6921432566]
WITHDRAW_GROUP_ID = -5377908906

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
DB_FILE = os.path.join(CURRENT_DIR, "bot_data.json")
USERS_FILE = os.path.join(CURRENT_DIR, "users_db.json")

BACKUP_DIR = os.path.join(CURRENT_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

file_lock = threading.Lock()
BD_TZ = timezone(timedelta(hours=6))

spam_tracker = {}
spam_lock = threading.Lock()
low_stock_notified = set()

# ================= Premium Custom Emojis =================
PEM = {
    "ok": '<tg-emoji emoji-id="5352694861990501856">✅</tg-emoji>',
    "no": '<tg-emoji emoji-id="6267000941547885720">❌</tg-emoji>',
    "warn": '<tg-emoji emoji-id="5336944168944047463">⚠️</tg-emoji>',
    "admin": '<tg-emoji emoji-id="5353032893096567467">📊</tg-emoji>',
    "user": '<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji>',
    "money": '<tg-emoji emoji-id="5348469219761626211">💸</tg-emoji>',
    "gift": '<tg-emoji emoji-id="5420396762189831222">🎁</tg-emoji>',
    "msg": '<tg-emoji emoji-id="5337302974806922068">💬</tg-emoji>',
    "gear": '<tg-emoji emoji-id="5420155432272438703">⚙️</tg-emoji>',
    "link": '<tg-emoji emoji-id="5420517437885943844">🔗</tg-emoji>',
    "trash": '<tg-emoji emoji-id="5422557736330106570">🗑</tg-emoji>',
    "upload": '<tg-emoji emoji-id="5353001161878182134">📤</tg-emoji>',
    "world": '<tg-emoji emoji-id="5336972142066047577">🌐</tg-emoji>',
    "lock": '<tg-emoji emoji-id="5353022963132174959">🔐</tg-emoji>',
    "phone": '<tg-emoji emoji-id="5337132498965010628">📱</tg-emoji>',
    "num": '<tg-emoji emoji-id="5352862640592949843">🔢</tg-emoji>',
    "pin": '<tg-emoji emoji-id="5352922460897452503">📍</tg-emoji>',
    "star": '<tg-emoji emoji-id="5352552689983067014">✨</tg-emoji>',
    "hi": '<tg-emoji emoji-id="5353027129250453493">👋</tg-emoji>',
    "cal": '<tg-emoji emoji-id="5352585194295564660">📅</tg-emoji>',
    "bank": '<tg-emoji emoji-id="5190899075968441286">💳</tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5352597830089347330">🚀</tg-emoji>',
    "headset": '<tg-emoji emoji-id="5336850036145823599">🎧</tg-emoji>'
}

db = {
    "admins": OWNER_IDS,
    "banned_users": [],
    "maintenance_mode": False,
    "ranges": {},
    "range_rates": {},
    "range_traffic_otps": {},
    "default_otp_rate": 5.0,
    "min_withdraw": 50.0,
    "num_timeout_minutes": 10,
    "active_sessions": {},
    "assigned_numbers": {},
    "number_ranges": {},
    "withdraw_requests": {},
    "daily_system_earnings": {},
    "user_period_stats": {},
    "last_reset_day": "",
    "settings": {
        "otp_link": "https://t.me/msmethod/116",
        "support_username": "SupportAdmin"
    }
}

user_states = {}
temp_data = {}

def get_bd_now():
    return datetime.now(BD_TZ)

def get_bd_reset_day_str():
    now = get_bd_now()
    if now.hour < 6:
        eff = now - timedelta(days=1)
    else:
        eff = now
    return eff.strftime('%Y-%m-%d')

def is_admin(user_id):
    try:
        u_id = int(str(user_id).strip())
        owner_int_ids = [int(str(x).strip()) for x in OWNER_IDS]
        if u_id in owner_int_ids:
            return True
        db_admins = [int(str(x).strip()) for x in db.get("admins", [])]
        return u_id in db_admins
    except Exception:
        return False

def load_data():
    global db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    db.update(data)
        except Exception:
            bak = f"{DB_FILE}.bak"
            if os.path.exists(bak):
                try:
                    with open(bak, "r", encoding="utf-8") as bf:
                        db.update(json.load(bf))
                except Exception:
                    pass

    owner_int_ids = [int(str(x).strip()) for x in OWNER_IDS]
    if "admins" not in db or not isinstance(db["admins"], list):
        db["admins"] = list(owner_int_ids)
    else:
        for oid in owner_int_ids:
            if oid not in db["admins"]:
                db["admins"].append(oid)

    if "settings" not in db: db["settings"] = {}
    db["settings"]["otp_link"] = "https://t.me/msmethod/116"

    if "daily_system_earnings" not in db: db["daily_system_earnings"] = {}
    if "user_period_stats" not in db: db["user_period_stats"] = {}
    if "range_rates" not in db: db["range_rates"] = {}
    if "range_traffic_otps" not in db: db["range_traffic_otps"] = {}
    if "ranges" not in db: db["ranges"] = {}
    if "assigned_numbers" not in db: db["assigned_numbers"] = {}
    if "number_ranges" not in db: db["number_ranges"] = {}
    if "active_sessions" not in db: db["active_sessions"] = {}
    if "withdraw_requests" not in db: db["withdraw_requests"] = {}
    if "num_timeout_minutes" not in db: db["num_timeout_minutes"] = 10
    if "maintenance_mode" not in db: db["maintenance_mode"] = False

    cur_reset_day = get_bd_reset_day_str()
    if db.get("last_reset_day") != cur_reset_day:
        db["last_reset_day"] = cur_reset_day
        save_data()
        reset_today_stats_for_all_users()

def save_data():
    with file_lock:
        tmp = f"{DB_FILE}.tmp"
        bak = f"{DB_FILE}.bak"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(DB_FILE):
                shutil.copy2(DB_FILE, bak)
            os.replace(tmp, DB_FILE)
        except Exception as e:
            print(f"Error saving bot data: {e}")
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass

def get_all_users_from_file():
    with file_lock:
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            return data
            except Exception:
                pass
            bak = f"{USERS_FILE}.bak"
            if os.path.exists(bak):
                try:
                    with open(bak, "r", encoding="utf-8") as bf:
                        return json.load(bf)
                except Exception:
                    return {}
        return {}

def save_all_users_to_file(users_data):
    if not users_data or not isinstance(users_data, dict):
        return
    with file_lock:
        tmp = f"{USERS_FILE}.tmp"
        bak = f"{USERS_FILE}.bak"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(users_data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(USERS_FILE):
                shutil.copy2(USERS_FILE, bak)
            os.replace(tmp, USERS_FILE)
        except Exception as e:
            print(f"Error writing USERS_FILE: {e}")
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass

def reset_today_stats_for_all_users():
    users = get_all_users_from_file()
    cur_reset_day = get_bd_reset_day_str()
    for uid, dat in users.items():
        dat["today_earnings"] = 0.0
        dat["today_otps"] = 0
        dat["last_active_date"] = cur_reset_day
    save_all_users_to_file(users)

def get_user(uid, username=""):
    uid = str(uid).strip()
    users = get_all_users_from_file()
    cur_reset_day = get_bd_reset_day_str()
    modified = False

    if uid not in users:
        users[uid] = {
            "user_id": uid,
            "username": username or "",
            "balance": 0.0,
            "today_earnings": 0.0,
            "today_otps": 0,
            "total_earnings": 0.0,
            "last_active_date": cur_reset_day,
            "total_otps": 0,
            "referred_by": None,
            "registered_at": time.time()
        }
        modified = True
    else:
        if username and users[uid].get("username") != username:
            users[uid]["username"] = username
            modified = True
        if users[uid].get("last_active_date") != cur_reset_day:
            users[uid]["today_earnings"] = 0.0
            users[uid]["today_otps"] = 0
            users[uid]["last_active_date"] = cur_reset_day
            modified = True

    if modified:
        save_all_users_to_file(users)
    return users[uid]

def update_balance(uid, amount, is_earning=False, is_otp=False):
    uid = str(uid).strip()
    users = get_all_users_from_file()
    cur_reset_day = get_bd_reset_day_str()
    amt = float(amount)

    if uid not in users:
        users[uid] = {
            "user_id": uid,
            "username": "",
            "balance": 0.0,
            "today_earnings": 0.0,
            "today_otps": 0,
            "total_earnings": 0.0,
            "last_active_date": cur_reset_day,
            "total_otps": 0,
            "referred_by": None,
            "registered_at": time.time()
        }

    if users[uid].get("last_active_date") != cur_reset_day:
        users[uid]["today_earnings"] = 0.0
        users[uid]["today_otps"] = 0
        users[uid]["last_active_date"] = cur_reset_day

    users[uid]["balance"] = round(float(users[uid].get("balance", 0.0)) + amt, 2)

    if is_earning and amt > 0:
        users[uid]["today_earnings"] = round(float(users[uid].get("today_earnings", 0.0)) + amt, 2)
        users[uid]["total_earnings"] = round(float(users[uid].get("total_earnings", 0.0)) + amt, 2)

        load_data()
        if cur_reset_day not in db["daily_system_earnings"]:
            db["daily_system_earnings"][cur_reset_day] = {"amount": 0.0, "otps": 0}
        db["daily_system_earnings"][cur_reset_day]["amount"] = round(db["daily_system_earnings"][cur_reset_day]["amount"] + amt, 2)
        if is_otp:
            db["daily_system_earnings"][cur_reset_day]["otps"] += 1

        if "user_period_stats" not in db: db["user_period_stats"] = {}
        if cur_reset_day not in db["user_period_stats"]: db["user_period_stats"][cur_reset_day] = {}
        if uid not in db["user_period_stats"][cur_reset_day]:
            db["user_period_stats"][cur_reset_day][uid] = {"otps": 0, "amount": 0.0}
        db["user_period_stats"][cur_reset_day][uid]["amount"] = round(db["user_period_stats"][cur_reset_day][uid]["amount"] + amt, 2)
        if is_otp:
            db["user_period_stats"][cur_reset_day][uid]["otps"] += 1
        save_data()

    if is_otp:
        users[uid]["today_otps"] = int(users[uid].get("today_otps", 0)) + 1
        users[uid]["total_otps"] = int(users[uid].get("total_otps", 0)) + 1

    save_all_users_to_file(users)
    return users[uid]["balance"]

load_data()

session = requests.Session()

def api_call(method, payload=None):
    url = f"{BASE_URL}/{method}"
    try:
        res = session.post(url, json=payload, timeout=12)
        return res.json()
    except Exception:
        return {}

def send_msg(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("sendMessage", payload)

def edit_msg(chat_id, msg_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("editMessageText", payload)

def delete_msg(chat_id, msg_id):
    return api_call("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})

def send_document(chat_id, file_path, caption=None):
    url = f"{BASE_URL}/sendDocument"
    for _ in range(3):
        try:
            with open(file_path, "rb") as f:
                files = {"document": (os.path.basename(file_path), f)}
                data = {"chat_id": str(chat_id)}
                if caption:
                    data["caption"] = caption
                    data["parse_mode"] = "HTML"
                res = session.post(url, data=data, files=files, timeout=40)
                if res.status_code == 200 and res.json().get("ok"):
                    return res.json()
        except Exception as e:
            print(f"Error sending document: {e}")
            time.sleep(2)
    return {}

# ================= Forced Subscription / Join Verification =================
def check_user_membership(user_id):
    channels = ["@frndotp", "@msmethod"]
    for ch in channels:
        try:
            res = api_call("getChatMember", {"chat_id": ch, "user_id": user_id})
            if res.get("ok"):
                status = res.get("result", {}).get("status")
                if status not in ["member", "administrator", "creator"]:
                    return False
            else:
                return False
        except Exception:
            return False
    return True

def send_verification_prompt(chat_id, msg_id=None):
    text = (
        f"{PEM['warn']} <b>JOIN REQUIRED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🔐 <b>Welcome to our community!</b>\n\n"
        f"Bot ব্যবহার করতে হলে প্রথমে আমাদের দু’টি গ্রুপে Join করতে হবে।\n\n"
        f"📲 <b>Step 1:</b> OTP Group-এ Join করুন\n"
        f"🛠 <b>Step 2:</b> Method Group-এ Join করুন\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ Join করা শেষ হলে নিচের <b>Verify</b> button-এ click করুন."
    )
    kb = {
        "inline_keyboard": [
            [
                {"text": "📲 OTP Group", "url": "https://t.me/frndotp"},
                {"text": "🛠 Method Group", "url": "https://t.me/msmethod"}
            ],
            [
                {"text": "✅ Verify", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "check_join"}
            ]
        ]
    }
    if msg_id:
        edit_msg(chat_id, msg_id, text, reply_markup=kb)
    else:
        send_msg(chat_id, text, reply_markup=kb)

# ================= Anti-Spam Protection =================
def is_spamming(user_id):
    if is_admin(user_id):
        return False
    now = time.time()
    with spam_lock:
        if user_id in spam_tracker:
            info = spam_tracker[user_id]
            if now < info.get("timeout_until", 0):
                return True
            info["timestamps"] = [t for t in info.get("timestamps", []) if now - t < 1.0]
            info["timestamps"].append(now)
            if len(info["timestamps"]) > 5:
                info["timeout_until"] = now + 120
                send_msg(user_id, f"{PEM['warn']} <b>Spam Detected!</b>\nApni ১ second-e ৫ bar-er beshi click korchen. Apnake ২ min-er jonno block kora holo.")
                return True
        else:
            spam_tracker[user_id] = {"timestamps": [now], "timeout_until": 0}
    return False

def check_and_alert_low_stock(range_name, current_stock):
    global low_stock_notified
    if current_stock <= 15:
        if range_name not in low_stock_notified:
            low_stock_notified.add(range_name)
            alert_msg = f"{PEM['warn']} <b>LOW STOCK ALERT!</b>\n\n📌 <b>Range:</b> <code>{range_name}</code>\n🔢 <b>Remaining:</b> <b>{current_stock}</b> ti numbers left.\n<i>Please add more numbers!</i>"
            for adm in db.get("admins", OWNER_IDS):
                send_msg(adm, alert_msg)
    else:
        low_stock_notified.discard(range_name)

# ================= 2 Hours Auto Backup Engine =================
def auto_backup_worker():
    while True:
        time.sleep(2 * 3600)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_files = [("users_db.json", USERS_FILE), ("bot_data.json", DB_FILE)]
        for name, path in target_files:
            if os.path.exists(path):
                try:
                    backup_filename = f"{os.path.splitext(name)[0]}_{timestamp}.json"
                    backup_filepath = os.path.join(BACKUP_DIR, backup_filename)
                    shutil.copy2(path, backup_filepath)
                    for admin_id in OWNER_IDS:
                        caption_text = f"📦 <b>Auto Backup (2 Hours):</b> <code>{name}</code>\n📅 <i>{get_bd_now().strftime('%d %b, %I:%M %p')} (BD)</i>"
                        send_document(admin_id, backup_filepath, caption=caption_text)
                        time.sleep(2)
                except Exception as e:
                    print(f"Auto-backup error: {e}")

threading.Thread(target=auto_backup_worker, daemon=True).start()

# ================= Anti-Waste Auto Release Engine =================
def uncopied_number_timeout_cleaner():
    while True:
        time.sleep(20)
        try:
            load_data()
            timeout_sec = int(db.get("num_timeout_minutes", 10)) * 60
            now_ts = time.time()
            sessions = dict(db.get("active_sessions", {}))
            changed = False

            for uid_str, s_info in sessions.items():
                if not s_info.get("copied", False):
                    assigned_at = s_info.get("assigned_at", 0)
                    if assigned_at > 0 and (now_ts - assigned_at) >= timeout_sec:
                        nums = s_info.get("nums", [])
                        r_name = s_info.get("range", "")
                        msg_id_to_del = s_info.get("msg_id")

                        if msg_id_to_del:
                            delete_msg(int(uid_str), msg_id_to_del)

                        if r_name and nums:
                            if r_name not in db["ranges"]: db["ranges"][r_name] = []
                            for n in nums:
                                if n not in db["ranges"][r_name]:
                                    db["ranges"][r_name].append(n)
                                clean_d = re.sub(r'\D', '', str(n))
                                if clean_d in db.get("assigned_numbers", {}):
                                    del db["assigned_numbers"][clean_d]
                                if clean_d in db.get("number_ranges", {}):
                                    del db["number_ranges"][clean_d]

                            del db["active_sessions"][uid_str]
                            changed = True
                            send_msg(int(uid_str), f"⏱ <b>Number Expired!</b>\nApni {db.get('num_timeout_minutes', 10)} min er moddhe number copy na koray number gulo remove hoye stock-e ferot geche.")

            if changed:
                save_data()
        except Exception as e:
            print(f"Timeout cleaner error: {e}")

threading.Thread(target=uncopied_number_timeout_cleaner, daemon=True).start()

# ================= Daily 6:00 AM BD Reset Checker =================
def bd_6am_reset_checker():
    while True:
        time.sleep(60)
        try:
            load_data()
            cur_reset_day = get_bd_reset_day_str()
            if db.get("last_reset_day") != cur_reset_day:
                db["last_reset_day"] = cur_reset_day
                save_data()
                reset_today_stats_for_all_users()
                print(f"🌅 [BD 6:00 AM RESET] Daily earnings reset completed for: {cur_reset_day}")
        except Exception as e:
            print(f"Reset checker error: {e}")

threading.Thread(target=bd_6am_reset_checker, daemon=True).start()

# ================= Keyboards =================
def main_kb(user_id):
    kb = [
        [
            {"text": "GET NUMBER", "icon_custom_emoji_id": "5337132498965010628", "style": "primary"},
            {"text": "Balance", "icon_custom_emoji_id": "5348469219761626211", "style": "success"}
        ],
        [
            {"text": "Profile", "icon_custom_emoji_id": "5352861489541714456", "style": "primary"},
            {"text": "🚦 Live Traffic", "icon_custom_emoji_id": "5353032893096567467", "style": "success"}
        ],
        [
            {"text": "OTP Channel", "icon_custom_emoji_id": "5420517437885943844", "style": "primary"},
            {"text": "Support", "icon_custom_emoji_id": "5336850036145823599", "style": "primary"}
        ]
    ]
    if is_admin(user_id):
        kb.append([{"text": "Admin Panel", "icon_custom_emoji_id": "5420155432272438703", "style": "danger"}])
    return {"keyboard": kb, "resize_keyboard": True}

def cancel_kb():
    return {"inline_keyboard": [[{"text": "Cancel Operation", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "cancel_state", "style": "danger"}]]}

def admin_kb():
    load_data()
    m_mode = db.get("maintenance_mode", False)
    m_btn_text = "🟢 Maintenance: ON (Pause Bot)" if m_mode else "⚪ Maintenance: OFF"
    m_style = "danger" if m_mode else "primary"

    return {"inline_keyboard": [
        [
            {"text": "👤 User Management", "callback_data": "adm_user_manage", "style": "primary"},
            {"text": "🏆 Leaderboard", "callback_data": "lb_tab_today", "style": "success"}
        ],
        [
            {"text": "📈 Revenue Analytics", "callback_data": "adm_analytics", "style": "success"},
            {"text": "📜 Withdraw History", "callback_data": "adm_wd_history", "style": "primary"}
        ],
        [
            {"text": "Upload Numbers", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "adm_add_num", "style": "primary"},
            {"text": "Delete Range", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "adm_del_range", "style": "danger"}
        ],
        [
            {"text": "💰 OTP Rate Manager", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "adm_rates", "style": "success"},
            {"text": "Min Withdraw", "icon_custom_emoji_id": "5190899075968441286", "callback_data": "adm_min_w", "style": "primary"}
        ],
        [
            {"text": "⏱ Auto-Release Timer", "callback_data": "adm_set_timeout", "style": "primary"},
            {"text": "👑 Manage Admins", "callback_data": "adm_manage_admins", "style": "primary"}
        ],
        [
            {"text": m_btn_text, "callback_data": "adm_toggle_maintenance", "style": m_style}
        ],
        [
            {"text": "📥 Download DB", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "adm_db_menu", "style": "primary"},
            {"text": "Broadcast", "icon_custom_emoji_id": "5789428375261023681", "callback_data": "adm_broadcast", "style": "primary"}
        ],
        [
            {"text": "Set Support User", "icon_custom_emoji_id": "5336850036145823599", "callback_data": "adm_set_support", "style": "primary"},
            {"text": "Close Console", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close", "style": "danger"}
        ]
    ]}

def render_live_traffic_view():
    load_data()
    ranges = db.get("ranges", {})
    traffic_stats = db.get("range_traffic_otps", {})
    range_rates = db.get("range_rates", {})
    default_rate = float(db.get("default_otp_rate", 5.0))

    sorted_ranges = []
    for r_name in ranges.keys():
        stock_count = len(ranges[r_name])
        otp_hits = int(traffic_stats.get(r_name, 0))
        rate = float(range_rates.get(r_name, default_rate))
        sorted_ranges.append({
            "name": r_name,
            "stock": stock_count,
            "otps": otp_hits,
            "rate": rate
        })

    sorted_ranges.sort(key=lambda x: (x["otps"], x["stock"]), reverse=True)

    txt = "🚦 <b>LIVE RANGE TRAFFIC</b>\n"
    txt += "<i>রিয়েল-টাইম এক্টিভ রেঞ্জ ও ওটিপি ফ্লো:</i>\n\n"

    if not sorted_ranges:
        txt += "❌ <i>বর্তমানে কোনো সচল রেঞ্জ নেই!</i>"
    else:
        for idx, r in enumerate(sorted_ranges):
            badge = "🔥 HOT" if (idx < 3 and r["otps"] > 0) else "🟢 ACTIVE"
            txt += f"<b>{idx+1}. {r['name']}</b> ❪{badge}❫\n"
            txt += f" ├ ⚡ Hits: <b>{r['otps']} OTP</b>\n"
            txt += f" ├ 📦 Stock: <b>{r['stock']} pcs</b>\n"
            txt += f" └ 💰 Rate: <b>{r['rate']:.1f} BDT</b>\n\n"

    kb = {
        "inline_keyboard": [
            [{"text": "🔄 Refresh Traffic", "callback_data": "refresh_live_traffic", "style": "success"}],
            [{"text": "❌ Close", "callback_data": "close", "style": "danger"}]
        ]
    }
    return txt, kb

def leaderboard_kb(active_tab):
    return {"inline_keyboard": [
        [
            {"text": "Today" + (" •" if active_tab == "today" else ""), "callback_data": "lb_tab_today", "style": "success" if active_tab == "today" else "primary"},
            {"text": "Weekly" + (" •" if active_tab == "weekly" else ""), "callback_data": "lb_tab_weekly", "style": "success" if active_tab == "weekly" else "primary"},
            {"text": "Monthly" + (" •" if active_tab == "monthly" else ""), "callback_data": "lb_tab_monthly", "style": "success" if active_tab == "monthly" else "primary"},
            {"text": "All-Time" + (" •" if active_tab == "alltime" else ""), "callback_data": "lb_tab_alltime", "style": "success" if active_tab == "alltime" else "primary"}
        ],
        [
            {"text": "🔄 Refresh", "callback_data": f"lb_tab_{active_tab}", "style": "primary"},
            {"text": "Back to Admin", "callback_data": "admin_main", "style": "danger"}
        ]
    ]}

def generate_leaderboard_text(tab):
    load_data()
    all_users = get_all_users_from_file()
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    ranking_data = []

    if tab == "today":
        header_title = "🌟 TODAY'S LIVE LEADERBOARD (ADMIN)"
        subtitle = "<i>(প্রতিদিন সকাল ৬:০০ টায় অটো রিসেট হয়)</i>"
        for uid, u in all_users.items():
            otps = int(u.get("today_otps", 0))
            amt = float(u.get("today_earnings", 0.0))
            if otps > 0 or amt > 0:
                ranking_data.append({"uid": uid, "username": u.get("username", ""), "otps": otps, "amt": amt})
        ranking_data.sort(key=lambda x: (x["otps"], x["amt"]), reverse=True)

    elif tab == "alltime":
        header_title = "🌐 ALL-TIME TOP EARNERS (ADMIN)"
        subtitle = "<i>(সর্বমোট লাইফটাইম পরিসংখ্যান)</i>"
        for uid, u in all_users.items():
            otps = int(u.get("total_otps", 0))
            amt = float(u.get("total_earnings", 0.0))
            if otps > 0 or amt > 0:
                ranking_data.append({"uid": uid, "username": u.get("username", ""), "otps": otps, "amt": amt})
        ranking_data.sort(key=lambda x: (x["otps"], x["amt"]), reverse=True)

    else:
        now_dt = get_bd_now()
        days = 7 if tab == "weekly" else 30
        header_title = f"🗓 {'WEEKLY' if tab == 'weekly' else 'MONTHLY'} TOP PERFORMERS (ADMIN)"
        subtitle = f"<i>(গত {days} দিনের পারফরম্যান্স রিপোর্ট)</i>"
        aggregated = {}

        for i in range(days):
            d_str = (now_dt - timedelta(days=i)).strftime('%Y-%m-%d')
            day_data = db.get("user_period_stats", {}).get(d_str, {})
            for uid, s in day_data.items():
                if uid not in aggregated: aggregated[uid] = {"otps": 0, "amt": 0.0}
                aggregated[uid]["otps"] += int(s.get("otps", 0))
                aggregated[uid]["amt"] += float(s.get("amount", 0.0))

        for uid, s in aggregated.items():
            u = all_users.get(uid, {})
            ranking_data.append({"uid": uid, "username": u.get("username", ""), "otps": s["otps"], "amt": s["amt"]})
        ranking_data.sort(key=lambda x: (x["otps"], x["amt"]), reverse=True)

    txt = f"""╔══════════════════════════╗
║ 🏆 <b>{header_title}</b>
╠══════════════════════════╣
║ {subtitle}
╚══════════════════════════╝\n\n"""

    if not ranking_data:
        txt += "ℹ️ <i>এই সময়কালের মধ্যে এখনো কোনো রেকর্ড নেই!</i>\n"
    else:
        for idx, item in enumerate(ranking_data[:10]):
            badge = medals[idx] if idx < len(medals) else "👤"
            u_tag = f"@{item['username']}" if item['username'] else f"<code>{item['uid']}</code>"
            txt += f"<b>{badge} {u_tag}</b>\n"
            txt += f"    🔐 OTP: <b>{item['otps']}</b> টি | 💰 Earned: <b>{item['amt']:.2f} BDT</b>\n"
            txt += "──────────────────────────\n"

    return txt

def user_card_kb(target_uid, is_banned):
    ban_btn_text = "🟢 Unban User" if is_banned else "🔴 Ban User"
    ban_action = f"ub_unban_{target_uid}" if is_banned else f"ub_ban_{target_uid}"
    return {"inline_keyboard": [
        [
            {"text": "➕ Add Balance", "callback_data": f"ub_add_{target_uid}", "style": "success"},
            {"text": "➖ Cut Balance", "callback_data": f"ub_cut_{target_uid}", "style": "danger"}
        ],
        [
            {"text": "✉️ Send Direct Message", "callback_data": f"ub_msg_{target_uid}", "style": "primary"},
            {"text": ban_btn_text, "callback_data": ban_action, "style": "danger"}
        ],
        [
            {"text": "🔄 Refresh Details", "callback_data": f"ub_view_{target_uid}", "style": "primary"},
            {"text": "Back to Admin", "callback_data": "admin_main", "style": "primary"}
        ]
    ]}

def render_user_manage_profile(target_uid):
    users = get_all_users_from_file()
    uid_str = str(target_uid).strip()
    if uid_str not in users:
        return None, None

    u = users[uid_str]
    is_banned = int(uid_str) in db.get("banned_users", [])
    status_tag = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
    u_tag = f"@{u.get('username')}" if u.get("username") else "No Username"
    reg_date = datetime.fromtimestamp(u.get("registered_at", time.time())).strftime('%d-%m-%Y %I:%M %p')

    card = f"""╔══════════════════════╗
║ 👤 <b>USER MANAGEMENT CONSOLE</b>
╚══════════════════════╝
🆔 <b>User ID:</b> <code>{uid_str}</code>
🏷 <b>Username:</b> {u_tag}
🚦 <b>Status:</b> <b>{status_tag}</b>
💰 <b>Current Balance:</b> <b>{u.get('balance', 0.0):.2f} BDT</b>
🌟 <b>Today Earned:</b> <b>{u.get('today_earnings', 0.0):.2f} BDT</b>
📊 <b>Total Earned:</b> <b>{u.get('total_earnings', 0.0):.2f} BDT</b>
🔐 <b>Today OTPs:</b> <b>{u.get('today_otps', 0)}</b> টি
🔐 <b>Total OTPs:</b> <b>{u.get('total_otps', 0)}</b> টি
📅 <b>Registered At:</b> {reg_date}
👥 <b>Referred By:</b> <code>{u.get('referred_by') or 'None'}</code>
"""
    return card, user_card_kb(uid_str, is_banned)

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    sender_id = msg.get("from", {}).get("id", chat_id)
    text = msg.get("text", "").strip()
    username = msg.get("from", {}).get("username", "")

    if is_spamming(sender_id):
        return

    if sender_id in db.get("banned_users", []):
        send_msg(chat_id, f"{PEM['no']} <b>Apnar account ti suspend/ban kora hoyeche!</b>\nSupport team er shathe jogajog korun.")
        return

    if db.get("maintenance_mode", False) and not is_admin(sender_id):
        send_msg(chat_id, f"🛠 <b>Bot is currently updating!</b>\nAmra system update korchi. Khub shighroi bot abar shuru hobe. Dhorjo dhorun.")
        return

    get_user(sender_id, username=username)

    if not is_admin(sender_id) and not text.startswith("/start"):
        if not check_user_membership(sender_id):
            send_verification_prompt(chat_id)
            return

    if text in ["/id", "/myid"]:
        send_msg(chat_id, f"🆔 Apnar Telegram ID: <code>{sender_id}</code>\nAdmin Status: <b>{'✅ Yes' if is_admin(sender_id) else '❌ No'}</b>")
        return

    if text in ["/admin", "Admin Panel"] or "Admin Panel" in text:
        if is_admin(sender_id):
            send_msg(chat_id, f"{PEM['admin']} <b>Admin Control Console</b>", reply_markup=admin_kb())
            return

    MAIN_COMMANDS = ["/start", "GET NUMBER", "Balance", "Profile", "🚦 Live Traffic", "Support", "OTP Channel", "Admin Panel"]
    if any(text.startswith(cmd) for cmd in MAIN_COMMANDS):
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]

    if chat_id in user_states:
        state = user_states[chat_id]

        if state == "wait_manage_uid" and text:
            target_uid = text.strip()
            card, kb = render_user_manage_profile(target_uid)
            if not card:
                send_msg(chat_id, f"{PEM['no']} <b>User ID {target_uid} khuje paoa jayni!</b>\nSothik Telegram Numeric User ID pathan ba Cancel korun:", reply_markup=cancel_kb())
                return
            del user_states[chat_id]
            send_msg(chat_id, card, reply_markup=kb)
            return

        elif state == "wait_ub_add_val" and text:
            target_uid = temp_data[chat_id]["target_uid"]
            try:
                amt = float(text)
                new_bal = update_balance(target_uid, amt, is_earning=False)
                send_msg(chat_id, f"{PEM['ok']} User <code>{target_uid}</code> er balance e <b>+{amt:.2f} BDT</b> add kora hoyeche!\nNotun Balance: <b>{new_bal:.2f} BDT</b>")
                send_msg(target_uid, f"🎁 <b>Admin apnar account-e +{amt:.2f} BDT balance jog koreche!</b>\nCurrent Balance: <code>{new_bal:.2f} BDT</code>")
            except ValueError:
                send_msg(chat_id, f"{PEM['no']} Invalid amount! Shudhu number pathan:")
                return
            del user_states[chat_id]
            del temp_data[chat_id]
            card, kb = render_user_manage_profile(target_uid)
            if card: send_msg(chat_id, card, reply_markup=kb)
            return

        elif state == "wait_ub_cut_val" and text:
            target_uid = temp_data[chat_id]["target_uid"]
            try:
                amt = float(text)
                new_bal = update_balance(target_uid, -amt, is_earning=False)
                send_msg(chat_id, f"{PEM['ok']} User <code>{target_uid}</code> er balance theke <b>-{amt:.2f} BDT</b> kete neya hoyeche!\nNotun Balance: <b>{new_bal:.2f} BDT</b>")
                send_msg(target_uid, f"⚠️ <b>Admin apnar account theke -{amt:.2f} BDT kete niyeche!</b>\nCurrent Balance: <code>{new_bal:.2f} BDT</code>")
            except ValueError:
                send_msg(chat_id, f"{PEM['no']} Invalid amount! Shudhu number pathan:")
                return
            del user_states[chat_id]
            del temp_data[chat_id]
            card, kb = render_user_manage_profile(target_uid)
            if card: send_msg(chat_id, card, reply_markup=kb)
            return

        elif state == "wait_ub_msg_val" and text:
            target_uid = temp_data[chat_id]["target_uid"]
            res = send_msg(target_uid, f"📩 <b>Notification from Admin:</b>\n\n{text}")
            if res.get("ok"):
                send_msg(chat_id, f"{PEM['ok']} User <code>{target_uid}</code> ke message pathano hoyeche!")
            else:
                send_msg(chat_id, f"{PEM['no']} Message pathano jayni! User bot block kore rekheche hoyto.")
            del user_states[chat_id]
            del temp_data[chat_id]
            card, kb = render_user_manage_profile(target_uid)
            if card: send_msg(chat_id, card, reply_markup=kb)
            return

        elif state == "wait_timeout_val" and text:
            try:
                mins = int(text.strip())
                if mins < 1: mins = 1
                db["num_timeout_minutes"] = mins
                save_data()
                send_msg(chat_id, f"{PEM['ok']} <b>Auto-Release Timeout set to: {mins} Minutes!</b>\nUser number copy na korle {mins} min por stock-e ferot ashbe.", reply_markup=main_kb(sender_id))
            except ValueError:
                send_msg(chat_id, f"{PEM['no']} Shudhu integer number pathan (e.g. 5, 10, 15):", reply_markup=cancel_kb())
                return
            del user_states[chat_id]
            return

        elif state == "wait_range_name" and text:
            temp_data[chat_id] = {"range": text}
            user_states[chat_id] = "wait_numbers_input"
            send_msg(chat_id, f"{PEM['pin']} <b>Range Name:</b> <code>{text}</code>\n\n{PEM['upload']} Ekhon number gulo pathan:\n• Direct Text (line by line)\n• Othoba <b>.txt</b> file upload korun:\n\n<i>(Note: Duplicate ba already assigned number thakle ta auto skip hobe)</i>", reply_markup=cancel_kb())
            return

        elif state == "wait_numbers_input":
            raw_lines = []
            if "document" in msg:
                doc = msg["document"]
                if doc["file_name"].endswith(".txt"):
                    f_info = api_call("getFile", {"file_id": doc["file_id"]})
                    f_path = f_info.get("result", {}).get("file_path")
                    f_content = requests.get(f"{FILE_URL}{f_path}").text
                    raw_lines = f_content.splitlines()
            elif text:
                raw_lines = re.split(r'[\n,]+', text)

            load_data()
            all_existing_numbers = set()
            for r_list in db.get("ranges", {}).values():
                for n in r_list:
                    all_existing_numbers.add(re.sub(r'\D', '', str(n)))
            for assigned_n in db.get("assigned_numbers", {}).keys():
                all_existing_numbers.add(re.sub(r'\D', '', str(assigned_n)))

            clean_nums = []
            duplicate_count = 0
            for item in raw_lines:
                clean_item = re.sub(r'[^\d+]', '', item.strip())
                digits_only = re.sub(r'\D', '', clean_item)
                if digits_only and len(digits_only) >= 7:
                    if digits_only in all_existing_numbers:
                        duplicate_count += 1
                        continue
                    if not clean_item.startswith("+"): clean_item = "+" + clean_item
                    clean_nums.append(clean_item)
                    all_existing_numbers.add(digits_only)

            if not clean_nums:
                send_msg(chat_id, f"{PEM['no']} <b>Kono notun number paoa jayni!</b>\nShob number already stock-e ase ba duplicate ({duplicate_count} skipped).", reply_markup=cancel_kb())
                return

            range_name = temp_data[chat_id]["range"]
            if range_name not in db["ranges"]:
                db["ranges"][range_name] = []

            db["ranges"][range_name].extend(clean_nums)
            save_data()

            check_and_alert_low_stock(range_name, len(db["ranges"][range_name]))

            send_msg(chat_id, f"{PEM['ok']} Range <b>{range_name}</b> e notun <b>{len(clean_nums)}</b> ti number add hoyeche!\n⚠️ <b>{duplicate_count}</b> ti duplicate number skip kora hoyeche.", reply_markup=main_kb(sender_id))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_withdraw_amount" and text:
            try:
                amt = float(text)
                min_w = db.get("min_withdraw", 50.0)
                current_bal = get_user(sender_id).get("balance", 0.0)

                if amt < min_w:
                    send_msg(chat_id, f"{PEM['no']} <b>Minimum withdrawal limit: {min_w} BDT!</b>\nAbar amount pathan:", reply_markup=cancel_kb())
                    return
                if amt > current_bal:
                    send_msg(chat_id, f"{PEM['no']} <b>Account e porjapto balance nei!</b>\nCurrent Balance: <code>{current_bal:.2f} BDT</code>\nAbar amount pathan:", reply_markup=cancel_kb())
                    return

                temp_data[chat_id] = {"amount": amt}
                del user_states[chat_id]

                method_kb = {
                    "inline_keyboard": [
                        [{"text": "📱 bKash (Personal)", "callback_data": "wmethod_bkash", "style": "primary"}],
                        [{"text": "🔶 Binance Pay (UID)", "callback_data": "wmethod_binance", "style": "primary"}],
                        [{"text": "Cancel", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "cancel_state", "style": "danger"}]
                    ]
                }
                send_msg(chat_id, f"{PEM['bank']} <b>Select Withdrawal Method:</b>\n\nAmount: <b>{amt:.2f} BDT</b>\nNicher theke method select korun:", reply_markup=method_kb)
            except ValueError:
                send_msg(chat_id, f"{PEM['no']} Invalid amount! Shudhu number pathan:", reply_markup=cancel_kb())
            return

        elif state == "wait_user_acc_details" and text:
            account_val = text.strip()
            method_type = temp_data[chat_id].get("method", "Other")

            if method_type == "bKash":
                clean_phone = re.sub(r'\D', '', account_val)
                if len(clean_phone) < 11:
                    send_msg(chat_id, f"{PEM['no']} <b>Invalid bKash number!</b>\n11 digit er number pathan:", reply_markup=cancel_kb())
                    return
                account_val = clean_phone

            amt = temp_data[chat_id]["amount"]
            temp_data[chat_id]["account"] = account_val

            confirm_txt = f"""╔══════════════════════╗
║ {PEM['warn']} <b>CONFIRM WITHDRAWAL</b>
║ 💰 <b>Amount:</b> <b>{amt:.2f} BDT</b>
║ 💳 <b>Method:</b> <b>{method_type}</b>
║ 🎯 <b>Account / ID:</b> <code>{account_val}</code>
╚══════════════════════╝"""

            kb = {
                "inline_keyboard": [
                    [{"text": "Confirm & Submit", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "confirm_withdraw_req", "style": "success"}],
                    [{"text": "Cancel", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "cancel_state", "style": "danger"}]
                ]
            }
            send_msg(chat_id, confirm_txt, reply_markup=kb)
            return

        elif state == "wait_global_rate" and text:
            try:
                rate = float(text)
                db["default_otp_rate"] = rate
                save_data()
                send_msg(chat_id, f"{PEM['ok']} <b>Global Default OTP Rate</b> updated: <b>{rate} BDT</b>", reply_markup=main_kb(sender_id))
            except ValueError:
                send_msg(chat_id, f"{PEM['no']} Invalid rate!")
            del user_states[chat_id]
            return

        elif state == "wait_range_rate_val" and text:
            try:
                rate = float(text)
                r_target = temp_data[chat_id]["range"]
                if "range_rates" not in db: db["range_rates"] = {}
                db["range_rates"][r_target] = rate
                save_data()
                send_msg(chat_id, f"{PEM['ok']} Range <b>{r_target}</b> per OTP rate: <b>{rate} BDT</b>", reply_markup=main_kb(sender_id))
            except ValueError:
                send_msg(chat_id, f"{PEM['no']} Invalid rate!")
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_min_w_val" and text:
            try:
                min_w = float(text)
                db["min_withdraw"] = min_w
                save_data()
                send_msg(chat_id, f"{PEM['ok']} <b>Min Withdraw:</b> <b>{min_w} BDT</b>", reply_markup=main_kb(sender_id))
            except ValueError:
                send_msg(chat_id, f"{PEM['no']} Invalid number!")
            del user_states[chat_id]
            return

        elif state == "wait_support_uname" and text:
            clean_u = text.replace("@", "").strip()
            if "settings" not in db: db["settings"] = {}
            db["settings"]["support_username"] = clean_u
            save_data()
            del user_states[chat_id]
            send_msg(chat_id, f"{PEM['ok']} Support username: <b>@{clean_u}</b>", reply_markup=main_kb(sender_id))
            return

        elif state == "wait_broadcast":
            del user_states[chat_id]
            send_msg(chat_id, f"{PEM['rocket']} Broadcast shuru hocche...")
            count = 0
            all_u = get_all_users_from_file()
            for u_id in list(all_u.keys()):
                res = api_call("copyMessage", {"chat_id": u_id, "from_chat_id": chat_id, "message_id": msg["message_id"]})
                if res.get("ok"): count += 1
                time.sleep(0.04)
            send_msg(chat_id, f"{PEM['ok']} <b>Broadcast Complete!</b> ({count} sent)")
            return

        elif state == "wait_new_admin" and text:
            del user_states[chat_id]
            if text.isdigit():
                aid = int(text)
                if aid not in db["admins"]:
                    db["admins"].append(aid)
                    save_data()
                    send_msg(chat_id, f"{PEM['ok']} Admin ID <code>{text}</code> added!")
                else:
                    send_msg(chat_id, f"{PEM['warn']} Admin ID already exists!")
            else:
                send_msg(chat_id, f"{PEM['no']} Invalid numeric ID!")
            return

    if text.startswith("/start"):
        parts = text.split()
        if len(parts) > 1 and parts[1].startswith("ref_"):
            inviter_uid = parts[1].replace("ref_", "").strip()
            users = get_all_users_from_file()
            if str(sender_id) in users:
                if not users[str(sender_id)].get("referred_by") and inviter_uid != str(sender_id):
                    users[str(sender_id)]["referred_by"] = inviter_uid
                    save_all_users_to_file(users)
            else:
                get_user(sender_id, username=username)
                if inviter_uid != str(sender_id):
                    users = get_all_users_from_file()
                    users[str(sender_id)]["referred_by"] = inviter_uid
                    save_all_users_to_file(users)

        if not is_admin(sender_id) and not check_user_membership(sender_id):
            send_verification_prompt(chat_id)
            return

        send_msg(chat_id, f"{PEM['hi']} <b>Welcome!</b> Menu theke service select korun:", reply_markup=main_kb(sender_id))

    elif "GET NUMBER" in text:
        load_data()
        if not db.get("ranges"):
            send_msg(chat_id, f"{PEM['no']} Kono range e number available nei.")
            return
        kb = []
        for r_name in list(db["ranges"].keys()):
            count = len(db["ranges"][r_name])
            if count > 0:
                rate = db.get("range_rates", {}).get(r_name, db.get("default_otp_rate", 5.0))
                kb.append([{"text": f"{r_name} ({count} left) | {rate} BDT", "icon_custom_emoji_id": "5336972142066047577", "callback_data": f"sel_r_{r_name}", "style": "primary"}])
        if not kb:
            send_msg(chat_id, f"{PEM['no']} Sob range e stock sesh.")
            return
        send_msg(chat_id, f"{PEM['pin']} <b>Select Target Range:</b>", reply_markup={"inline_keyboard": kb})

    elif "Balance" in text:
        u_data = get_user(sender_id, username=username)
        bal_txt = f"╔══════════════════════╗\n║ {PEM['money']} <b>YOUR BALANCE</b>\n║ {PEM['gift']} <b>Available:</b> <b>{u_data.get('balance', 0.0):.2f} BDT</b>\n║ 🌟 <b>Today:</b> <b>{u_data.get('today_earnings', 0.0):.2f} BDT</b>\n║ 📊 <b>Total:</b> <b>{u_data.get('total_earnings', 0.0):.2f} BDT</b>\n║ {PEM['lock']} <b>Today OTPs:</b> {u_data.get('today_otps', 0)}\n║ {PEM['lock']} <b>Total OTPs:</b> {u_data.get('total_otps', 0)}\n║ {PEM['bank']} <b>Min Withdraw:</b> {db.get('min_withdraw', 50.0)} BDT\n╚══════════════════════╝"
        kb = {
            "inline_keyboard": [
                [{"text": "Request Withdraw", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "start_withdraw", "style": "success"}],
                [{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": "refresh_balance", "style": "primary"}]
            ]
        }
        send_msg(chat_id, bal_txt, reply_markup=kb)

    elif "Profile" in text:
        u_data = get_user(sender_id, username=username)
        u_tag = f"@{u_data.get('username')}" if u_data.get("username") else "Not Set"
        
        bot_info = api_call("getMe").get("result", {})
        bot_name = bot_info.get("username", "YourBot")
        ref_link = f"https://t.me/{bot_name}?start=ref_{sender_id}"
        all_u = get_all_users_from_file()
        my_refs = [uid for uid, dat in all_u.items() if dat.get("referred_by") == str(sender_id)]
        
        msg_text = f"""━━━━━━━━━━━━━━━━━━
{PEM['user']} <b>USER PROFILE</b>
━━━━━━━━━━━━━━━━━━
🆔 <b>User ID:</b> <code>{sender_id}</code>
👤 <b>Username:</b> {u_tag}
{PEM['money']} <b>Balance:</b> <b>{u_data.get('balance', 0.0):.2f} BDT</b>
🌟 <b>Today:</b> <b>{u_data.get('today_earnings', 0.0):.2f} BDT</b>
📊 <b>Total:</b> <b>{u_data.get('total_earnings', 0.0):.2f} BDT</b>
{PEM['lock']} <b>Today OTPs:</b> <b>{u_data.get('today_otps', 0)}</b>
{PEM['lock']} <b>Total OTPs:</b> <b>{u_data.get('total_otps', 0)}</b>
━━━━━━━━━━━━━━━━━━
🎁 <b>Referral Program (6% Lifetime)</b>
👥 <b>Total Invited:</b> <b>{len(my_refs)} users</b>
🔗 <b>Your Link:</b>
<code>{ref_link}</code>"""
        
        profile_kb = {
            "inline_keyboard": [
                [{"text": "📋 Copy Referral Link", "copy_text": {"text": ref_link}, "style": "success"}],
                [{"text": "Refresh Profile", "callback_data": "refresh_profile", "style": "primary"}]
            ]
        }
        send_msg(chat_id, msg_text, reply_markup=profile_kb)

    elif "🚦 Live Traffic" in text:
        txt, kb = render_live_traffic_view()
        send_msg(chat_id, txt, reply_markup=kb)

    elif "Support" in text:
        sup_u = db.get("settings", {}).get("support_username", "SupportAdmin")
        send_msg(chat_id, f"{PEM['headset']} Support link:", reply_markup={"inline_keyboard": [[{"text": "Contact Support", "url": f"https://t.me/{sup_u}"}]]})

    elif "OTP Channel" in text:
        send_msg(chat_id, f"{PEM['msg']} <b>Official OTP Group:</b>\nhttps://t.me/msmethod/116")

    elif "Admin Panel" in text and is_admin(sender_id):
        send_msg(chat_id, f"{PEM['admin']} <b>Admin Control Console</b>", reply_markup=admin_kb())

def send_numbers_to_user(chat_id, range_name, msg_id=None, no_plus_mode=False, is_toggle=False):
    load_data()
    uid_str = str(chat_id)

    if is_toggle and uid_str in db.get("active_sessions", {}) and db["active_sessions"][uid_str].get("range") == range_name:
        pulled = db["active_sessions"][uid_str].get("nums", [])
        db["active_sessions"][uid_str]["no_plus"] = no_plus_mode
        save_data()
    else:
        if range_name not in db["ranges"] or not db["ranges"][range_name]:
            text = f"{PEM['no']} <b>{range_name}</b> range e number nei!"
            if msg_id: edit_msg(chat_id, msg_id, text)
            else: send_msg(chat_id, text)
            return

        # ==========================================
        # FIX: Remove user's previous assigned numbers to prevent OTP misrouting
        # ==========================================
        if "assigned_numbers" in db:
            old_nums_to_remove = [num for num, u_id in db["assigned_numbers"].items() if str(u_id) == uid_str]
            for num in old_nums_to_remove:
                del db["assigned_numbers"][num]
                if num in db.get("number_ranges", {}):
                    del db["number_ranges"][num]

        pulled = db["ranges"][range_name][:3]
        db["ranges"][range_name] = db["ranges"][range_name][3:]

        check_and_alert_low_stock(range_name, len(db["ranges"][range_name]))

        for n in pulled:
            clean = re.sub(r'\D', '', str(n))
            db["assigned_numbers"][clean] = chat_id
            db["number_ranges"][clean] = range_name

        db["active_sessions"][uid_str] = {
            "range": range_name,
            "nums": pulled,
            "no_plus": False,
            "assigned_at": time.time(),
            "copied": True,
            "msg_id": msg_id
        }
        save_data()
        no_plus_mode = False

    rate = db.get("range_rates", {}).get(range_name, db.get("default_otp_rate", 5.0))
    
    kb = []
    for n in pulled:
        clean_digits = re.sub(r'\D', '', str(n))
        formatted_num = clean_digits if no_plus_mode else f"+{clean_digits}"
        kb.append([{"text": f"📋 {formatted_num}", "copy_text": {"text": formatted_num}, "style": "primary"}])

    toggle_btn_text = "➕ Format: Add (+)" if no_plus_mode else "➖ Format: Remove (+)"
    next_toggle_mode = "0" if no_plus_mode else "1"

    kb.append([{"text": toggle_btn_text, "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"tog_p_{next_toggle_mode}", "style": "primary"}])
    kb.append([{"text": "Get New 3 Numbers", "icon_custom_emoji_id": "5352597830089347330", "callback_data": f"get_new_{range_name}", "style": "success"},
               {"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close", "style": "danger"}])

    text = f"╔══════════════════════╗\n║ {PEM['pin']} <b>Range:</b> {range_name}\n║ {PEM['money']} <b>Rate:</b> {rate} BDT\n╚══════════════════════╝"
    
    if msg_id:
        edit_msg(chat_id, msg_id, text, reply_markup={"inline_keyboard": kb})
    else:
        res = send_msg(chat_id, text, reply_markup={"inline_keyboard": kb})
        if res.get("ok") and uid_str in db.get("active_sessions", {}):
            db["active_sessions"][uid_str]["msg_id"] = res.get("result", {}).get("message_id")
            save_data()

def handle_callback(call):
    chat_id = call["message"]["chat"]["id"]
    from_user_id = call.get("from", {}).get("id", chat_id)
    msg_id = call["message"]["message_id"]
    data = call.get("data", "")
    call_id = call["id"]

    if is_spamming(from_user_id):
        api_call("answerCallbackQuery", {"callback_query_id": call_id, "text": "⚠️ Slow down!", "show_alert": False})
        return

    bypass_callbacks = ["check_join", "close", "cancel_state"]
    if not is_admin(from_user_id) and data not in bypass_callbacks:
        if not check_user_membership(from_user_id):
            api_call("answerCallbackQuery", {"callback_query_id": call_id, "text": "❌ Aghe group-e join kore Verify korun!", "show_alert": True})
            send_verification_prompt(chat_id, msg_id)
            return

    api_call("answerCallbackQuery", {"callback_query_id": call_id})

    if data == "check_join":
        if check_user_membership(from_user_id):
            delete_msg(chat_id, msg_id)
            send_msg(chat_id, f"{PEM['ok']} <b>Verification Successful!</b>\nEkhon apni bot use korte parben:", reply_markup=main_kb(from_user_id))
        else:
            api_call("answerCallbackQuery", {"callback_query_id": call_id, "text": "❌ Apni shob gulo group-e join করেননি! Aghe join korun.", "show_alert": True})

    elif data == "close":
        delete_msg(chat_id, msg_id)

    elif data == "cancel_state":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        delete_msg(chat_id, msg_id)
        send_msg(chat_id, f"{PEM['ok']} Cancelled.", reply_markup=main_kb(from_user_id))

    elif data == "refresh_live_traffic":
        txt, kb = render_live_traffic_view()
        edit_msg(chat_id, msg_id, txt, reply_markup=kb)

    elif data == "refresh_profile":
        u_data = get_user(from_user_id)
        u_tag = f"@{u_data.get('username')}" if u_data.get("username") else "Not Set"
        bot_info = api_call("getMe").get("result", {})
        bot_name = bot_info.get("username", "YourBot")
        ref_link = f"https://t.me/{bot_name}?start=ref_{from_user_id}"
        all_u = get_all_users_from_file()
        my_refs = [uid for uid, dat in all_u.items() if dat.get("referred_by") == str(from_user_id)]
        
        msg_text = f"""━━━━━━━━━━━━━━━━━━
{PEM['user']} <b>USER PROFILE</b>
━━━━━━━━━━━━━━━━━━
🆔 <b>User ID:</b> <code>{from_user_id}</code>
👤 <b>Username:</b> {u_tag}
{PEM['money']} <b>Balance:</b> <b>{u_data.get('balance', 0.0):.2f} BDT</b>
🌟 <b>Today:</b> <b>{u_data.get('today_earnings', 0.0):.2f} BDT</b>
📊 <b>Total:</b> <b>{u_data.get('total_earnings', 0.0):.2f} BDT</b>
{PEM['lock']} <b>Today OTPs:</b> <b>{u_data.get('today_otps', 0)}</b>
{PEM['lock']} <b>Total OTPs:</b> <b>{u_data.get('total_otps', 0)}</b>
━━━━━━━━━━━━━━━━━━
🎁 <b>Referral Program (6% Lifetime)</b>
👥 <b>Total Invited:</b> <b>{len(my_refs)} users</b>
🔗 <b>Your Link:</b>
<code>{ref_link}</code>"""
        
        profile_kb = {
            "inline_keyboard": [
                [{"text": "📋 Copy Referral Link", "copy_text": {"text": ref_link}, "style": "success"}],
                [{"text": "Refresh Profile", "callback_data": "refresh_profile", "style": "primary"}]
            ]
        }
        edit_msg(chat_id, msg_id, msg_text, reply_markup=profile_kb)

    elif data.startswith("cpnum_"):
        uid_str = str(chat_id)
        if uid_str in db.get("active_sessions", {}):
            db["active_sessions"][uid_str]["copied"] = True
            save_data()

    elif data.startswith("sel_r_"):
        send_numbers_to_user(chat_id, data.replace("sel_r_", "", 1), msg_id, is_toggle=False)

    elif data.startswith("get_new_"):
        send_numbers_to_user(chat_id, data.replace("get_new_", "", 1), msg_id, is_toggle=False)

    elif data.startswith("tog_p_"):
        mode = data.replace("tog_p_", "") == "1"
        r_name = db.get("active_sessions", {}).get(str(chat_id), {}).get("range", "")
        if r_name:
            send_numbers_to_user(chat_id, r_name, msg_id=msg_id, no_plus_mode=mode, is_toggle=True)

    elif data == "refresh_balance":
        u_data = get_user(from_user_id)
        bal_txt = f"╔══════════════════════╗\n║ {PEM['money']} <b>YOUR BALANCE</b>\n║ {PEM['gift']} <b>Available:</b> <b>{u_data.get('balance', 0.0):.2f} BDT</b>\n║ 🌟 <b>Today:</b> <b>{u_data.get('today_earnings', 0.0):.2f} BDT</b>\n║ 📊 <b>Total:</b> <b>{u_data.get('total_earnings', 0.0):.2f} BDT</b>\n╚══════════════════════╝"
        kb = {"inline_keyboard": [
            [{"text": "Request Withdraw", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "start_withdraw", "style": "success"}],
            [{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": "refresh_balance", "style": "primary"}]
        ]}
        edit_msg(chat_id, msg_id, bal_txt, reply_markup=kb)

    elif data == "start_withdraw":
        u_data = get_user(from_user_id)
        bal = u_data.get("balance", 0.0)
        min_w = db.get("min_withdraw", 50.0)
        if bal < min_w:
            api_call("answerCallbackQuery", {"callback_query_id": call_id, "text": f"❌ Min {min_w} BDT!", "show_alert": True})
            return
        user_states[chat_id] = "wait_withdraw_amount"
        edit_msg(chat_id, msg_id, f"📝 Koto taka withdraw korte chan? (Min: {min_w} BDT):", reply_markup=cancel_kb())

    elif data == "wmethod_bkash":
        temp_data[chat_id]["method"] = "bKash"
        user_states[chat_id] = "wait_user_acc_details"
        edit_msg(chat_id, msg_id, f"📱 Apnar <b>bKash Personal Number</b> pathan:\n<i>(e.g. 017xxxxxxxx)</i>", reply_markup=cancel_kb())

    elif data == "wmethod_binance":
        temp_data[chat_id]["method"] = "Binance Pay"
        user_states[chat_id] = "wait_user_acc_details"
        edit_msg(chat_id, msg_id, f"🔶 Apnar <b>Binance Pay ID / UID</b> pathan:", reply_markup=cancel_kb())

    elif data == "confirm_withdraw_req":
        if chat_id in temp_data and "amount" in temp_data[chat_id] and "account" in temp_data[chat_id]:
            amt = temp_data[chat_id]["amount"]
            method_type = temp_data[chat_id].get("method", "Other")
            account_val = temp_data[chat_id]["account"]
            u_info = get_user(from_user_id)

            if u_info.get("balance", 0.0) < amt:
                edit_msg(chat_id, msg_id, f"{PEM['no']} Account e porjapto balance nei!")
                return

            update_balance(from_user_id, -amt, is_earning=False)
            req_id = f"WD-{str(uuid.uuid4())[:6].upper()}"

            load_data()
            if "withdraw_requests" not in db: db["withdraw_requests"] = {}
            db["withdraw_requests"][req_id] = {
                "user_id": from_user_id,
                "username": u_info.get("username", ""),
                "amount": amt,
                "method": method_type,
                "account": account_val,
                "status": "pending",
                "time": time.time()
            }
            save_data()

            delete_msg(chat_id, msg_id)
            user_confirm = f"""╔══════════════════════╗
║ {PEM['ok']} <b>WITHDRAWAL SUBMITTED!</b>
║ 🧾 <b>Req ID:</b> <code>{req_id}</code>
║ 💰 <b>Amount:</b> <b>{amt:.2f} BDT</b>
║ 💳 <b>Method:</b> <b>{method_type}</b>
║ 🎯 <b>Account:</b> <code>{account_val}</code>
╚══════════════════════╝"""
            send_msg(chat_id, user_confirm, reply_markup=main_kb(from_user_id))

            u_tag = f"@{u_info.get('username')}" if u_info.get("username") else "None"
            time_now_str = get_bd_now().strftime('%d %b, %I:%M %p')

            admin_alert_card = f"""╔══════════════════════════╗
║ 🚨 <b>NEW WITHDRAWAL REQUEST</b>
╠══════════════════════════╣
║ 🆔 <b>User ID:</b> <code>{from_user_id}</code>
║ 👤 <b>Username:</b> {u_tag}
║ 💰 <b>Amount:</b> <b>{amt:.2f} BDT</b>
║ 💳 <b>Method:</b> <b>{method_type}</b>
║ 🎯 <b>Account:</b> <code>{account_val}</code>
║ 🧾 <b>Req ID:</b> <code>{req_id}</code>
║ 📅 <b>Time:</b> <i>{time_now_str} (BD)</i>
╚══════════════════════════╝"""

            admin_alert_kb = {
                "inline_keyboard": [
                    [{"text": f"📋 Copy {account_val}", "copy_text": {"text": str(account_val)}, "style": "primary"}],
                    [
                        {"text": "✅ Approve", "callback_data": f"wapp_{req_id}", "style": "success"},
                        {"text": "❌ Reject & Refund", "callback_data": f"wrej_{req_id}", "style": "danger"}
                    ]
                ]
            }

            # Sent to Withdraw Notify Group ID -5377908906
            send_msg(WITHDRAW_GROUP_ID, admin_alert_card, reply_markup=admin_alert_kb)

            del user_states[chat_id]
            del temp_data[chat_id]

    elif data.startswith("wapp_") or data.startswith("wrej_"):
        if not is_admin(from_user_id): return
        is_approve = data.startswith("wapp_")
        req_id = data.split("_")[1]
        load_data()
        req = db.get("withdraw_requests", {}).get(req_id)
        if not req or req.get("status") != "pending": return

        target_uid = req["user_id"]
        amt = req["amount"]
        m_name = req.get("method", "Payment")
        acc_info = req.get("account", "")

        if is_approve:
            req["status"] = "approved"
            save_data()
            edit_msg(chat_id, msg_id, f"{PEM['ok']} <b>WITHDRAWAL APPROVED</b>\n\n🆔 User: <code>{target_uid}</code>\n💰 Amount: <b>{amt:.2f} BDT</b>\n💳 Method: <b>{m_name}</b>\n🎯 Account: <code>{acc_info}</code>\n🧾 ID: <code>{req_id}</code>\n👨‍⚖️ By Admin: <code>{from_user_id}</code>")
            send_msg(target_uid, f"✅ <b>Payment Completed!</b>\nAmount: {amt:.2f} BDT ({m_name})\nAccount: <code>{acc_info}</code>")

            ref = get_user(target_uid).get("referred_by")
            if ref:
                comm = round(float(amt) * 0.06, 2)
                if comm > 0:
                    update_balance(ref, comm, is_earning=True)
                    send_msg(ref, f"🎉 <b>Referral Commission Received!</b>\nAmount: +{comm:.2f} BDT")
        else:
            req["status"] = "rejected"
            update_balance(target_uid, amt, is_earning=False)
            save_data()
            edit_msg(chat_id, msg_id, f"{PEM['no']} <b>WITHDRAWAL REJECTED</b>\n\n🆔 User: <code>{target_uid}</code>\n💰 Amount: <b>{amt:.2f} BDT</b> Refunded.")
            send_msg(target_uid, f"❌ <b>Apnar withdrawal request reject kora hoyeche!</b>\n💰 <b>{amt:.2f} BDT</b> balance-e refund hoyeche.")

    # ================= Admin Panel Actions =================
    elif is_admin(from_user_id):
        if data.startswith("lb_tab_"):
            tab = data.replace("lb_tab_", "")
            txt = generate_leaderboard_text(tab)
            edit_msg(chat_id, msg_id, txt, reply_markup=leaderboard_kb(tab))

        elif data == "adm_toggle_maintenance":
            load_data()
            db["maintenance_mode"] = not db.get("maintenance_mode", False)
            save_data()
            st_str = "ON" if db["maintenance_mode"] else "OFF"
            api_call("answerCallbackQuery", {"callback_query_id": call_id, "text": f"Maintenance Mode is now {st_str}!", "show_alert": True})
            edit_msg(chat_id, msg_id, f"{PEM['admin']} <b>Admin Control Console</b>", reply_markup=admin_kb())

        elif data == "adm_user_manage":
            user_states[chat_id] = "wait_manage_uid"
            edit_msg(chat_id, msg_id, f"{PEM['user']} <b>User Management</b>\n\nJe user-ke manage korte chan tar <b>Telegram Numeric User ID</b> pathan:", reply_markup=cancel_kb())

        elif data.startswith("ub_view_"):
            target_uid = data.replace("ub_view_", "")
            card, kb = render_user_manage_profile(target_uid)
            if card: edit_msg(chat_id, msg_id, card, reply_markup=kb)

        elif data.startswith("ub_add_"):
            target_uid = data.replace("ub_add_", "")
            temp_data[chat_id] = {"target_uid": target_uid}
            user_states[chat_id] = "wait_ub_add_val"
            edit_msg(chat_id, msg_id, f"➕ User <code>{target_uid}</code> er balance-e koto taka add korte chan? (e.g. 100):", reply_markup=cancel_kb())

        elif data.startswith("ub_cut_"):
            target_uid = data.replace("ub_cut_", "")
            temp_data[chat_id] = {"target_uid": target_uid}
            user_states[chat_id] = "wait_ub_cut_val"
            edit_msg(chat_id, msg_id, f"➖ User <code>{target_uid}</code> er balance theke koto taka cut/minus korte chan? (e.g. 50):", reply_markup=cancel_kb())

        elif data.startswith("ub_msg_"):
            target_uid = data.replace("ub_msg_", "")
            temp_data[chat_id] = {"target_uid": target_uid}
            user_states[chat_id] = "wait_ub_msg_val"
            edit_msg(chat_id, msg_id, f"✉️ User <code>{target_uid}</code> ke ki message pathate chan? Direct text pathan:", reply_markup=cancel_kb())

        elif data.startswith("ub_ban_"):
            target_uid = int(data.replace("ub_ban_", ""))
            load_data()
            if "banned_users" not in db: db["banned_users"] = []
            db["banned_users"].append(target_uid)
            db["banned_users"] = list(set(db["banned_users"]))
            save_data()
            card, kb = render_user_manage_profile(target_uid)
            if card: edit_msg(chat_id, msg_id, card, reply_markup=kb)

        elif data.startswith("ub_unban_"):
            target_uid = int(data.replace("ub_unban_", ""))
            load_data()
            if "banned_users" in db and target_uid in db["banned_users"]:
                db["banned_users"].remove(target_uid)
            save_data()
            card, kb = render_user_manage_profile(target_uid)
            if card: edit_msg(chat_id, msg_id, card, reply_markup=kb)

        elif data == "adm_wd_history":
            load_data()
            all_reqs = list(db.get("withdraw_requests", {}).values())
            if not all_reqs:
                txt = "📜 <b>Kono withdraw request record paoa jayni!</b>"
            else:
                txt = "📜 <b>RECENT WITHDRAWAL HISTORY (Last 10)</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                for req in reversed(all_reqs[-10:]):
                    st_icon = "⏳" if req.get("status") == "pending" else ("✅" if req.get("status") == "approved" else "❌")
                    dt_str = datetime.fromtimestamp(req.get("time", time.time())).strftime('%d-%b %I:%M%p')
                    txt += f"{st_icon} <b>{req.get('amount')} BDT</b> via <b>{req.get('method')}</b>\n"
                    txt += f"👤 <code>{req.get('user_id')}</code> | Acc: <code>{req.get('account')}</code>\n"
                    txt += f"📅 {dt_str} | Status: <i>{req.get('status').upper()}</i>\n"
                    txt += "────────────────────\n"
            edit_msg(chat_id, msg_id, txt, reply_markup={"inline_keyboard": [[{"text": "Back to Admin", "callback_data": "admin_main", "style": "primary"}]]})

        elif data == "adm_analytics":
            load_data()
            daily_stats = db.get("daily_system_earnings", {})
            now_dt = get_bd_now()

            weekly_amt = 0.0
            weekly_otps = 0
            for i in range(7):
                d_str = (now_dt - timedelta(days=i)).strftime('%Y-%m-%d')
                if d_str in daily_stats:
                    weekly_amt += daily_stats[d_str].get("amount", 0.0)
                    weekly_otps += daily_stats[d_str].get("otps", 0)

            monthly_amt = 0.0
            monthly_otps = 0
            for i in range(30):
                d_str = (now_dt - timedelta(days=i)).strftime('%Y-%m-%d')
                if d_str in daily_stats:
                    monthly_amt += daily_stats[d_str].get("amount", 0.0)
                    monthly_otps += daily_stats[d_str].get("otps", 0)

            all_users = get_all_users_from_file()
            total_all_users_earnings = sum(float(u.get("total_earnings", 0.0)) for u in all_users.values())
            total_all_users_otps = sum(int(u.get("total_otps", 0)) for u in all_users.values())

            analytics_txt = f"""╔══════════════════════════╗
║ 📈 <b>GLOBAL REVENUE ANALYTICS</b>
╠══════════════════════════╣
║ 🗓 <b>Last 7 Days (Weekly):</b>
║ 💰 Total Earned: <b>{weekly_amt:.2f} BDT</b>
║ 🔐 Total OTPs: <b>{weekly_otps}</b> টি
╠──────────────────────────╣
║ 📅 <b>Last 30 Days (Monthly):</b>
║ 💰 Total Earned: <b>{monthly_amt:.2f} BDT</b>
║ 🔐 Total OTPs: <b>{monthly_otps}</b> টি
╠──────────────────────────╣
║ 🌐 <b>All-Time System Stats:</b>
║ 💰 System Payout: <b>{total_all_users_earnings:.2f} BDT</b>
║ 📊 Delivered OTPs: <b>{total_all_users_otps}</b> টি
║ 👥 Registered Users: <b>{len(all_users)}</b>
╚══════════════════════════╝"""

            kb = [
                [{"text": "🔄 Refresh", "callback_data": "adm_analytics", "style": "primary"}],
                [
                    {"text": "🗑 Reset 7 Days", "callback_data": "rst_conf_7", "style": "danger"},
                    {"text": "🗑 Reset 30 Days", "callback_data": "rst_conf_30", "style": "danger"}
                ],
                [{"text": "Back to Admin", "callback_data": "admin_main", "style": "primary"}]
            ]
            edit_msg(chat_id, msg_id, analytics_txt, reply_markup={"inline_keyboard": kb})

        elif data.startswith("rst_conf_"):
            days = data.replace("rst_conf_", "")
            conf_txt = f"⚠️ <b>Last {days} Days er analytics stats reset korte chan?</b>"
            kb = [
                [{"text": f"✅ Yes, Reset {days} Days", "callback_data": f"rst_do_{days}", "style": "danger"}],
                [{"text": "Cancel", "callback_data": "adm_analytics", "style": "primary"}]
            ]
            edit_msg(chat_id, msg_id, conf_txt, reply_markup={"inline_keyboard": kb})

        elif data.startswith("rst_do_"):
            days = int(data.replace("rst_do_", ""))
            load_data()
            now_dt = get_bd_now()
            daily_stats = db.get("daily_system_earnings", {})
            for i in range(days):
                d_str = (now_dt - timedelta(days=i)).strftime('%Y-%m-%d')
                if d_str in daily_stats:
                    del daily_stats[d_str]
            db["daily_system_earnings"] = daily_stats
            save_data()
            edit_msg(chat_id, msg_id, f"{PEM['ok']} <b>Last {days} Days report reset kora hoyeche!</b>", reply_markup={"inline_keyboard": [[{"text": "Back to Analytics", "callback_data": "adm_analytics", "style": "primary"}]]})

        elif data == "adm_set_timeout":
            load_data()
            cur_to = db.get("num_timeout_minutes", 10)
            user_states[chat_id] = "wait_timeout_val"
            edit_msg(chat_id, msg_id, f"⏱ <b>Auto-Release Number Timeout</b>\n\nBortoman Timeout: <b>{cur_to} Minutes</b>\n\nUser number copy na korle koto minute por stock-e ferot ashbe? (e.g. 5, 10, 15):", reply_markup=cancel_kb())

        elif data == "adm_manage_admins":
            load_data()
            adms = db.get("admins", OWNER_IDS)
            txt = f"👑 <b>ADMIN MANAGEMENT PANEL</b>\n\nTotal Admins: <b>{len(adms)}</b>\nNicher list theke remove korte parben othoba notun add korte parben:\n"
            kb = []
            for aid in adms:
                if aid in OWNER_IDS:
                    kb.append([{"text": f"⭐ Owner: {aid}", "callback_data": "none", "style": "primary"}])
                else:
                    kb.append([
                        {"text": f"👤 UID: {aid}", "callback_data": "none"},
                        {"text": "❌ Remove", "callback_data": f"del_adm_{aid}", "style": "danger"}
                    ])
            kb.append([{"text": "➕ Add New Admin", "callback_data": "adm_add_admin_prompt", "style": "success"}])
            kb.append([{"text": "Back to Admin", "callback_data": "admin_main", "style": "primary"}])
            edit_msg(chat_id, msg_id, txt, reply_markup={"inline_keyboard": kb})

        elif data.startswith("del_adm_"):
            target_aid = int(data.replace("del_adm_", ""))
            load_data()
            if target_aid in db.get("admins", []):
                db["admins"].remove(target_aid)
                save_data()
                api_call("answerCallbackQuery", {"callback_query_id": call_id, "text": f"Admin {target_aid} Removed!", "show_alert": True})
            edit_msg(chat_id, msg_id, f"{PEM['ok']} Admin <code>{target_aid}</code> successfully removed!", reply_markup={"inline_keyboard": [[{"text": "Back to Admins", "callback_data": "adm_manage_admins", "style": "primary"}]]})

        elif data == "adm_add_admin_prompt":
            user_states[chat_id] = "wait_new_admin"
            edit_msg(chat_id, msg_id, "Notun Admin-er numeric <b>Telegram User ID</b> pathan:", reply_markup=cancel_kb())

        elif data == "adm_rates":
            load_data()
            def_rate = db.get("default_otp_rate", 5.0)
            kb = [
                [{"text": f"🌐 Set Global Rate ({def_rate} BDT)", "callback_data": "set_global_rate", "style": "primary"}],
                [{"text": "🎯 Set Specific Range Rate", "callback_data": "choose_range_rate", "style": "success"}],
                [{"text": "Back to Admin", "callback_data": "admin_main", "style": "danger"}]
            ]
            edit_msg(chat_id, msg_id, f"💰 <b>OTP RATE MANAGER</b>\n\n🌐 Current Global Rate: <b>{def_rate} BDT</b>", reply_markup={"inline_keyboard": kb})

        elif data == "choose_range_rate":
            load_data()
            ranges = list(db.get("ranges", {}).keys())
            if not ranges:
                edit_msg(chat_id, msg_id, f"{PEM['no']} Kono range toiri kora nei!", reply_markup={"inline_keyboard": [[{"text": "Back", "callback_data": "adm_rates", "style": "primary"}]]})
            else:
                kb = []
                for r in ranges:
                    cur_rate = db.get("range_rates", {}).get(r, db.get("default_otp_rate", 5.0))
                    kb.append([{"text": f"{r} » {cur_rate} BDT", "callback_data": f"setr_rate_{r}", "style": "primary"}])
                kb.append([{"text": "Back", "callback_data": "adm_rates", "style": "danger"}])
                edit_msg(chat_id, msg_id, "📌 <b>Kon range-er rate change korte chan select korun:</b>", reply_markup={"inline_keyboard": kb})

        elif data.startswith("setr_rate_"):
            r_target = data.replace("setr_rate_", "")
            temp_data[chat_id] = {"range": r_target}
            user_states[chat_id] = "wait_range_rate_val"
            edit_msg(chat_id, msg_id, f"📝 <b>Range: {r_target}</b>\nPer OTP rate koto taka hobe? (e.g. 5, 8.5):", reply_markup=cancel_kb())

        elif data == "set_global_rate":
            user_states[chat_id] = "wait_global_rate"
            edit_msg(chat_id, msg_id, "Notun Global OTP Rate pathan:", reply_markup=cancel_kb())

        elif data == "adm_min_w":
            user_states[chat_id] = "wait_min_w_val"
            edit_msg(chat_id, msg_id, f"Current Min: {db.get('min_withdraw', 50.0)} BDT\nNotun Limit pathan:", reply_markup=cancel_kb())

        elif data == "adm_add_num":
            user_states[chat_id] = "wait_range_name"
            edit_msg(chat_id, msg_id, f"{PEM['pin']} Range Name pathan:", reply_markup=cancel_kb())

        elif data == "adm_del_range":
            load_data()
            kb = [[{"text": f"Delete {r}", "callback_data": f"delr_{r}", "style": "danger"}] for r in db["ranges"].keys()]
            kb.append([{"text": "Back", "callback_data": "admin_main", "style": "primary"}])
            edit_msg(chat_id, msg_id, "Select range to delete:", reply_markup={"inline_keyboard": kb})

        elif data.startswith("delr_"):
            r = data.replace("delr_", "")
            load_data()
            if r in db["ranges"]: del db["ranges"][r]
            if "range_rates" in db and r in db["range_rates"]: del db["range_rates"][r]
            save_data()
            edit_msg(chat_id, msg_id, f"Deleted: {r}")

        elif data == "adm_db_menu":
            edit_msg(chat_id, msg_id, "Database Export Panel:", reply_markup=db_backup_kb())

        elif data == "dl_bot_data":
            save_data()
            if os.path.exists(DB_FILE): send_document(chat_id, DB_FILE, caption="bot_data.json")

        elif data == "dl_users_db":
            if os.path.exists(USERS_FILE): send_document(chat_id, USERS_FILE, caption="users_db.json")

        elif data == "dl_both_files":
            save_data()
            if os.path.exists(DB_FILE): send_document(chat_id, DB_FILE, caption="bot_data.json")
            if os.path.exists(USERS_FILE): send_document(chat_id, USERS_FILE, caption="users_db.json")

        elif data == "adm_broadcast":
            user_states[chat_id] = "wait_broadcast"
            edit_msg(chat_id, msg_id, "Broadcast Message pathan:", reply_markup=cancel_kb())

        elif data == "adm_set_support":
            user_states[chat_id] = "wait_support_uname"
            edit_msg(chat_id, msg_id, "Notun Support username pathan:", reply_markup=cancel_kb())

        elif data == "admin_main":
            edit_msg(chat_id, msg_id, f"{PEM['admin']} <b>Admin Control Console</b>", reply_markup=admin_kb())

def main():
    offset = None
    executor = ThreadPoolExecutor(max_workers=50)
    print("🤖 Bot Controller Engine (Verified Admin Access + Forced Subscription) Running...")
    while True:
        try:
            updates = api_call("getUpdates", {"timeout": 30, "offset": offset})
            if updates and "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        executor.submit(handle_message, update["message"])
                    elif "callback_query" in update:
                        executor.submit(handle_callback, update["callback_query"])
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    main()
