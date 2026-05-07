import os
import re
import time
import base64
import secrets
import string
import subprocess

from datetime import datetime, timedelta

import requests

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

AES_KEY = os.getenv(
    "AES_KEY",
    "THIS_IS_MY_32_BYTE_SECRET_KEY!"
).encode()

def safe_print(message):
    print(f"[INFO] {message}")

def generate_credentials():

    username = "rdp_" + ''.join(
        secrets.choice(
            string.ascii_lowercase +
            string.digits
        )
        for _ in range(8)
    )

    password = ''.join(
        secrets.choice(
            string.ascii_letters +
            string.digits +
            "!@#$%^&*"
        )
        for _ in range(16)
    )

    return username, password

def validate_cloudflare_url(url):

    pattern = r"^https:\/\/[a-zA-Z0-9\-]+\.trycloudflare\.com$"

    return bool(re.match(pattern, url))

def encrypt_data(data):

    key = AES_KEY.ljust(32, b'\0')[:32]

    iv = get_random_bytes(16)

    cipher = AES.new(
        key,
        AES.MODE_CBC,
        iv
    )

    encrypted = cipher.encrypt(
        pad(
            data.encode(),
            AES.block_size
        )
    )

    return base64.b64encode(
        iv + encrypted
    ).decode()

def send_to_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:
        safe_print("Telegram secrets غير موجودة")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            safe_print("تم إرسال الرسالة")
        else:
            safe_print(
                f"Telegram Error: {response.text}"
            )

    except Exception as e:

        safe_print(
            f"Request Error: {e}"
        )

def check_windows():

    if os.name != "nt":
        return False

    try:

        result = subprocess.run(
            "systeminfo",
            shell=True,
            capture_output=True,
            text=True
        )

        return (
            "Microsoft" in result.stdout
            and
            "Windows" in result.stdout
        )

    except:
        return False

def create_rdp_user(username, password):

    commands = [

        [
            "net",
            "user",
            username,
            password,
            "/add"
        ],

        [
            "net",
            "localgroup",
            "Remote Desktop Users",
            username,
            "/add"
        ]
    ]

    for command in commands:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            raise Exception(
                result.stderr
            )

    safe_print(
        f"تم إنشاء المستخدم {username}"
    )

def delete_rdp_user(username):

    result = subprocess.run(
        [
            "net",
            "user",
            username,
            "/delete"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:

        safe_print(
            f"تم حذف المستخدم {username}"
        )

    else:

        safe_print(
            result.stderr
        )

def main():

    safe_print("بدء التشغيل")

    if not check_windows():

        safe_print("هذا ليس Windows")
        return

    try:

        hours = float(
            input("مدة الجلسة بالساعات: ")
        )

        if hours <= 0:
            raise ValueError

    except:

        safe_print("مدة غير صالحة")
        return

    user, pwd = generate_credentials()

    trycloudflare_link = input(
        "رابط TryCloudflare: "
    ).strip()

    if not validate_cloudflare_url(
        trycloudflare_link
    ):

        safe_print(
            "الرابط غير صالح"
        )

        return

    try:

        create_rdp_user(
            user,
            pwd
        )

    except Exception as e:

        safe_print(
            f"خطأ إنشاء المستخدم: {e}"
        )

        return

    encrypted_user = encrypt_data(user)

    encrypted_pwd = encrypt_data(pwd)

    encrypted_link = encrypt_data(
        trycloudflare_link
    )

    end_time = (
        datetime.now() +
        timedelta(hours=hours)
    )

    report = f"""
🔐 RDP SESSION

👤 USER:
{encrypted_user}

🔑 PASSWORD:
{encrypted_pwd}

🌐 LINK:
{encrypted_link}

⏳ DURATION:
{hours} HOURS

🕒 END:
{end_time}
"""

    send_to_telegram(report)

    safe_print("تم بدء الجلسة")

    try:

        time.sleep(hours * 3600)

    except KeyboardInterrupt:

        safe_print("تم الإيقاف")

    finally:

        delete_rdp_user(user)

        send_to_telegram(
            f"⏰ انتهت الجلسة: {user}"
        )

if __name__ == "__main__":
    main()
