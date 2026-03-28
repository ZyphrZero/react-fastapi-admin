import re
import secrets
import string
from typing import Dict, List, Union, Tuple, Optional

import bcrypt

from app.settings.config import settings


BCRYPT_MAX_PASSWORD_BYTES = 72
BOOTSTRAP_ADMIN_PASSWORD_LENGTH = 12
BOOTSTRAP_ADMIN_PASSWORD_SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"
BOOTSTRAP_ADMIN_PASSWORD_CHARACTERS = string.digits + BOOTSTRAP_ADMIN_PASSWORD_SYMBOLS


def get_password_policy() -> Dict[str, Union[int, bool]]:
    return {
        "password_min_length": settings.PASSWORD_MIN_LENGTH,
        "password_require_uppercase": settings.PASSWORD_REQUIRE_UPPERCASE,
        "password_require_lowercase": settings.PASSWORD_REQUIRE_LOWERCASE,
        "password_require_digits": settings.PASSWORD_REQUIRE_DIGITS,
        "password_require_special": settings.PASSWORD_REQUIRE_SPECIAL,
    }


def validate_bcrypt_password_length(password: str) -> Tuple[bool, str]:
    """
    Validate bcrypt's maximum supported password byte length.

    Starting with bcrypt 5.0.0, passwords longer than 72 bytes raise ValueError directly.
    We perform a single pre-check here to avoid turning a hashing failure into a 500 response.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        return False, f"密码长度不能超过{BCRYPT_MAX_PASSWORD_BYTES}个字节"
    return True, ""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password.
    :param plain_password: Plain-text password.
    :param hashed_password: Hashed password.
    :return: Verification result.
    """
    try:
        # Convert strings to bytes.
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Return the password hash.
    :param password: Plain-text password.
    :return: Hashed password.
    """
    is_valid, message = validate_bcrypt_password_length(password)
    if not is_valid:
        raise ValueError(message)

    # Generate a salt and hash the password.
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def generate_password(length: Optional[int] = None) -> str:
    """
    Generate a random password.
    :param length: Password length.
    :return: Random password.
    """
    min_length = settings.PASSWORD_MIN_LENGTH
    actual_length = length if length and length >= min_length else min_length

    # Determine the character set from the configured policy.
    characters = string.ascii_lowercase  # Base character set (lowercase letters).

    # Add character classes required by the current policy.
    if settings.PASSWORD_REQUIRE_UPPERCASE:
        characters += string.ascii_uppercase
    if settings.PASSWORD_REQUIRE_DIGITS:
        characters += string.digits
    if settings.PASSWORD_REQUIRE_SPECIAL:
        characters += '!@#$%^&*(),.?":{}|<>'

    # Ensure the password includes each required character class.
    password_chars = []

    # Add at least one character from each required class first.
    if settings.PASSWORD_REQUIRE_LOWERCASE:
        password_chars.append(secrets.choice(string.ascii_lowercase))
    if settings.PASSWORD_REQUIRE_UPPERCASE:
        password_chars.append(secrets.choice(string.ascii_uppercase))
    if settings.PASSWORD_REQUIRE_DIGITS:
        password_chars.append(secrets.choice(string.digits))
    if settings.PASSWORD_REQUIRE_SPECIAL:
        password_chars.append(secrets.choice('!@#$%^&*(),.?":{}|<>'))

    # Fill the remaining length with random characters.
    remaining_length = actual_length - len(password_chars)
    for _ in range(remaining_length):
        password_chars.append(secrets.choice(characters))

    # Shuffle the characters to remove predictable ordering.
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)


def generate_bootstrap_admin_password(length: int = BOOTSTRAP_ADMIN_PASSWORD_LENGTH) -> str:
    """
    Generate the bootstrap-only administrator password.

    This password uses only digits and symbols to avoid depending on the regular password policy configuration.
    """
    if length < 2:
        raise ValueError("首次引导密码长度不能少于2个字符")

    password_chars = [
        secrets.choice(string.digits),
        secrets.choice(BOOTSTRAP_ADMIN_PASSWORD_SYMBOLS),
    ]

    for _ in range(length - len(password_chars)):
        password_chars.append(secrets.choice(BOOTSTRAP_ADMIN_PASSWORD_CHARACTERS))

    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    :param password: Password to validate.
    :return: (whether validation passed, failure reason)
    """
    # Check the length.
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"密码长度不能少于{settings.PASSWORD_MIN_LENGTH}个字符"

    # Check the bcrypt byte-length limit.
    is_valid, message = validate_bcrypt_password_length(password)
    if not is_valid:
        return False, message

    # Check uppercase letters.
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        return False, "密码必须包含至少一个大写字母"

    # Check lowercase letters.
    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        return False, "密码必须包含至少一个小写字母"

    # Check digits.
    if settings.PASSWORD_REQUIRE_DIGITS and not re.search(r"\d", password):
        return False, "密码必须包含至少一个数字"

    # Check special characters.
    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含至少一个特殊字符"

    return True, ""


def get_password_strength_score(password: str) -> Dict[str, Union[int, List[str]]]:
    """
    Return a password-strength score and improvement suggestions.
    :param password: Password.
    :return: Strength score (0-100) and improvement suggestions.
    """
    score = 0
    suggestions = []

    # Base length score, capped at 40 points.
    length_score = min(40, len(password) * 4)
    score += length_score

    # Add a suggestion when the password is too short.
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        suggestions.append(f"密码长度至少应为{settings.PASSWORD_MIN_LENGTH}个字符")

    # Character-class diversity score, 15 points per class and 60 points max.
    if re.search(r"[a-z]", password):
        score += 15
    else:
        suggestions.append("添加小写字母可以提高密码强度")

    if re.search(r"[A-Z]", password):
        score += 15
    else:
        suggestions.append("添加大写字母可以提高密码强度")

    if re.search(r"\d", password):
        score += 15
    else:
        suggestions.append("添加数字可以提高密码强度")

    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 15
    else:
        suggestions.append("添加特殊字符可以提高密码强度")

    # Return the score and suggestions.
    return {"score": score, "suggestions": suggestions}
