import pytest
import base64

from src.vpn import generate_wg_keypair


def test_generate_wg_keypair():
    private_b64, public_b64 = generate_wg_keypair()

    # Base64 -> raw bytes
    private_raw = base64.b64decode(private_b64)
    public_raw = base64.b64decode(public_b64)

    assert isinstance(private_b64, str)
    assert isinstance(public_b64, str)
    assert len(private_raw) == 32
    assert len(public_raw) == 32

    # Function generates different private keys across calls
    priv1, pub1 = generate_wg_keypair()
    priv2, pub2 = generate_wg_keypair()

    assert priv1 != priv2
    assert pub1 != pub2
