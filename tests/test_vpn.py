import pytest
import base64

from pygments.lexer import inherit

from src.vpn import generate_wg_keypair, WireGuardKeyPair


def test_generate_wg_keypair():
    keypair = generate_wg_keypair()
    assert isinstance(keypair, WireGuardKeyPair)
    assert isinstance(keypair.private_key, str)
    assert isinstance(keypair.public_key, str)

    # Base64 -> raw bytes
    private_raw = base64.b64decode(keypair.private_key)
    public_raw = base64.b64decode(keypair.public_key)

    assert len(private_raw) == 32
    assert len(public_raw) == 32

    # Function generates different private keys across calls
    keypair1 = generate_wg_keypair()
    keypair2 = generate_wg_keypair()

    assert keypair1.private_key != keypair2.private_key
    assert keypair1.public_key != keypair2.public_key
