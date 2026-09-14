import sys
from types import ModuleType
import re

# Python 3.12+ distutils compatibility fix for undetected_chromedriver
try:
    from distutils.version import LooseVersion
except (ImportError, ModuleNotFoundError):
    distutils_mod = ModuleType('distutils')
    distutils_version_mod = ModuleType('distutils.version')
    
    class LooseVersion:
        def __init__(self, vstring=None):
            self.vstring = str(vstring) if vstring else ""
        def __str__(self):
            return self.vstring
        def _parse(self, v):
            return [int(x) if x.isdigit() else x for x in re.findall(r'\d+|[a-zA-Z]+', v)]
        def __lt__(self, other):
            return self._parse(self.vstring) < self._parse(str(other))
        def __le__(self, other):
            return self._parse(self.vstring) <= self._parse(str(other))
        def __gt__(self, other):
            return self._parse(self.vstring) > self._parse(str(other))
        def __ge__(self, other):
            return self._parse(self.vstring) >= self._parse(str(other))
        def __eq__(self, other):
            return self._parse(self.vstring) == self._parse(str(other))
        def __ne__(self, other):
            return self._parse(self.vstring) != self._parse(str(other))

    distutils_version_mod.LooseVersion = LooseVersion
    distutils_mod.version = distutils_version_mod
    sys.modules['distutils'] = distutils_mod
    sys.modules['distutils.version'] = distutils_version_mod

import os
import json
import time
import random
import shutil
import requests
import threading
import subprocess
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from tkinter import messagebox
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException

BOT_TOKEN = "8867778383:AAGKHcZdr4mA7bX2Tl4AO_LOrqjelOlTqt4"
TELEGRAM_GROUP_ID = "-1004318007695"

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "bot_data.json")
USERS_FILE = os.path.join(BASE_DIR, "users_db.json")

TARGET_URL = "https://www.ivasms.com/portal/live/my_sms"
LOGIN_EMAIL = "maiologgmail.com"
LOGIN_PASSWORD = "Abdi20@"

CHROME_PROFILE_DIR = os.path.expanduser('~/sadi/IrysNode')
CHROME_PROFILE = os.path.join(CHROME_PROFILE_DIR, 'chrome_profile')
os.makedirs(CHROME_PROFILE, exist_ok=True)

CHECK_INTERVAL = 0.2
processed_sms_ids = set()

tg_executor = ThreadPoolExecutor(max_workers=35)
db_lock = threading.Lock()

COUNTRY_DIAL_FLAGS = {
    "1242": "🇧🇸", "1246": "🇧🇧", "1264": "🇦🇮", "1268": "🇦🇬", "1284": "🇻🇬",
    "1340": "🇻🇮", "1345": "🇰🇾", "1441": "🇧🇲", "1473": "🇬🇩", "1649": "🇹🇨", "1664": "🇲🇸",
    "1670": "🇲🇵", "1671": "🇬🇺", "1684": "🇦🇸", "1721": "🇸🇽", "1758": "🇱🇨", "1767": "🇩🇲",
    "1784": "🇻🇨", "1787": "🇵🇷", "1809": "🇩🇴", "1829": "🇩🇴", "1849": "🇩🇴", "1868": "🇹🇹",
    "1869": "🇰🇳", "1876": "🇯🇲", "1939": "🇵🇷",
    "995": "🇬🇪", "996": "🇰🇬", "998": "UZ", "994": "AZ", "993": "TM", "992": "TJ",
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

def _send_tg_worker(chat_id, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    headers = {"User-Agent": "Mozilla/5.0", "Connection": "close"}
    for _ in range(4):
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=6)
            data = res.json()
            if data.get("ok"): return
            elif data.get("error_code") == 429:
                time.sleep(data.get("parameters", {}).get("retry_after", 1))
                continue
            else:
                payload["text"] = re.sub(r'<[^>]+>', '', payload.get("text", ""))
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, headers=headers, timeout=6)
                return
        except Exception:
            time.sleep(0.3)

def send_telegram_msg_async(chat_id, text, reply_markup=None):
    payload = {"chat_id": str(chat_id), "text": render_body_text(text), "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    tg_executor.submit(_send_tg_worker, chat_id, payload)

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

def find_number_owner_fast(clean_digits):
    clean_digits = re.sub(r'\D', '', str(clean_digits))
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                assigned = data.get("assigned_numbers", {})
                num_ranges = data.get("number_ranges", {})
                range_rates = data.get("range_rates", {})
                default_rate = float(data.get("default_otp_rate", 5.0))

                for stored_num, uid in assigned.items():
                    c_stored = re.sub(r'\D', '', str(stored_num))
                    if clean_digits == c_stored or (len(c_stored) >= 8 and clean_digits.endswith(c_stored[-8:])) or (len(clean_digits) >= 8 and c_stored.endswith(clean_digits[-8:])):
                        r_name = num_ranges.get(stored_num, "")
                        rate = float(range_rates.get(r_name, default_rate))
                        return uid, r_name, rate
        except Exception:
            pass
    return None, "", 5.0

# ================= Financial & Live Range Helpers =================
def calculate_weekly_revenue(users_file):
    if not os.path.exists(users_file):
        return 0.0, 0.0
    try:
        with open(users_file, "r", encoding="utf-8") as f:
            users = json.load(f)
        
        total_all_time = 0.0
        today_total = 0.0
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        for uid, data in users.items():
            total_all_time += float(data.get("total_earnings", 0.0))
            if data.get("last_active_date") == today_str:
                today_total += float(data.get("today_earnings", 0.0))
                
        return today_total, total_all_time
    except Exception:
        return 0.0, 0.0

def get_user_live_financials(uid):
    uid_str = str(uid).strip()
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
                if uid_str in users:
                    u_data = users[uid_str]
                    return (
                        float(u_data.get("balance", 0.0)),
                        float(u_data.get("today_earnings", 0.0)),
                        float(u_data.get("total_earnings", 0.0)),
                        int(u_data.get("total_otps", 0))
                    )
        except Exception:
            pass
    return 0.0, 0.0, 0.0, 0.0

def add_balance_fast(uid, reward_amount):
    uid_str = str(uid).strip()
    today = datetime.now().strftime('%Y-%m-%d')
    reward = float(reward_amount)

    with db_lock:
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

        if uid_str not in users:
            users[uid_str] = {
                "user_id": uid_str, "username": "", "balance": 0.0,
                "today_earnings": 0.0, "total_earnings": 0.0, "last_active_date": today,
                "total_otps": 0, "today_otps": 0, "referred_by": None, "registered_at": time.time()
            }

        user = users[uid_str]
        if user.get("last_active_date") != today:
            user["today_earnings"] = 0.0
            user["today_otps"] = 0
            user["last_active_date"] = today

        old_bal = float(user.get("balance", 0.0))
        new_bal = round(old_bal + reward, 2)

        user["balance"] = new_bal
        user["today_earnings"] = round(float(user.get("today_earnings", 0.0)) + reward, 2)
        user["total_earnings"] = round(float(user.get("total_earnings", 0.0)) + reward, 2)
        user["total_otps"] = int(user.get("total_otps", 0)) + 1
        user["today_otps"] = int(user.get("today_otps", 0)) + 1

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
            print(f"💰 [IVAS SUCCESS] Added {reward:.2f} BDT to UID {uid_str}. Balance: {new_bal:.2f} BDT")
        except Exception as e:
            print(f"IvaSMS Write Error: {e}")
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass

        return new_bal

class IvaSMSScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IvaSMS Scalable Monitor (Anti-Redirect & Captcha Safe)")
        self.root.geometry("670x720")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.driver = None
        self.monitoring = False
        self.sms_count = 0
        self.last_otp_time = time.time()
        self.idle_refresh_seconds = 300

        self.title_label = ctk.CTkLabel(root, text="IvaSMS Live Monitor Engine (Anti-Redirect)", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)

        self.stats_frame = ctk.CTkFrame(root)
        self.stats_frame.pack(pady=5, padx=20, fill="x")
        
        self.live_rev_lbl = ctk.CTkLabel(self.stats_frame, text="📅 Today Rev: 0.00 BDT | 📊 Weekly Range: Active", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00ffcc")
        self.live_rev_lbl.pack(pady=6)

        self.btn_frame = ctk.CTkFrame(root)
        self.btn_frame.pack(pady=5, padx=20, fill="x")

        self.start_browser_btn = ctk.CTkButton(self.btn_frame, text="🚀 Open Chrome & Login", command=self.start_browser, width=170)
        self.start_browser_btn.pack(side="left", padx=5, pady=8)

        self.start_mon_btn = ctk.CTkButton(self.btn_frame, text="📡 Start Monitoring", command=self.start_monitoring, state="disabled", width=170)
        self.start_mon_btn.pack(side="left", padx=5, pady=8)

        self.stop_btn = ctk.CTkButton(self.btn_frame, text="🛑 Stop", command=self.stop_monitoring, state="disabled", width=90)
        self.stop_btn.pack(side="left", padx=5, pady=8)

        self.setting_frame = ctk.CTkFrame(root)
        self.setting_frame.pack(pady=6, padx=20, fill="x")

        self.refresh_lbl = ctk.CTkLabel(self.setting_frame, text="⏱ Inactivity Auto-Refresh:", font=ctk.CTkFont(size=13, weight="bold"))
        self.refresh_lbl.pack(side="left", padx=8, pady=8)

        self.minute_options = ["1 Minute", "2 Minutes", "3 Minutes", "4 Minutes", "5 Minutes", "6 Minutes", "7 Minutes", "8 Minutes", "9 Minutes", "10 Minutes", "OFF"]
        self.dropdown = ctk.CTkOptionMenu(self.setting_frame, values=self.minute_options, command=self.on_dropdown_change, width=130)
        self.dropdown.set("5 Minutes")
        self.dropdown.pack(side="left", padx=5, pady=8)

        self.timer_display_lbl = ctk.CTkLabel(self.setting_frame, text="Next: 300s", text_color="orange")
        self.timer_display_lbl.pack(side="left", padx=10, pady=8)

        self.status_label = ctk.CTkLabel(root, text="Status: Ready to launch Chrome", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=4)

        self.counter_label = ctk.CTkLabel(root, text="Total SMS Processed: 0", text_color="green", font=ctk.CTkFont(size=16, weight="bold"))
        self.counter_label.pack(pady=2)

        self.log_box = ctk.CTkTextbox(root, width=620, height=210, font=("Consolas", 12))
        self.log_box.pack(pady=8, padx=20)
        self.log("Click 'Open Chrome & Login' -> Sign in -> Click 'Start Monitoring'")

        self.start_timer_updater()
        self.start_revenue_updater()

    def on_dropdown_change(self, choice):
        if choice == "OFF":
            self.idle_refresh_seconds = 0
            self.log("⏱ Auto-refresh has been DISABLED.")
            self.timer_display_lbl.configure(text="Disabled", text_color="gray")
        else:
            mins = int(choice.split()[0])
            self.idle_refresh_seconds = mins * 60
            self.last_otp_time = time.time()
            self.log(f"⏱ Auto-refresh set to: {mins} Minutes ({self.idle_refresh_seconds}s)")

    def start_timer_updater(self):
        def loop():
            while True:
                if self.monitoring:
                    if self.idle_refresh_seconds > 0:
                        elapsed = int(time.time() - self.last_otp_time)
                        remaining = max(0, self.idle_refresh_seconds - elapsed)
                        self.root.after(0, lambda r=remaining: self.timer_display_lbl.configure(text=f"Next in: {r}s", text_color="orange" if r > 30 else "red"))
                    else:
                        self.root.after(0, lambda: self.timer_display_lbl.configure(text="Disabled", text_color="gray"))
                time.sleep(1)
        threading.Thread(target=loop, daemon=True).start()

    def start_revenue_updater(self):
        def loop():
            while True:
                try:
                    today_rev, total_rev = calculate_weekly_revenue(USERS_FILE)
                    rev_text = f"📅 Today Rev: {today_rev:.2f} BDT | 📈 Total / Weekly Range Tracker: Active"
                    self.root.after(0, lambda t=rev_text: self.live_rev_lbl.configure(text=t))
                except Exception:
                    pass
                time.sleep(3)
        threading.Thread(target=loop, daemon=True).start()

    def log(self, text):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_box.insert("end", f"[{timestamp}] {text}\n")
        self.log_box.see("end")

    def find_chrome(self):
        paths = ["/usr/bin/google-chrome-stable", "/usr/bin/google-chrome", "/snap/bin/chromium", "/usr/bin/chromium-browser"]
        for p in paths:
            if os.path.exists(p): return p
        try:
            res = subprocess.run(['which', 'google-chrome-stable'], capture_output=True, text=True)
            if res.returncode == 0: return res.stdout.strip()
        except Exception: pass
        return None

    def get_chrome_version_main(self):
        chrome_bin = self.find_chrome()
        if chrome_bin:
            try:
                output = subprocess.check_output([chrome_bin, "--version"]).decode("utf-8")
                match = re.search(r'(\d+)\.', output)
                if match:
                    return int(match.group(1))
            except Exception:
                pass
        return 149

    def start_browser(self):
        try:
            self.status_label.configure(text="Status: Launching Chrome...", text_color="orange")
            cache_path = os.path.expanduser("~/.local/share/undetected_chromedriver")
            if os.path.exists(cache_path):
                try: shutil.rmtree(cache_path)
                except Exception: pass

            chrome_bin = self.find_chrome()
            options = uc.ChromeOptions()
            if chrome_bin:
                options.binary_location = chrome_bin

            options.add_argument("--start-maximized")
            options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-popup-blocking")

            v_main = self.get_chrome_version_main()
            self.log(f"Detected Chrome Major Version: {v_main}")

            try:
                self.driver = uc.Chrome(options=options, version_main=v_main)
            except Exception:
                self.driver = uc.Chrome(options=options, version_main=149)

            self.driver.get(TARGET_URL)
            time.sleep(4)

            for _ in range(10):
                title = self.driver.title.lower()
                if "just a moment" in title or "checking your browser" in title:
                    self.log("🛡 Cloudflare Verification Active. Bypassing...")
                    time.sleep(2)
                else:
                    break

            try:
                e_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input[name="username"]')
                p_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"], input[name="password"]')
                e_field.clear()
                e_field.send_keys(LOGIN_EMAIL)
                p_field.clear()
                p_field.send_keys(LOGIN_PASSWORD)
                self.log("Credentials auto-filled. Complete sign in.")
            except Exception:
                pass

            self.status_label.configure(text="Chrome ready. Sign in and start monitoring", text_color="green")
            self.start_mon_btn.configure(state="normal")
            self.start_browser_btn.configure(state="disabled")
        except Exception as e:
            self.log(f"Error starting Chrome: {e}")
            self.status_label.configure(text="Failed to open Chrome", text_color="red")
            messagebox.showerror("Error", f"Failed to start Chrome:\n{e}")

    def start_monitoring(self):
        if not self.driver: return
        self.monitoring = True
        self.last_otp_time = time.time()
        self.status_label.configure(text="Monitoring Active - Zero Drop Mode", text_color="green")
        self.start_mon_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log("Live SMS monitor started.")
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def stop_monitoring(self):
        self.monitoring = False
        self.status_label.configure(text="Monitoring Stopped", text_color="red")
        self.start_mon_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.log("Monitoring stopped.")

    def check_idle_and_refresh(self):
        if self.idle_refresh_seconds <= 0: return
        current_time = time.time()
        if (current_time - self.last_otp_time) >= self.idle_refresh_seconds:
            self.last_otp_time = time.time()
            try:
                self.log("🔄 Inactivity detected. Executing session-safe reload...")
                cur_url = self.driver.current_url.lower()
                if "portal/live/my_sms" not in cur_url:
                    self.log("⚠️ Redirect detected! Returning directly to Live SMS URL...")
                    self.driver.get(TARGET_URL)
                    time.sleep(2.5)
                    return

                reloaded = self.driver.execute_script("""
                    if (window.jQuery) {
                        if (jQuery.fn.dataTable && jQuery.fn.dataTable.isDataTable('table')) {
                            jQuery('table').DataTable().ajax.reload(null, false);
                            return true;
                        }
                        if (jQuery('.table').length > 0) {
                            jQuery('.table').trigger('reload');
                        }
                    }
                    return false;
                """)

                if reloaded:
                    self.log("⚡ In-place Table AJAX successfully reloaded (Session Preserved).")
                    return

                btn_clicked = False
                reload_icons = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='reload'], .fa-sync, .fa-refresh, i.fa-repeat, button[title*='refresh']")
                for btn in reload_icons:
                    if btn.is_displayed():
                        try:
                            self.driver.execute_script("arguments[0].click();", btn)
                            btn_clicked = True
                            self.log("🔘 Portal Live Reload button triggered.")
                            break
                        except Exception: pass

                if not btn_clicked:
                    self.driver.get(TARGET_URL)
                    self.log("🌐 Navigated directly to TARGET_URL.")

                time.sleep(2)
            except Exception as e:
                self.log(f"⚠️ Safe reload notice: {e}")

    def ensure_correct_url(self):
        try:
            cur_url = self.driver.current_url
            if cur_url and "portal/live/my_sms" not in cur_url.lower():
                if "ivasms.com" in cur_url.lower() and "portal/live/my_sms" not in cur_url.lower():
                    self.log(f"⚠️ Wrong page detected ({cur_url}). Redirecting back to Live SMS...")
                    self.driver.get(TARGET_URL)
                    time.sleep(2)
        except Exception:
            pass

    def process_table_row(self, row):
        try:
            cols = row.find_elements(By.TAG_NAME, "td")
            if not cols or len(cols) < 3: return

            col_live_sms = cols[0].text.strip()
            col_sid = cols[1].text.strip() if len(cols) > 1 else ""
            row_full_text = row.text.upper()
            is_paid = "PAID" in row_full_text and "UNPAID" not in row_full_text

            msg_content = cols[-1].text.strip()
            if not msg_content or len(msg_content) < 3: return

            lines = [l.strip() for l in col_live_sms.splitlines() if l.strip()]
            clean_num = ""
            for l in reversed(lines):
                digits = re.sub(r'\D', '', l)
                if len(digits) >= 7:
                    clean_num = digits
                    break

            if not clean_num or len(clean_num) < 7: return

            extracted_otp = extract_exact_otp(msg_content)
            if not is_paid and not extracted_otp: return
            otp = extracted_otp if extracted_otp else "NONE"

            msg_unique_key = f"{clean_num}_{otp}_{hash(msg_content)}"
            if msg_unique_key in processed_sms_ids: return

            processed_sms_ids.add(msg_unique_key)
            if len(processed_sms_ids) > 10000: processed_sms_ids.clear()

            self.last_otp_time = time.time()

            srv_icon, srv_name = detect_service_and_icon(msg_content, col_sid)
            country_flag = get_country_flag(clean_num)
            lang_code = detect_language(msg_content)
            status_tag = "PAID" if is_paid else "UNPAID"

            owner_id, range_name, otp_rate = find_number_owner_fast(clean_num)

            self.sms_count += 1
            self.counter_label.configure(text=f"Total SMS Processed: {self.sms_count}")
            self.log(f"🔥 +{clean_num} | OTP: {otp} | [{status_tag}] | {srv_name} | {country_flag}")

            safe_sms_text = msg_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            masked_num = mask_number_for_group(clean_num, owner_uid=owner_id)
            group_card = (
                f"╔ {srv_icon} {srv_name} {country_flag} {lang_code} [{status_tag}]\n"
                f"╠ 📱 <code>{masked_num}</code>\n"
                f"╚ 💬 <b>MS :</b>\n<code>{safe_sms_text}</code>"
            )
            group_kb = {"inline_keyboard": [[{"text": f"🔑 {otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]}
            send_telegram_msg_async(TELEGRAM_GROUP_ID, group_card, group_kb)

            if owner_id:
                if not is_paid:
                    self.log(f"🚫 Skipped User Delivery for +{clean_num} (UNPAID).")
                    return

                new_balance = add_balance_fast(owner_id, otp_rate)
                u_bal, u_today, u_total, u_otps = get_user_live_financials(owner_id)
                
                user_card = (
                    f"╔ {srv_icon} {srv_name} {country_flag} {lang_code} [PAID]\n"
                    f"╠ 📱 <code>+{clean_num}</code>\n"
                    f"╠ 🎁 <b>Reward:</b> <code>+{otp_rate:.2f} BDT</code>\n"
                    f"╠ 💰 <b>Live Balance:</b> <code>{u_bal:.2f} BDT</code>\n"
                    f"╠ 📊 <b>Today Earn:</b> <code>{u_today:.2f} BDT</code>\n"
                    f"╚ 💬 <b>MS :</b>\n<code>{safe_sms_text}</code>"
                )
                user_kb = {"inline_keyboard": [
                    [{"text": f"🔑 {otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}],
                    [{"text": f"💰 Balance: {u_bal:.2f} BDT", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "balance_info", "style": "primary"}]
                ]}
                send_telegram_msg_async(owner_id, user_card, user_kb)
                self.log(f"✅ User ID {owner_id} credited (Bal: {new_balance:.2f} BDT)")
            else:
                self.log(f"ℹ️ Unassigned Number: +{clean_num}")

        except Exception as e:
            self.log(f"Row error: {e}")

    def monitor_loop(self):
        while self.monitoring:
            try:
                self.ensure_correct_url()
                self.check_idle_and_refresh()
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
                for r in rows:
                    try: self.process_table_row(r)
                    except StaleElementReferenceException: continue
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                err_msg = str(e).lower()
                if "no such window" in err_msg or "target window already closed" in err_msg or "invalid session id" in err_msg:
                    self.log("🛑 Browser closed.")
                    self.root.after(0, self.stop_monitoring)
                    break
                time.sleep(0.5)

    def on_close(self):
        self.monitoring = False
        if self.driver:
            try: self.driver.quit()
            except Exception: pass
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = IvaSMSScraperApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
