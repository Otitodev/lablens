"""Epic FHIR sandbox OAuth service for LabLens MCP.

Implements SMART on FHIR Backend Services (client credentials + JWT assertion)
for Epic's non-production sandbox. Tokens are cached in memory with expiry
tracking so the token endpoint is not called on every FHIR request.

Flow:
  1. Generate a signed RS384 JWT (client_assertion) from the RSA private key.
  2. POST client_assertion to Epic's token endpoint.
  3. Cache the returned access token until it is close to expiry.

Reference:
  https://fhir.epic.com/Documentation?docId=oauth2&section=BackendOAuth2Guide
"""
from __future__ import annotations

import base64
import logging
import threading
import time
import uuid
from dataclasses import dataclass

import httpx
import jwt  # PyJWT
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.config import Settings

logger = logging.getLogger(__name__)

_TOKEN_EXPIRY_BUFFER_SECONDS = 60

# Known Epic sandbox patient IDs — public, non-PHI, from Epic's documentation.
EPIC_SANDBOX_PATIENT_IDS: list[dict[str, str]] = [
    {"patient_id": "eD5PmS3L3BFwWuAnV2bAk2g3", "name": "Camila Lopez",   "note": "Adult female"},
    {"patient_id": "erXuFYUfucBZaryVksYEcMg3", "name": "Derrick Lin",     "note": "Adult male"},
    {"patient_id": "eq081-VQEgP8drUUqCWzHfw3",  "name": "Jason Argonaut", "note": "SMART tutorial patient"},
    {"patient_id": "eIXesllypH3M9tAA5WdJftQ3", "name": "Nancy Smart",     "note": "Paediatric"},
]


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float  # time.monotonic() — immune to wall-clock changes


class EpicOAuthService:
    """Thread-safe in-memory token cache for Epic FHIR sandbox OAuth (JWT assertion)."""

    def __init__(self, settings: Settings, timeout: float = 10.0) -> None:
        self._settings = settings
        self._timeout = timeout
        self._lock = threading.Lock()
        self._cached: _CachedToken | None = None

    def get_access_token(self) -> str:
        """Return a valid access token, fetching a new one if the cache is stale.

        Thread-safe: concurrent callers block on the lock rather than issuing
        parallel token requests to the Epic token endpoint.
        """
        with self._lock:
            if self._cached and time.monotonic() < self._cached.expires_at:
                logger.debug("epic_oauth token_cache_hit")
                return self._cached.access_token
            logger.info("epic_oauth token_cache_miss fetching_new_token")
            self._cached = self._fetch_token()
            return self._cached.access_token

    def _fetch_token(self) -> _CachedToken:
        now = int(time.time())
        assertion = jwt.encode(
            payload={
                "iss": self._settings.epic_client_id,
                "sub": self._settings.epic_client_id,
                "aud": self._settings.epic_token_url,
                "jti": str(uuid.uuid4()),  # unique per request — Epic rejects replays
                "nbf": now,
                "iat": now,
                "exp": now + 300,  # Epic enforces 5-minute maximum
            },
            key=self._normalize_pem(self._settings.epic_private_key),
            algorithm="RS384",
            headers={"kid": self._settings.epic_kid},
        )

        try:
            response = httpx.post(
                self._settings.epic_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_assertion_type": (
                        "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
                    ),
                    "client_assertion": assertion,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "epic_oauth token_fetch_failed status=%s body=%s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise
        except httpx.RequestError as exc:
            logger.error("epic_oauth token_fetch_request_error error=%s", exc)
            raise

        payload = response.json()
        expires_in = int(payload.get("expires_in", 3600))
        effective_ttl = expires_in - _TOKEN_EXPIRY_BUFFER_SECONDS
        logger.info(
            "epic_oauth token_fetched expires_in=%d effective_ttl=%d",
            expires_in,
            effective_ttl,
        )
        return _CachedToken(
            access_token=payload["access_token"],
            expires_at=time.monotonic() + effective_ttl,
        )

    def _get_public_jwk(self) -> dict:
        """Derive the RSA public JWK from the configured private key PEM.

        Returns a JWK dict suitable for serving at GET /jwks.json.
        Epic fetches this URL to verify the client_assertion JWT signature.
        The kid must match the kid in the JWT JOSE header.
        """
        pem = self._normalize_pem(self._settings.epic_private_key)
        private_key = load_pem_private_key(pem.encode("utf-8"), password=None)
        pub_numbers = private_key.public_key().public_numbers()

        def _b64url(n: int) -> str:
            byte_length = (n.bit_length() + 7) // 8
            return (
                base64.urlsafe_b64encode(n.to_bytes(byte_length, "big"))
                .rstrip(b"=")
                .decode("ascii")
            )

        return {
            "kty": "RSA",
            "alg": "RS384",
            "use": "sig",
            "kid": self._settings.epic_kid,
            "n": _b64url(pub_numbers.n),
            "e": _b64url(pub_numbers.e),
        }

    @staticmethod
    def _normalize_pem(raw: str) -> str:
        """Reconstruct a multiline PEM from a single-line env-var value.

        Env vars (Railway, Docker) can't reliably store literal newlines.
        Store the PEM with \\n separators and this method restores them.
        If the string already contains real newlines it is returned unchanged.
        """
        if "\n" in raw:
            return raw
        return raw.replace("\\n", "\n")
