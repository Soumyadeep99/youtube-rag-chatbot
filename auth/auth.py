import random
import string
import bcrypt
from datetime import datetime, timedelta

from db.database import (
    create_user,
    get_user_by_email,
    mark_user_verified,
    save_otp,
    get_otp,
    delete_otp
)
from auth.email import send_otp_email


# ---------------------------
# Password Hashing
# ---------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8")
    )


# ---------------------------
# OTP Generation
# ---------------------------

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


# ---------------------------
# Auth Actions
# ---------------------------

def register_user(email: str, password: str) -> dict:
    """
    Registers a new user and sends OTP for verification.
    Returns {"success": bool, "message": str}
    """
    existing = get_user_by_email(email)

    if existing:
        if existing["is_verified"]:
            return {"success": False, "message": "Email already registered. Please log in."}
        else:
            # Resend OTP for unverified account
            otp = generate_otp()
            expires_at = datetime.now() + timedelta(minutes=10)
            save_otp(email, otp, expires_at)
            sent = send_otp_email(email, otp)

            if not sent:
                return {"success": False, "message": "Failed to send OTP. Check your email config."}

            return {"success": True, "message": "OTP resent. Please verify your email."}

    hashed = hash_password(password)
    create_user(email, hashed)

    otp = generate_otp()
    expires_at = datetime.now() + timedelta(minutes=10)
    save_otp(email, otp, expires_at)
    sent = send_otp_email(email, otp)

    if not sent:
        return {"success": False, "message": "Account created but failed to send OTP. Check your email config."}

    return {"success": True, "message": "Account created. Please check your email for the OTP."}


def verify_otp_code(email: str, entered_otp: str) -> dict:
    """
    Verifies the OTP entered by the user.
    Returns {"success": bool, "message": str}
    """
    record = get_otp(email)

    if record is None:
        return {"success": False, "message": "No OTP found. Please register again."}

    if datetime.now() > record["expires_at"]:
        delete_otp(email)
        return {"success": False, "message": "OTP expired. Please register again."}

    if entered_otp.strip() != record["otp"]:
        return {"success": False, "message": "Incorrect OTP. Please try again."}

    mark_user_verified(email)
    delete_otp(email)

    return {"success": True, "message": "Email verified successfully!"}


def login_user(email: str, password: str) -> dict:
    """
    Logs in a verified user.
    Returns {"success": bool, "message": str, "user": dict | None}
    """
    user = get_user_by_email(email)

    if user is None:
        return {"success": False, "message": "No account found with this email.", "user": None}

    if not user["is_verified"]:
        return {"success": False, "message": "Email not verified. Please register and verify first.", "user": None}

    if not verify_password(password, user["hashed_password"]):
        return {"success": False, "message": "Incorrect password.", "user": None}

    return {"success": True, "message": "Login successful!", "user": user}