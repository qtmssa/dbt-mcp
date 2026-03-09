import secrets

from mcp.server.auth.provider import AccessToken, TokenVerifier


class ApiKeyTokenVerifier(TokenVerifier):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self._api_key):
            return None
        return AccessToken(
            token=token,
            client_id="api-key",
            scopes=[],
            expires_at=None,
        )
