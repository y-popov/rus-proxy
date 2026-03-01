import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519


def generate_wg_keypair() -> tuple[str, str]:
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

    return (
        base64.b64encode(private_raw).decode(),
        base64.b64encode(public_raw).decode()
    )
