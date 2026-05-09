import os
import httpx
from dotenv import load_dotenv

load_dotenv()

EMAILJS_SERVICE_ID  = os.getenv("EMAILJS_SERVICE_ID",  "service_t8mya7a")
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "template_o4szglj")
EMAILJS_PUBLIC_KEY  = os.getenv("EMAILJS_PUBLIC_KEY",  "W_14FKnRGUjpZg6IZ")
EMAILJS_PRIVATE_KEY = os.getenv("EMAILJS_PRIVATE_KEY", "")
APP_BASE_URL        = os.getenv("APP_BASE_URL", "http://localhost:8501")


def send_verification_email(to_email: str, token: str):
    """
    Send verification email via EmailJS HTTP API.
    Works on Render free tier — pure HTTPS, no SMTP ports.
    Free tier: 200 emails/month.
    """
    if not EMAILJS_PRIVATE_KEY:
        raise RuntimeError(
            "EMAILJS_PRIVATE_KEY not set. Go to EmailJS → Account → API Keys "
            "→ Private Key and add it to your Render environment variables."
        )

    verify_url = f"{APP_BASE_URL}/?verify={token}"

    response = httpx.post(
        "https://api.emailjs.com/api/v1.0/email/send",
        headers={"Content-Type": "application/json"},
        json={
            "service_id":  EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id":     EMAILJS_PUBLIC_KEY,
            "accessToken": EMAILJS_PRIVATE_KEY,
            "template_params": {
                "to_email":   to_email,
                "verify_url": verify_url
            }
        },
        timeout=15
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"EmailJS error {response.status_code}: {response.text}"
        )