import requests
from db_helper import get_setting
from dotenv import load_dotenv
import os
from pathlib import Path

class SmsNotifier:
    def __init__(self):
        # بارگذاری متغیرها از فایل .env
        load_dotenv()
        self.api_key = os.getenv("IPPANEL_API_KEY")
        self.from_number = os.getenv("IPPANEL_FROM_NUMBER")
        self.pattern_code = os.getenv("IPPANEL_PATTERN_CODE")
        self.api_url = "http://edge.ippanel.com/v1/api/send"
        
        # مسیر مطمئن برای ذخیره لاگ (همان مسیر main.py)
        self.log_dir = Path.home() / "AppData" / "Local" / "Amoozeshgah"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "error.log"

    def send_renew_term_notification(self, student_name, phone_number, class_name):
        if get_setting("sms_enabled", "فعال") == "غیرفعال":
            print("ℹ️ ارسال پیامک غیرفعال است.")
            return

        # تبدیل شماره به فرمت +98
        if phone_number.startswith("0"):
            recipient = "+98" + phone_number[1:]
        elif phone_number.startswith("9"):
            recipient = "+98" + phone_number
        else:
            recipient = phone_number

        params = {
            "student_name": student_name,
            "class_name": class_name
        }

        data = {
            "sending_type": "pattern",
            "from_number": self.from_number,
            "code": self.pattern_code,
            "recipients": [recipient],
            "params": params
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization":self.api_key
        }

        response = requests.post(self.api_url, headers=headers, json=data)

        if response.status_code != 200:
            error_message = (
                f"ارسال پیامک برای {student_name} ({phone_number}) با خطا مواجه شد:\n"
                f"کد وضعیت: {response.status_code}\n"
                f"متن خطا: {response.text}"
            )
            # نوشتن در فایل لاگ (مسیر مطمئن)
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"[SMS ERROR] {error_message}\n")
            except Exception as e:
                print(f"❌ خطا در نوشتن لاگ: {e}")
            raise Exception(error_message)

        print(f"✅ پیامک برای {student_name} ارسال شد.")