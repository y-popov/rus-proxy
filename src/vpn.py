import base64
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519


@dataclass(frozen=True, slots=True)
class WireGuardKeyPair:
    private_key: str
    public_key: str


def generate_wg_keypair() -> WireGuardKeyPair:
    """
    Generate a WireGuard-compatible private/public keypair using cryptography.
    Returns:
        (private_key_b64, public_key_b64)
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

    return WireGuardKeyPair(
        private_key=base64.b64encode(private_raw).decode(),
        public_key=base64.b64encode(public_raw).decode()
    )
