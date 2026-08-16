import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)
_ENCRYPTED_PREFIX = "enc::"

def _get_fernet() -> Fernet:
    raw_key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(raw_key)
    return Fernet(fernet_key)

def encrypt_value(plain_text: str) -> str:
    if not plain_text:
        return plain_text  
    if plain_text.startswith(_ENCRYPTED_PREFIX):
        return plain_text
    token = _get_fernet().encrypt(plain_text.encode("utf-8"))
    return _ENCRYPTED_PREFIX + token.decode("utf-8")

def decrypt_value(stored_value: str) -> str:
    if not stored_value:
        return stored_value  
    if not stored_value.startswith(_ENCRYPTED_PREFIX):
        return stored_value
    token = stored_value[len(_ENCRYPTED_PREFIX):]
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error("Failed to decrypt value — token invalid or SECRET_KEY changed.")
        return ""