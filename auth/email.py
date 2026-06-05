import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Sends an OTP verification email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    subject = "Your YouTube RAG Chatbot OTP"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 24px;">
        <h2 style="color: #FF0000;">🎥 YouTube RAG Chatbot</h2>
        <p>Your one-time verification code is:</p>
        <div style="
          font-size: 36px;
          font-weight: bold;
          letter-spacing: 8px;
          color: #1a1a1a;
          background: #f4f4f4;
          padding: 16px 24px;
          border-radius: 8px;
          display: inline-block;
          margin: 16px 0;
        ">
          {otp}
        </div>
        <p style="color: #555;">This code expires in <strong>10 minutes</strong>.</p>
        <p style="color: #999; font-size: 12px;">
          If you did not request this, please ignore this email.
        </p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email Error] {e}")
        return False