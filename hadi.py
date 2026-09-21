import os
import re
import json
import time
import queue
import shutil
import hashlib
import requests
import threading
from collections import deque
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

BOT_TOKEN = "8867778383:AAGKHcZdr4mA7bX2Tl4AO_LOrqjelOlTqt4"
TELEGRAM_GROUP_ID = "-1004318007695"

HADI_API_TOKEN = "QlBUSUNBUzRGlpaERo5UV0ZSZ2R3VVBbfWCBRFN0Z2FJZ4NaZniVdQ=="
HADI_API_URL = "http://147.135.212.197/crapi/had/viewstats"

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "bot_data.json")
USERS_FILE = os.path.join(BASE_DIR, "users_db.json")

POLL_INTERVAL = 1.0
otp_task_queue = queue.Queue()

MAX_SIGNATURES = 20000
processed_sms_signatures = deque(maxlen=MAX_SIGNATURES)
signature_set = set()
file_lock = threading.Lock()

def create_safe_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504], raise_on_status=False)
    adapter = HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

http_session = create_safe_session()

COUNTRY_DIAL_FLAGS = {
    "1242": "🇧🇸", "1246": "🇧🇧", "1264": "🇦🇮", "1268": "🇦🇬", "1284": "🇻🇬",
    "1340": "🇻🇮", "1345": "🇰🇾", "1441": "🇧🇲", "1473": "🇬🇩", "1649": "🇹🇨", "1664": "🇲🇸",
    "1670": "🇲🇵", "1671": "🇬🇺", "1684": "🇦🇸", "1721": "🇸🇽", "1758": "🇱🇨", "1767": "🇩🇲",
    "1784": "🇻🇨", "1787": "🇵🇷", "1809": "🇩🇴", "1829": "🇩🇴", "1849": "🇩🇴", "1868": "🇹🇹",
    "1869": "🇰🇳", "1876": "🇯🇲", "1939": "🇵🇷",
    "995": "🇬🇪", "996": "🇰🇬", "998": "🇺🇿", "994": "🇦🇿", "993": "🇹🇲", "992": "🇹🇯",
    "977": "🇳🇵", "976": "🇲🇳", "975": "🇧🇹", "974": "🇶🇦", "973": "🇧🇭", "972": "🇮🇱",
    "971": "🇦🇪", "970": "🇵🇸", "968": "🇴🇲", "967": "🇾🇪", "966": "🇸🇦", "965": "🇰🇼",
    "964": "🇮🇶", "963": "🇸🇾", "962": "🇯🇴", "961": "🇱🇧", "960": "🇲🇻", "886": "🇹🇼",
    "880": "🇧🇩", "856": "🇱🇦", "855": "🇰🇭", "853": "🇲🇴", "852": "🇭🇰", "850": "🇰🇵",
    "269": "🇰🇲", "268": "🇸🇿", "267": "🇧🇼", "266": "🇱🇸", "265": "🇲🇼", "264": "🇳🇦",
    "263": "🇿🇼", "262": "🇷🇪", "261": "🇲🇬", "260": "🇿🇲", "258": "🇲🇿", "257": "🇧🇮",
    "256": "🇺🇬", "255": "🇹🇿", "254": "🇰🇪", "253": "🇩🇯", "252": "🇸🇴", "251": "🇪🇹",
    "250": "🇷🇼", "249": "🇸🇩", "248": "🇸🇨", "246": "🇮🇴", "245": "🇬🇼", "244": "🇦🇴",
    "243": "🇨🇩", "242": "🇨🇬", "241": "🇬🇦", "240": "🇬🇶", "239": "🇸🇹", "238": "🇨🇻",
    "237": "🇨🇲", "236": "🇨🇫", "235": "🇹🇩", "234": "🇳🇬", "233": "🇬🇭", "232": "🇸🇱",
    "231": "🇱🇷", "230": "🇲🇺", "229": "🇧🇯", "228": "🇹🇬", "227": "🇳🇪", "226": "🇧🇫",
    "225": "🇨🇮", "224": "🇬🇳", "223": "🇲🇱", "222": "🇲🇷", "221": "🇸🇳", "220": "🇬🇲",
    "218": "🇱🇾", "216": "🇹🇳", "213": "🇩🇿", "212": "🇲🇦", "211": "🇸🇸",
    "98": "🇮🇷", "95": "🇲🇲", "94": "🇱🇰", "93": "🇦🇫", "92": "🇵🇰", "91": "🇮🇳", "90": "🇹🇷",
    "86": "🇨🇳", "84": "🇻🇳", "82": "🇰🇷", "81": "🇯🇵", "66": "🇹🇭", "65": "🇸🇬", "64": "🇳🇿",
    "63": "🇵🇭", "62": "🇮🇩", "61": "🇦🇺", "60": "🇲🇾", "58": "🇻🇪", "57": "🇨🇴", "56": "🇨🇱",
    "55": "🇧🇷", "54": "🇦🇷", "53": "🇨🇺", "52": "🇲🇽", "51": "🇵🇪", "49": "🇩🇪", "48": "🇵🇱",
    "47": "🇳🇴", "46": "🇸🇪", "45": "🇩🇰", "44": "🇬🇧", "43": "🇦🇹", "41": "🇨🇭", "40": "🇷🇴",
    "39": "🇮🇹", "36": "🇭🇺", "34": "🇪🇸", "33": "🇫🇷", "32": "🇧🇪", "31": "🇳🇱", "30": "🇬🇷",
    "27": "🇿🇦", "20": "🇪🇬", "7": "🇷🇺", "1": "🇺🇸"
}

def get_country_flag(num_str):
    clean = re.sub(r'\D', '', str(num_str))
    for prefix in sorted(COUNTRY_DIAL_FLAGS.keys(), key=len, reverse=True):
        if clean.startswith(prefix):
            return COUNTRY_DIAL_FLAGS[prefix]
    return "🌍"

GLOBAL_BODY_EMOJIS = {
    "➖": "5870818207383686839", "🚫": "5334807341109908955", "📱": "5337132498965010628",
    "🔐": "5337255927735163754", "🎁": "5420396762189831222", "💰": "5190576863226933563",
    "🔑": "5353022963132174959", "📅": "5352585194295564660"
}

def render_body_text(text):
    if not text: return ""
    parts = re.split(r'(<tg-emoji.*?</tg-emoji>)', str(text))
    for i in range(len(parts)):
        if not parts[i].startswith('<tg-emoji'):
            for normal_emj, prem_id in GLOBAL_BODY_EMOJIS.items():
                if normal_emj in parts[i]:
                    parts[i] = parts[i].replace(normal_emj, f'<tg-emoji emoji-id="{prem_id}">{normal_emj}</tg-emoji>')
    return "".join(parts)

def send_tg_direct(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": str(chat_id), "text": render_body_text(text), "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    try:
        res = http_session.post(url, json=payload, timeout=8)
        if res.status_code == 429:
            time.sleep(res.json().get("parameters", {}).get("retry_after", 1))
            res = http_session.post(url, json=payload, timeout=8)
        if not res.json().get("ok"):
            payload["text"] = re.sub(r'<[^>]+>', '', payload.get("text", ""))
            payload.pop("parse_mode", None)
            http_session.post(url, json=payload, timeout=8)
    except Exception as e:
        print(f"Telegram Send Error: {e}")

def mask_number_for_group(number, owner_uid=None):
    clean = re.sub(r'\D', '', str(number))
    tag = f'<a href="tg://user?id={owner_uid}">USER</a>' if owner_uid else "USER"
    if len(clean) > 6: return f"+{clean[:3]}✦{tag}✦{clean[-3:]}"
    elif len(clean) > 2: return f"+{clean[:1]}✦{tag}✦{clean[-1:]}"
    return f"+{clean}"

def extract_exact_otp(message_text):
    if not message_text: return None
    raw = str(message_text).strip()

    burmese_m = re.search(r'အတည်ပြုနံပါတ်[\s:=]*(\d{4,12})', raw)
    if burmese_m: return burmese_m.group(1).strip()

    kw_match = re.search(r'(?:kod\s*weryfikacyjny|code\s*de\s*verification|verification\s*code|viber\s*code|your\s*code|otp|pin|is\s*your)[\s#:=]*(\d{4,12})', raw, re.I)
    if kw_match: return kw_match.group(1).strip()

    hash_match = re.search(r'#\s*(?:[^\d\n]*?)(\d{4,12})', raw, re.I)
    if hash_match: return hash_match.group(1).strip()

    pwd_match = re.search(r'(?:Password|Mot\s*de\s*passe|pass|pwd|رمز|کد)[\s:=]*([a-zA-Z0-9]{4,16})', raw, re.I)
    if pwd_match: return pwd_match.group(1).strip()

    digits_std = re.findall(r'\b\d{4,8}\b', raw)
    if digits_std: return digits_std[0].strip()

    digits_long = re.findall(r'\b\d{9,12}\b', raw)
    if digits_long: return digits_long[0].strip()

    fallback = re.search(r'\b[a-zA-Z0-9]{4,12}\b', raw)
    if fallback:
        val = fallback.group(0).strip()
        if val.upper() not in {"VERIFICATION", "PASSWORD", "VOTRE", "POUR", "AVEC", "INFO", "USER"}:
            return val
    return None

def detect_service_and_icon(text, sid=""):
    combined = f"{sid} {text}".upper()
    services = {
        "NEBAREX": ("⚡", "Nebarex"), "TIKTOK": ("🎵", "TikTok"), "MEGAPARI": ("🎰", "Megapari"),
        "BIZBET": ("⚡", "Bizbet"), "22BET": ("⚽", "22Bet"), "ASTEK": ("🎯", "Astekbet"),
        "1XBET": ("🎲", "1xBet"), "MELBET": ("🎯", "Melbet"), "VIBER": ("🟣", "Viber"), "UBER": ("🚗", "Uber")
    }
    for key, val in services.items():
        if key in combined: return val
    clean_sid = sid.strip().title() if sid.strip() else "SMS"
    return "📱", clean_sid

def detect_language(text):
    if not text: return "#EN"
    if any('\u1000' <= c <= '\u109f' for c in text): return "#MY"
    if any('\u0600' <= c <= '\u06ff' for c in text): return "#FA"
    if "kod weryfikacyjny" in text.lower(): return "#PL"
    if "de verification" in text.lower() or "mot de passe" in text.lower(): return "#FR"
    if any('\u10a0' <= c <= '\u10ff' for c in text): return "#GE"
    if any('\u0400' <= c <= '\u04ff' for c in text): return "#RU"
    return "#EN"

def generate_signature(num, dt_val, msg):
    msg_hash = hashlib.md5(str(msg).encode('utf-8')).hexdigest()[:10]
    return f"{num}_{dt_val}_{msg_hash}"

def find_number_owner_and_range(clean_num):
    owner_id = None
    range_name = ""
    rate = 1.0
    clean_digits = re.sub(r'\D', '', str(clean_num))

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                assigned = data.get("assigned_numbers", {})
                num_ranges = data.get("number_ranges", {})
                range_rates = data.get("range_rates", {})
                default_rate = float(data.get("default_otp_rate", 1.0))

                for stored_num, uid in assigned.items():
                    c_stored = re.sub(r'\D', '', str(stored_num))
                    if clean_digits == c_stored or (len(c_stored) >= 8 and clean_digits.endswith(c_stored[-8:])) or (len(clean_digits) >= 8 and c_stored.endswith(clean_digits[-8:])):
                        owner_id = uid
                        range_name = num_ranges.get(stored_num, "")
                        rate = float(range_rates.get(range_name, default_rate))
                        break
        except Exception as e:
            print(f"DB Read Error: {e}")

    return owner_id, range_name, rate

# ================= Safe Atomic User Database Write =================
def add_balance_strictly(uid, reward_amount):
    target_uid = str(uid).strip()
    today = datetime.now().strftime('%Y-%m-%d')
    reward = float(reward_amount)
    
    with file_lock:
        users = {}
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content: users = json.loads(content)
            except Exception:
                bak = f"{USERS_FILE}.bak"
                if os.path.exists(bak):
                    try:
                        with open(bak, "r", encoding="utf-8") as bf: users = json.load(bf)
                    except Exception: users = {}

        if target_uid not in users:
            users[target_uid] = {
                "user_id": target_uid, "username": "", "balance": 0.0,
                "today_earnings": 0.0, "total_earnings": 0.0, "last_active_date": today,
                "total_otps": 0, "referred_by": None, "registered_at": time.time()
            }

        user = users[target_uid]
        old_bal = float(user.get("balance", 0.0))
        old_today = float(user.get("today_earnings", 0.0))
        old_total = float(user.get("total_earnings", 0.0))

        if user.get("last_active_date") != today:
            old_today = 0.0
            user["last_active_date"] = today

        new_bal = round(old_bal + reward, 2)
        user["balance"] = new_bal
        user["today_earnings"] = round(old_today + reward, 2)
        user["total_earnings"] = round(old_total + reward, 2)
        user["total_otps"] = int(user.get("total_otps", 0)) + 1

        tmp = f"{USERS_FILE}.tmp"
        bak = f"{USERS_FILE}.bak"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(USERS_FILE):
                shutil.copy2(USERS_FILE, bak)
            os.replace(tmp, USERS_FILE)
            print(f"💰 [HADI SUCCESS] Added {reward:.2f} BDT to UID {target_uid}. Balance: {new_bal:.2f} BDT")
        except Exception as e:
            print(f"Write File Error: {e}")
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass

    return new_bal

def record_signature(sig):
    if len(processed_sms_signatures) >= MAX_SIGNATURES:
        oldest = processed_sms_signatures.popleft()
        signature_set.discard(oldest)
    processed_sms_signatures.append(sig)
    signature_set.add(sig)

def otp_queue_processor():
    while True:
        task = otp_task_queue.get()
        if not task: continue
        try:
            raw_number, raw_message, unique_dt, sid = task
            lines = [l.strip() for l in str(raw_number).splitlines() if l.strip()]
            num_digits = ""
            for l in reversed(lines):
                d = re.sub(r'\D', '', l)
                if len(d) >= 7:
                    num_digits = d
                    break

            if not num_digits or len(num_digits) < 7: continue

            sig = generate_signature(num_digits, unique_dt, raw_message)
            if sig in signature_set: continue

            record_signature(sig)

            extracted_otp = extract_exact_otp(raw_message)
            otp_code = extracted_otp if extracted_otp else "NONE"

            srv_icon, srv_name = detect_service_and_icon(raw_message, sid)
            country_flag = get_country_flag(num_digits)
            lang_code = detect_language(raw_message)
            current_time_str = datetime.now().strftime('%d %b, %I:%M %p')

            owner_id, range_name, otp_rate = find_number_owner_and_range(num_digits)
            masked_num = mask_number_for_group(num_digits, owner_uid=owner_id)

            print(f"🔥 HADI OTP -> +{num_digits} | Code: {otp_code} | Flag: {country_flag} | User: {owner_id}")

            group_card = f"╔ {srv_icon} {srv_name} {country_flag} {lang_code} [PAID]\n║ 📱 <code>{masked_num}</code>\n║ 🔐 <b>OTP:</b> <code>{otp_code}</code>\n╚ 📅 <i>{current_time_str}</i>"
            group_kb = {"inline_keyboard": [[{"text": f"🔑 {otp_code}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp_code}, "style": "success"}]]}
            send_tg_direct(TELEGRAM_GROUP_ID, group_card, group_kb)

            if owner_id:
                new_balance = add_balance_strictly(owner_id, otp_rate)
                user_card = f"╔ {srv_icon} {srv_name} {country_flag} {lang_code} [PAID]\n║ 📱 <code>+{num_digits}</code>\n║ 🔐 <b>OTP:</b> <code>{otp_code}</code>\n║ 🎁 <b>Reward:</b> <code>+{otp_rate:.2f} BDT</code>\n║ 💰 <b>Balance:</b> <code>{new_balance:.2f} BDT</code>\n╚ 📅 <i>{current_time_str}</i>"
                user_kb = {"inline_keyboard": [
                    [{"text": f"🔑 {otp_code}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp_code}, "style": "success"}],
                    [{"text": f"💰 Balance: {new_balance:.2f} BDT", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "balance_info", "style": "primary"}]
                ]}
                send_tg_direct(owner_id, user_card, user_kb)
        except Exception as e:
            print(f"Processing Error: {e}")
        finally:
            otp_task_queue.task_done()

def poll_hadi():
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {"token": HADI_API_TOKEN, "records": 40}

    try:
        res = http_session.get(HADI_API_URL, params=params, headers=headers, timeout=8)
        if res.status_code == 200 and res.json().get("status") == "success":
            for item in res.json().get("data", []):
                lines = [l.strip() for l in str(item.get("num", "")).splitlines() if l.strip()]
                num = ""
                for l in reversed(lines):
                    d = re.sub(r'\D', '', l)
                    if len(d) >= 7:
                        num = d
                        break
                sig = generate_signature(num, str(item.get("dt", "")), str(item.get("message", "")))
                record_signature(sig)
        print("✅ HADI Zero-Drop Safe Engine Synchronized!")
    except Exception as e:
        print(f"Sync Error: {e}")

    while True:
        try:
            res = http_session.get(HADI_API_URL, params=params, headers=headers, timeout=8)
            if res.status_code == 200 and res.json().get("status") == "success":
                for item in reversed(res.json().get("data", [])):
                    otp_task_queue.put((str(item.get("num", "")), str(item.get("message", "")), str(item.get("dt", "")), str(item.get("cli", ""))))
            elif res.status_code == 429:
                time.sleep(2.0)
        except Exception as e:
            time.sleep(1.0)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    print("🚀 HADI Live Safe Engine Starting...")
    threading.Thread(target=otp_queue_processor, daemon=True).start()
    poll_hadi()
