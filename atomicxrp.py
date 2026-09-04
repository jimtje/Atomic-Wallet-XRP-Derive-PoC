import hashlib
import base58
from mnemonic import Mnemonic
from bip32 import BIP32
from ecdsa import SECP256k1
from bip_utils import Bip39MnemonicValidator
import json

DERIVATION_PATH = "m/44'/144'/0'/0/0"
FAMILY_SEED_PREFIX = b"\x21"
ACCOUNT_ID_PREFIX = b"\x00"
_N = SECP256k1.order
_G = SECP256k1.generator

XRP_ALPHABET = b"rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"

def bip39_mnemonic_to_seed(phrase: str, passphrase: str = "") -> bytes:
    return Mnemonic("english").to_seed(phrase, passphrase)

def bip32_derive_chaincode(seed: bytes, path: str) -> tuple[bytes, bytes]:
    node = BIP32.from_seed(seed)
    chaincode, privkey = node.get_extended_privkey_from_path(path)
    return (chaincode, privkey)

def ripple_b58check(body: bytes) -> str:
    checksum = hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4]
    return base58.b58encode(body + checksum, alphabet=XRP_ALPHABET).decode()


def ripple_generate_seed(entropy: bytes) -> str:
    ent16 = entropy[:16]
    prefix = FAMILY_SEED_PREFIX
    return ripple_b58check(prefix + ent16)

def _sha512_half(b: bytes) -> bytes:
    return hashlib.sha512(b).digest()[:32]

def _u32(i: int) -> bytes:
    return i.to_bytes(4, "big")

def _derive_scalar(b: bytes, discrim: int | None = None) -> int:
    i = 0
    while True:
        data = b + (_u32(discrim) if discrim is not None else b"") + _u32(i)
        key = int.from_bytes(_sha512_half(data), "big")
        if 0 < key < _N:
            return key
        i += 1


def secp256k1_derive_keypair(entropy: bytes) -> tuple[str, str]:
    ent16 = entropy[:16]
    root = _derive_scalar(ent16)
    pub_gen = (_G * root).to_bytes("compressed")
    account = (_derive_scalar(pub_gen, 0) + root) % _N
    private_key = b"\x00" + account.to_bytes(32, "big")
    public_key = (_G * account).to_bytes("compressed")
    return private_key.hex().upper(), public_key.hex().upper()

def derive_address(public_key_hex: str) -> str:
    pub = bytes.fromhex(public_key_hex)
    account_id = hashlib.new("ripemd160", hashlib.sha256(pub).digest()).digest()
    return ripple_b58check(ACCOUNT_ID_PREFIX + account_id)

def derive_xrp(mnemonic_phrase: str, passphrase: str = "") -> dict:
    seed = bip39_mnemonic_to_seed(mnemonic_phrase, passphrase)
    chaincode, privkey = bip32_derive_chaincode(seed, DERIVATION_PATH)
    family_seed = ripple_generate_seed(chaincode)
    priv, pub = secp256k1_derive_keypair(chaincode)
    address = derive_address(pub)
    outdict = {

        "bip39_seed": seed.hex(),
        "chainCode": chaincode.hex(),
        "family_seed(secret)": family_seed,
        "privateKey": priv,
        "publicKey": pub,
        "address": address,
    }
    return outdict

if __name__ == "__main__":
    mnemonic = input("enter your 12 word atomicc mnemonic> ")
    if Bip39MnemonicValidator().IsValid(mnemonic):
        print(json.dumps(derive_xrp(mnemonic)))
    else:
        print("Your mnemonic is broken, yo")