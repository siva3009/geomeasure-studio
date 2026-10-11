"""
Automated tests for API key management and v1 external measurement endpoint.
Covers all required security, lifecycle, ownership, and measurement verification cases.
"""

import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import DEV_JWT_SECRET
from app.services.api_key_service import _IN_MEMORY_API_KEYS

client = TestClient(app)

USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def create_token(user_id: uuid.UUID, email: str = "user@example.com", expires_in: int = 3600) -> str:
    """Generate a real cryptographically signed Supabase Auth JWT token."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + expires_in,
    }
    return jwt.encode(payload, DEV_JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def clean_in_memory_keys():
    """Ensure clean in-memory state before and after each test."""
    _IN_MEMORY_API_KEYS.clear()
    yield
    _IN_MEMORY_API_KEYS.clear()


# ==============================================================================
# 1. API Key Creation & Plaintext Secret Exposure Controls
# ==============================================================================

def test_successful_api_key_creation():
    """1. Successful API key creation returns 201 with expected metadata."""
    token = create_token(USER_A_ID)
    res = client.post(
        "/api/keys/",
        json={"name": "Production GIS Pipeline"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Production GIS Pipeline"
    assert data["prefix"].startswith("gm_live_")
    assert data["api_key"].startswith("gm_live_")
    assert "id" in data
    assert "created_at" in data


def test_plaintext_key_returned_only_at_creation():
    """2. The plaintext key is returned ONLY at creation and never in subsequent requests."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Test Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    key_id = created_data["id"]
    plaintext_key = created_data["api_key"]

    # Retrieve by ID: plaintext key must NOT be returned
    get_res = client.get(
        f"/api/keys/{key_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    meta = get_res.json()
    assert "api_key" not in meta
    assert meta["prefix"] in plaintext_key

    # List keys: plaintext key must NOT be returned
    list_res = client.get(
        "/api/keys/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    keys = list_res.json()
    assert len(keys) == 1
    assert "api_key" not in keys[0]


def test_database_stores_hash_rather_than_plaintext():
    """3. The database / repository stores a SHA-256 hash rather than the plaintext key."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Hash Verification Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = create_res.json()
    plaintext_key = data["api_key"]
    key_id = uuid.UUID(data["id"])

    # Inspect stored record in repository
    assert key_id in _IN_MEMORY_API_KEYS
    stored = _IN_MEMORY_API_KEYS[key_id]
    assert "api_key" not in stored
    assert stored["key_hash"] == hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()
    assert plaintext_key != stored["key_hash"]


def test_listing_keys_does_not_reveal_secrets_or_hashes():
    """4. Listing a user's keys does not reveal secrets or key hashes."""
    token = create_token(USER_A_ID)
    client.post(
        "/api/keys/",
        json={"name": "Key 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/api/keys/",
        json={"name": "Key 2"},
        headers={"Authorization": f"Bearer {token}"},
    )

    res = client.get("/api/keys/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    for item in items:
        assert "api_key" not in item
        assert "key_hash" not in item
        assert "prefix" in item
        assert item["prefix"].startswith("gm_live_")


# ==============================================================================
# 2. Authentication & Ownership Access Control
# ==============================================================================

def test_valid_authenticated_owner_can_manage_own_key():
    """5. A valid authenticated owner can retrieve, inspect, and revoke their own key."""
    token = create_token(USER_A_ID)

    # 1. Create key
    create_res = client.post(
        "/api/keys/",
        json={"name": "Owner Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    key_id = create_res.json()["id"]

    # 2. Inspect metadata
    meta_res = client.get(
        f"/api/keys/{key_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert meta_res.status_code == 200
    assert meta_res.json()["is_active"] is True

    # 3. Inspect usage
    usage_res = client.get(
        f"/api/keys/{key_id}/usage/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage_res.status_code == 200
    assert usage_res.json()["request_count"] == 0

    # 4. Revoke key
    revoke_res = client.delete(
        f"/api/keys/{key_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["is_active"] is False
    assert revoke_res.json()["revoked_at"] is not None


def test_unauthenticated_users_cannot_manage_keys():
    """6. Unauthenticated requests to /api/keys/ are rejected with HTTP 401."""
    # List without token
    assert client.get("/api/keys/").status_code == 401

    # Create without token
    assert client.post("/api/keys/", json={"name": "Test"}).status_code == 401

    # Inspect without token
    random_id = str(uuid.uuid4())
    assert client.get(f"/api/keys/{random_id}/").status_code == 401

    # Revoke without token
    assert client.delete(f"/api/keys/{random_id}/").status_code == 401

    # Usage without token
    assert client.get(f"/api/keys/{random_id}/usage/").status_code == 401

    # Invalid / corrupted token
    assert client.get("/api/keys/", headers={"Authorization": "Bearer not-a-valid-jwt"}).status_code == 401


def test_user_cannot_access_another_users_key():
    """7. User B cannot view, inspect, or revoke a key owned by User A."""
    token_a = create_token(USER_A_ID, email="alice@example.com")
    token_b = create_token(USER_B_ID, email="bob@example.com")

    # User A creates a key
    create_res = client.post(
        "/api/keys/",
        json={"name": "Alice Key"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    key_a_id = create_res.json()["id"]

    # User B lists keys: Alice's key must not be present
    list_b = client.get("/api/keys/", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    # User B tries to get Alice's key: 404 Not Found
    get_b = client.get(f"/api/keys/{key_a_id}/", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 404

    # User B tries to inspect Alice's usage: 404 Not Found
    usage_b = client.get(f"/api/keys/{key_a_id}/usage/", headers={"Authorization": f"Bearer {token_b}"})
    assert usage_b.status_code == 404

    # User B tries to revoke Alice's key: 404 Not Found
    revoke_b = client.delete(f"/api/keys/{key_a_id}/", headers={"Authorization": f"Bearer {token_b}"})
    assert revoke_b.status_code == 404

    # Alice's key must still be active
    meta_a = client.get(f"/api/keys/{key_a_id}/", headers={"Authorization": f"Bearer {token_a}"})
    assert meta_a.status_code == 200
    assert meta_a.json()["is_active"] is True


# ==============================================================================
# 3. External Protected API Endpoint (/api/v1/measurements/)
# ==============================================================================

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [77.2090, 28.6139],
            [77.2190, 28.6139],
            [77.2190, 28.6239],
            [77.2090, 28.6239],
            [77.2090, 28.6139],
        ]
    ],
}

SAMPLE_LINESTRING = {
    "type": "LineString",
    "coordinates": [
        [77.2090, 28.6139],
        [77.2190, 28.6139],
    ],
}


def test_valid_api_key_can_call_measurement_endpoint():
    """8. A valid API key can successfully invoke the external measurement endpoint."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "External Integration"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_res.json()["api_key"]
    key_id = create_res.json()["id"]

    # Call with X-API-Key header
    res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["geometry_type"] == "Polygon"
    assert data["source_crs"] == "EPSG:4326"
    assert data["measurement_crs"].startswith("EPSG:326")
    assert data["area_sq_meters"] is not None
    assert data["area_sq_meters"] > 0
    assert data["area_hectares"] is not None
    assert data["measurement_unit"] == "meters"

    # Verify usage was updated
    usage_res = client.get(f"/api/keys/{key_id}/usage/", headers={"Authorization": f"Bearer {token}"})
    assert usage_res.status_code == 200
    assert usage_res.json()["request_count"] == 1
    assert usage_res.json()["last_used_at"] is not None


def test_missing_and_invalid_api_keys_are_rejected():
    """9. Missing, malformed, and unrecognized API keys are rejected with HTTP 401."""
    # Missing header
    res_missing = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "EPSG:4326"},
    )
    assert res_missing.status_code == 401

    # Malformed key (doesn't start with gm_live_)
    res_malformed = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "EPSG:4326"},
        headers={"X-API-Key": "invalid_secret_key_123"},
    )
    assert res_malformed.status_code == 401

    # Unrecognized key with correct prefix format
    res_unknown = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "EPSG:4326"},
        headers={"X-API-Key": "gm_live_unrecognized_fake_random_key_12345"},
    )
    assert res_unknown.status_code == 401


def test_revoked_keys_are_rejected_immediately():
    """10. Revoked keys are rejected immediately upon revocation."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Temporary Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_res.json()["api_key"]
    key_id = create_res.json()["id"]

    # Verify key works initially
    pre_res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_LINESTRING, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert pre_res.status_code == 200

    # Revoke key
    del_res = client.delete(f"/api/keys/{key_id}/", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

    # Next request with revoked key must be rejected immediately
    post_res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_LINESTRING, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert post_res.status_code == 401
    assert "revoked" in post_res.json()["detail"].lower()


def test_expired_keys_are_rejected():
    """11. Expired keys are rejected with HTTP 401."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Expiring Key", "expires_in_days": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_res.json()["api_key"]
    key_id = uuid.UUID(create_res.json()["id"])

    # Simulate expiration in repository
    _IN_MEMORY_API_KEYS[key_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=10)

    # Calling with expired key must fail
    res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_invalid_measurement_input_is_rejected():
    """12. Invalid geometry inputs and unknown CRS are rejected with HTTP 400."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Validation Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_res.json()["api_key"]

    # 1. Invalid / malformed geometry structure
    bad_geom_res = client.post(
        "/api/v1/measurements/",
        json={"geometry": {"type": "InvalidType", "coordinates": []}, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert bad_geom_res.status_code == 400

    # 2. Unknown or unidentifiable CRS rejected (policy against guessing unknown CRS)
    unknown_crs_res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "Unknown"},
        headers={"X-API-Key": api_key},
    )
    assert unknown_crs_res.status_code == 400

    # 3. Invalid CRS format
    fake_crs_res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "FAKE:99999"},
        headers={"X-API-Key": api_key},
    )
    assert fake_crs_res.status_code == 400


def test_bearer_gm_live_header_supported():
    """Optional support for Authorization: Bearer gm_live_<key>."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Bearer API Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_res.json()["api_key"]

    res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_LINESTRING, "crs": "EPSG:4326"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert res.status_code == 200
    assert res.json()["length_meters"] is not None


# ==============================================================================
# 5. JWT Security & Asymmetric Verification Preflight Tests
# ==============================================================================

def test_jwt_unpermitted_algorithm_rejected():
    """Unpermitted algorithms (such as 'none' or 'HS384') are strictly rejected."""
    # 1. 'none' algorithm
    none_token = jwt.encode(
        {"sub": str(USER_A_ID), "aud": "authenticated", "exp": int(time.time()) + 3600},
        key="",
        algorithm="none",
    )
    res_none = client.get("/api/keys/", headers={"Authorization": f"Bearer {none_token}"})
    assert res_none.status_code == 401
    assert "unsupported or unpermitted" in res_none.json()["detail"].lower()

    # 2. HS384 algorithm (not on whitelist)
    hs384_token = jwt.encode(
        {"sub": str(USER_A_ID), "aud": "authenticated", "exp": int(time.time()) + 3600},
        DEV_JWT_SECRET,
        algorithm="HS384",
    )
    res_hs384 = client.get("/api/keys/", headers={"Authorization": f"Bearer {hs384_token}"})
    assert res_hs384.status_code == 401
    assert "unsupported or unpermitted" in res_hs384.json()["detail"].lower()


def test_jwt_malformed_token_rejected():
    """Tokens with malformed structures or non-UUID subjects are rejected with 401."""
    # Garbage string
    res_garbage = client.get("/api/keys/", headers={"Authorization": "Bearer not-a-valid-token"})
    assert res_garbage.status_code == 401

    # Token with non-UUID subject
    bad_sub_token = jwt.encode(
        {"sub": "not-a-valid-uuid", "aud": "authenticated", "exp": int(time.time()) + 3600},
        DEV_JWT_SECRET,
        algorithm="HS256",
    )
    res_bad_sub = client.get("/api/keys/", headers={"Authorization": f"Bearer {bad_sub_token}"})
    assert res_bad_sub.status_code == 401
    assert "valid uuid" in res_bad_sub.json()["detail"].lower()


def test_jwt_asymmetric_rs256_verification_and_key_rotation():
    """Asymmetric RS256 token verification succeeds via JWKS client and handles unknown key IDs."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from app.services.auth import set_jwks_client

    # Generate an ephemeral test RSA key pair
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    class MockSigningKey:
        def __init__(self, key):
            self.key = key

    class MockJWKClient:
        def __init__(self, keys):
            self.keys = keys

        def get_signing_key_from_jwt(self, token):
            hdr = jwt.get_unverified_header(token)
            kid = hdr.get("kid")
            if kid in self.keys:
                return MockSigningKey(self.keys[kid])
            raise jwt.PyJWKClientError(f"Key ID '{kid}' not found in mock JWKS.")

    # Configure mock JWKS client
    set_jwks_client(MockJWKClient({"supabase-rsa-key-1": public_pem}))

    try:
        # 1. Valid RS256 token with matching kid
        rs256_token = jwt.encode(
            {
                "sub": str(USER_A_ID),
                "email": "asymmetric_user@example.com",
                "aud": "authenticated",
                "exp": int(time.time()) + 3600,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "supabase-rsa-key-1"},
        )

        res_valid = client.post(
            "/api/keys/",
            json={"name": "RS256 Integration Key"},
            headers={"Authorization": f"Bearer {rs256_token}"},
        )
        assert res_valid.status_code == 201
        assert res_valid.json()["name"] == "RS256 Integration Key"

        # 2. RS256 token with unknown/rotated kid
        unknown_kid_token = jwt.encode(
            {
                "sub": str(USER_A_ID),
                "aud": "authenticated",
                "exp": int(time.time()) + 3600,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "supabase-unknown-rotated-key"},
        )
        res_unknown = client.get("/api/keys/", headers={"Authorization": f"Bearer {unknown_kid_token}"})
        assert res_unknown.status_code == 401
        assert "unrecognized jwt signing key identifier" in res_unknown.json()["detail"].lower()

    finally:
        # Reset JWKS client
        set_jwks_client(None)


# ==============================================================================
# 6. End-to-End QA Integration Tests (Point Geometry & Projected CRS)
# ==============================================================================

def test_point_geometry_measurement_endpoint():
    """Verify Point geometry submission and its documented output behavior (no area/length)."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Point Test Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_res.json()["api_key"]

    res = client.post(
        "/api/v1/measurements/",
        json={
            "geometry": {"type": "Point", "coordinates": [77.2090, 28.6139]},
            "crs": "EPSG:4326",
            "properties": {"landmark": "India Gate"},
        },
        headers={"X-API-Key": api_key},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["geometry_type"] == "Point"
    assert data["source_crs"] == "EPSG:4326"
    assert data["area_sq_meters"] is None
    assert data["length_meters"] is None
    assert data["properties"]["landmark"] == "India Gate"


def test_linestring_with_projected_crs():
    """Verify LineString measurement with an explicit projected CRS (EPSG:3857)."""
    token = create_token(USER_A_ID)
    create_res = client.post(
        "/api/keys/",
        json={"name": "Projected CRS Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_res.json()["api_key"]

    res = client.post(
        "/api/v1/measurements/",
        json={
            "geometry": {
                "type": "LineString",
                "coordinates": [[8595000, 3326000], [8596000, 3327000]],
            },
            "crs": "EPSG:3857",
        },
        headers={"X-API-Key": api_key},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["geometry_type"] == "LineString"
    assert data["source_crs"] == "EPSG:3857"
    assert data["length_meters"] is not None
    assert data["length_meters"] > 0
    assert data["length_km"] is not None


def test_full_api_key_lifecycle_and_usage_tracking():
    """Verify full sequential lifecycle: Create -> Measure -> Usage Counter -> Revoke -> Immediate 401."""
    token = create_token(USER_A_ID)

    # 1. Create key
    create_res = client.post(
        "/api/keys/",
        json={"name": "Lifecycle Integration Key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    key_id = created_data["id"]
    api_key = created_data["api_key"]

    # 2. First measurement call
    res_1 = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert res_1.status_code == 200

    # 3. Second measurement call
    res_2 = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_LINESTRING, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert res_2.status_code == 200

    # 4. Check usage counter is 2
    usage_res = client.get(f"/api/keys/{key_id}/usage/", headers={"Authorization": f"Bearer {token}"})
    assert usage_res.status_code == 200
    assert usage_res.json()["request_count"] == 2

    # 5. Revoke key
    revoke_res = client.delete(f"/api/keys/{key_id}/", headers={"Authorization": f"Bearer {token}"})
    assert revoke_res.status_code == 200
    assert revoke_res.json()["is_active"] is False

    # 6. Verify subsequent call fails with 401
    post_revoke_res = client.post(
        "/api/v1/measurements/",
        json={"geometry": SAMPLE_POLYGON, "crs": "EPSG:4326"},
        headers={"X-API-Key": api_key},
    )
    assert post_revoke_res.status_code == 401
    assert "revoked" in post_revoke_res.json()["detail"].lower()


