import re
from typing import List, Tuple

EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
PHONE_PATTERN = re.compile(r"^\+?[\d\s\-().]{10,20}$")


def _digit_count(value: str) -> int:
    return sum(ch.isdigit() for ch in value)


def validate_email(email: str) -> Tuple[bool, str]:
    email = (email or "").strip()
    if not email:
        return False, "Email is required"
    if "@" not in email or email.count("@") != 1:
        return False, "Enter a valid email address (example: name@company.com)"
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        return False, "Enter a complete email address with a valid domain"
    if not EMAIL_PATTERN.match(email):
        return False, "Enter a valid email address (example: name@company.com)"
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    phone = (phone or "").strip()
    if not phone:
        return False, "Phone number is required"
    digits = _digit_count(phone)
    if digits < 10:
        return False, "Enter a complete phone number with at least 10 digits"
    if digits > 15:
        return False, "Phone number is too long (maximum 15 digits)"
    if not PHONE_PATTERN.match(phone):
        return False, "Enter a valid phone number (digits, spaces, +, -, or parentheses only)"
    return True, ""


def validate_personal_contact(email: str, phone: str) -> List[str]:
    errors = []
    email_ok, email_msg = validate_email(email)
    if not email_ok:
        errors.append(email_msg)
    phone_ok, phone_msg = validate_phone(phone)
    if not phone_ok:
        errors.append(phone_msg)
    return errors
