#!/usr/bin/env python3
"""Generate RSA 2048-bit key pair for Epic FHIR JWT assertion.

Usage:
    python scripts/generate_epic_keys.py

Output:
    - EPIC_PRIVATE_KEY value for .env (single line with \\n separators)
    - Public JWK for manual inspection
    - Step-by-step setup instructions
"""
from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def _b64url(n: int) -> str:
    byte_length = (n.bit_length() + 7) // 8
    return (
        base64.urlsafe_b64encode(n.to_bytes(byte_length, "big"))
        .rstrip(b"=")
        .decode("ascii")
    )


def main() -> None:
    print("Generating RSA 2048-bit key pair...")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pem_str = pem_bytes.decode("utf-8")
    single_line = pem_str.replace("\n", "\\n")

    pub_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "alg": "RS384",
        "use": "sig",
        "kid": "lablens-1",
        "n": _b64url(pub_numbers.n),
        "e": _b64url(pub_numbers.e),
    }

    print()
    print("=" * 70)
    print("Add this to your .env file (one line):")
    print("=" * 70)
    print(f"EPIC_PRIVATE_KEY={single_line}")
    print()
    print("=" * 70)
    print("Public JWK (for manual verification):")
    print("=" * 70)
    print(json.dumps(jwk, indent=2))
    print()
    print("=" * 70)
    print("Next steps:")
    print("=" * 70)
    print("1. Add EPIC_PRIVATE_KEY=... and EPIC_KID=lablens-1 to your .env")
    print("2. Deploy / restart the server")
    print("3. Verify the JWK Set endpoint:")
    print("       GET https://lablens.up.railway.app/jwks.json")
    print("4. In the Epic developer portal, set 'Non-Production JWK Set URL' to:")
    print("       https://lablens.up.railway.app/jwks.json")
    print("5. Save the app — Epic will give you an EPIC_CLIENT_ID")
    print("6. Add EPIC_CLIENT_ID to your .env")
    print("7. Remove EPIC_CLIENT_SECRET if present (no longer used)")


if __name__ == "__main__":
    main()
