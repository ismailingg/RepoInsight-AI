import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_EMAIL    = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
APP_BASE_URL  = os.getenv("APP_BASE_URL", "http://localhost:8501")


def send_verification_email(to_email: str, token: str):
    """
    Send an account verification email with a one-click link.
    The link points to the Streamlit app with ?verify=<token> in the URL,
    which the frontend intercepts and calls POST /auth/verify.

    Requires in .env:
        SMTP_EMAIL     = your Gmail address
        SMTP_PASSWORD  = your Gmail App Password (not your login password)
        APP_BASE_URL   = http://localhost:8501  (or your deployed URL)

    Gmail setup:
        1. Go to myaccount.google.com → Security → 2-Step Verification (enable it)
        2. Then go to myaccount.google.com → Security → App passwords
        3. Create an app password for "Mail" → copy the 16-char password
        4. Put that 16-char password in SMTP_PASSWORD (no spaces)
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP_EMAIL and SMTP_PASSWORD must be set in .env to send verification emails.\n"
            "See mailer.py docstring for Gmail setup instructions."
        )

    verify_url = f"{APP_BASE_URL}/?verify={token}"

    # ── HTML email body ──────────────────────────────────────────
    html = f"""
    <div style="background:#0a0a0a;padding:48px 0;font-family:'Courier New',monospace;">
      <div style="max-width:520px;margin:0 auto;background:#0f0f0f;border:1px solid #1e1e1e;
                  border-top:3px solid #ff5000;padding:40px;">

        <div style="font-size:22px;font-weight:800;color:#e8e8e8;letter-spacing:-0.03em;
                    margin-bottom:6px;">
          REPO<span style="color:#ff5000;">INSIGHT</span>
        </div>
        <div style="font-size:9px;color:#333;letter-spacing:0.22em;text-transform:uppercase;
                    margin-bottom:36px;">
          Codebase Intelligence
        </div>

        <div style="font-size:13px;color:#888;line-height:1.9;margin-bottom:32px;">
          Thanks for registering. Click the button below to verify your email address
          and activate your account.
        </div>

        <a href="{verify_url}"
           style="display:inline-block;background:#ff5000;color:#0a0a0a;
                  font-family:'Courier New',monospace;font-weight:700;font-size:13px;
                  letter-spacing:0.08em;text-transform:uppercase;text-decoration:none;
                  padding:14px 28px;">
          VERIFY EMAIL →
        </a>

        <div style="margin-top:32px;font-size:10px;color:#333;line-height:1.8;">
          This link expires in <span style="color:#666;">24 hours</span>.<br>
          If you didn't create this account, ignore this email.
        </div>

        <div style="margin-top:24px;padding-top:24px;border-top:1px solid #1a1a1a;
                    font-size:10px;color:#222;">
          Can't click the button? Copy this link:<br>
          <span style="color:#444;">{verify_url}</span>
        </div>
      </div>
    </div>
    """

    # Plain text fallback
    plain = (
        f"Verify your RepoInsight AI account:\n\n"
        f"{verify_url}\n\n"
        f"This link expires in 24 hours.\n"
        f"If you didn't create this account, ignore this email."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your RepoInsight AI account"
    msg["From"]    = f"RepoInsight AI <{SMTP_EMAIL}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())