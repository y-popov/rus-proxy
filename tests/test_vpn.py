import pytest
import base64

from src.keys import generate_keypair, KeyPair, generate_uuid, generate_short_id


def test_generate_wg_keypair():
    keypair = generate_keypair()
    assert isinstance(keypair, KeyPair)
    assert isinstance(keypair.private_key, str)
    assert isinstance(keypair.public_key, str)

    # Base64 -> raw bytes
    private_raw = base64.b64decode(keypair.private_key)
    public_raw = base64.b64decode(keypair.public_key)

    assert len(private_raw) == 32
    assert len(public_raw) == 32

    # Function generates different private keys across calls
    keypair1 = generate_keypair()
    keypair2 = generate_keypair()

    assert keypair1.private_key != keypair2.private_key
    assert keypair1.public_key != keypair2.public_key


def test_generate_uuid():
    uuid = generate_uuid()
    assert isinstance(uuid, str)
    assert len(uuid) == 36


def test_generate_short_id():
    short_id = generate_short_id()
    assert isinstance(short_id, str)
    assert len(short_id) == 8
