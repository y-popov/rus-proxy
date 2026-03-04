import uuid
import base64
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519


@dataclass(frozen=True, slots=True)
class KeyPair:
    private_key: str
    public_key: str


def generate_keypair(urlsafe: bool = False) -> KeyPair:
    """
    Generate a WireGuard/v2ray-compatible private/public keypair using cryptography.
    """
    private = x25519.X25519PrivateKey.generate()
    public = private.public_key()

    private_raw = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_raw = public.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    if urlsafe:
        return KeyPair(
            private_key=base64.urlsafe_b64encode(private_raw).rstrip(b'=').decode(),
            public_key=base64.urlsafe_b64encode(public_raw).rstrip(b'=').decode(),
        )

    return KeyPair(
        private_key=base64.b64encode(private_raw).decode(),
        public_key=base64.b64encode(public_raw).decode()
    )

def generate_uuid() -> str:
    return str(uuid.uuid4())

def generate_short_id() -> str:
    return secrets.token_hex(4)  # 8 hex characters
