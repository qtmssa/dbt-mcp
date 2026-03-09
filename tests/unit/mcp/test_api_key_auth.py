import pytest

from dbt_mcp.mcp.api_key_auth import ApiKeyTokenVerifier


@pytest.mark.asyncio
async def test_api_key_verifier_accepts_valid_token():
    verifier = ApiKeyTokenVerifier("secret")
    token = await verifier.verify_token("secret")
    assert token is not None
    assert token.client_id == "api-key"
    assert token.scopes == []


@pytest.mark.asyncio
async def test_api_key_verifier_rejects_invalid_token():
    verifier = ApiKeyTokenVerifier("secret")
    token = await verifier.verify_token("wrong")
    assert token is None
