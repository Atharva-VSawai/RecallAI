from dataclasses import dataclass
from functools import lru_cache
import httpx
import jwt
from core.config import settings
from domain.exceptions import AuthenticationError


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    organization_id: str
    role: str
    email: str


class AuthService:
    def authenticate(self, token: str) -> AuthenticatedUser:
        if not settings.supabase_url:
            raise AuthenticationError("Supabase URL is not configured")
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid access token") from exc

        if algorithm == "HS256":
            return self._authenticate_shared_secret_token(token)
        if algorithm not in {"RS256", "ES256", "EdDSA"}:
            raise AuthenticationError("Unsupported JWT signing algorithm")
        try:
            claims = self._decode_with_jwks(token, algorithm)
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid or expired access token") from exc
        user_id = claims.get("sub")
        if not user_id:
            raise AuthenticationError("Access token does not identify a user")
        return AuthenticatedUser(
            user_id=str(user_id), organization_id="default", role="USER",
            email=str(claims.get("email") or f"{user_id}@supabase.local"),
        )

    def _decode_with_jwks(self, token: str, algorithm: str) -> dict:
        jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        issuer = self._issuer
        options = {"verify_aud": bool(settings.supabase_jwt_audience), "verify_iss": bool(issuer)}
        return jwt.decode(token, signing_key.key, algorithms=[algorithm], audience=settings.supabase_jwt_audience or None, issuer=issuer or None, options=options)

    def _authenticate_shared_secret_token(self, token: str) -> AuthenticatedUser:
        """Validate legacy HS256 tokens through Supabase Auth, not the JWT secret."""
        auth_api_key = settings.supabase_publishable_key or settings.supabase_anon_key
        if not auth_api_key:
            raise AuthenticationError("Supabase publishable/anon key is required for HS256 projects")
        try:
            response = httpx.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"apikey": auth_api_key, "Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
        except httpx.HTTPError as exc:
            raise AuthenticationError("Supabase Auth could not be reached") from exc
        if response.status_code != 200:
            raise AuthenticationError("Invalid or expired access token")
        user = response.json()
        user_id = user.get("id")
        if not user_id:
            raise AuthenticationError("Supabase Auth returned no user identity")
        return AuthenticatedUser(
            user_id=str(user_id), organization_id="default", role="USER",
            email=str(user.get("email") or f"{user_id}@supabase.local"),
        )

    @property
    def _issuer(self) -> str:
        return settings.supabase_jwt_issuer or f"{settings.supabase_url.rstrip('/')}/auth/v1"


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=600)
