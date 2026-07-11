import asyncio
import base64
import binascii
import hashlib
import hmac
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


PASSWORD_ITERATIONS = 260_000
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 1_024
MAX_EMAIL_LENGTH = 320
MAX_DISPLAY_NAME_LENGTH = 80
MAX_HASH_ITERATIONS = 2_000_000
DUMMY_PASSWORD_HASH = (
    "pbkdf2_sha256$260000$dGlja2ZyYW1lLWR1bW15LXNhbHQ="
    "$9n0k2vqmFStbaI4CAqV5KmBWmUuRWj2/KqmdSZKUA9g="
)


class AuthError(Exception):
    pass


class AuthConflict(AuthError):
    pass


class AuthInvalidCredentials(AuthError):
    pass


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    display_name: str
    created_at: datetime

    def to_api(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "email": self.email,
            "displayName": self.display_name,
            "createdAt": self.created_at.astimezone(timezone.utc).isoformat(),
        }


@dataclass
class _UserRecord:
    user: AuthUser
    password_hash: str


@dataclass
class _SessionRecord:
    user_id: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    local, separator, domain = value.rpartition("@")
    if (
        not separator
        or value.count("@") != 1
        or not local
        or not domain
        or len(value) > MAX_EMAIL_LENGTH
        or any(character.isspace() for character in value)
    ):
        raise ValueError("A valid email address is required")
    return value


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(PASSWORD_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_value, digest_value = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        parsed_iterations = int(iterations)
        if not 1 <= parsed_iterations <= MAX_HASH_ITERATIONS:
            return False
        salt = base64.b64decode(salt_value.encode("ascii"), validate=True)
        expected = base64.b64decode(digest_value.encode("ascii"), validate=True)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            parsed_iterations,
        )
    except (binascii.Error, OverflowError, TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self,
        database_url: Optional[str] = None,
        session_ttl_days: Optional[int] = None,
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        ttl_days = (
            session_ttl_days
            if session_ttl_days is not None
            else int(os.getenv("TICKFRAME_AUTH_SESSION_DAYS", "7"))
        )
        if not 1 <= ttl_days <= 365:
            raise ValueError("TICKFRAME_AUTH_SESSION_DAYS must be between 1 and 365")
        self.session_ttl = timedelta(days=ttl_days)
        self.engine: Optional[AsyncEngine] = None
        self._users_by_email: Dict[str, _UserRecord] = {}
        self._users_by_id: Dict[str, _UserRecord] = {}
        self._sessions: Dict[str, _SessionRecord] = {}

    async def start(self) -> None:
        if not self.database_url:
            return
        if self.engine is not None:
            return
        self.engine = create_async_engine(self.database_url, pool_pre_ping=True)
        try:
            await self.ensure_schema()
        except Exception:
            await self.engine.dispose()
            self.engine = None
            raise

    async def stop(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None

    async def ensure_schema(self) -> None:
        if self.engine is None:
            return
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS auth_users (
                        id UUID PRIMARY KEY,
                        email TEXT NOT NULL UNIQUE,
                        display_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        token_hash TEXT PRIMARY KEY,
                        user_id UUID NOT NULL REFERENCES auth_users(id)
                            ON DELETE CASCADE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        expires_at TIMESTAMPTZ NOT NULL,
                        revoked_at TIMESTAMPTZ
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS auth_sessions_user_idx
                    ON auth_sessions (user_id, expires_at DESC)
                    """
                )
            )

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, object]:
        normalized_email = normalize_email(email)
        validate_password(password)
        public_name = (
            " ".join(display_name.split())
            if display_name and display_name.strip()
            else normalized_email.split("@", 1)[0]
        )
        if len(public_name) > MAX_DISPLAY_NAME_LENGTH:
            raise ValueError(
                f"Display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters"
            )
        password_hash = await asyncio.to_thread(hash_password, password)

        if self.engine is not None:
            user = await self._register_database_user(
                normalized_email,
                public_name,
                password_hash,
            )
        else:
            user = self._register_memory_user(
                normalized_email,
                public_name,
                password_hash,
            )
        return await self._issue_auth_response(user)

    async def login(self, *, email: str, password: str) -> Dict[str, object]:
        normalized_email = normalize_email(email)
        record = await self._get_user_record_by_email(normalized_email)
        valid_password = await asyncio.to_thread(
            verify_password,
            password,
            record.password_hash if record is not None else DUMMY_PASSWORD_HASH,
        )
        if record is None or not valid_password:
            raise AuthInvalidCredentials("Invalid email or password")
        return await self._issue_auth_response(record.user)

    async def current_user(self, token: str) -> Optional[AuthUser]:
        token_hash = _hash_token(token)
        now = datetime.now(timezone.utc)

        if self.engine is not None:
            async with self.engine.connect() as connection:
                result = await connection.execute(
                    text(
                        """
                        SELECT u.id, u.email, u.display_name, u.created_at
                        FROM auth_sessions s
                        JOIN auth_users u ON u.id = s.user_id
                        WHERE s.token_hash = :token_hash
                          AND s.revoked_at IS NULL
                          AND s.expires_at > NOW()
                        """
                    ),
                    {"token_hash": token_hash},
                )
                row = result.mappings().first()
            return None if row is None else self._row_to_user(row)

        session = self._sessions.get(token_hash)
        if (
            session is None
            or session.revoked_at is not None
            or session.expires_at <= now
        ):
            self._sessions.pop(token_hash, None)
            return None
        record = self._users_by_id.get(session.user_id)
        return None if record is None else record.user

    async def logout(self, token: str) -> None:
        token_hash = _hash_token(token)
        if self.engine is not None:
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(
                        """
                        UPDATE auth_sessions
                        SET revoked_at = NOW()
                        WHERE token_hash = :token_hash
                          AND revoked_at IS NULL
                        """
                    ),
                    {"token_hash": token_hash},
                )
            return

        session = self._sessions.get(token_hash)
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)

    async def _register_database_user(
        self,
        email: str,
        display_name: str,
        password_hash: str,
    ) -> AuthUser:
        assert self.engine is not None
        user_id = str(uuid.uuid4())
        try:
            async with self.engine.begin() as connection:
                result = await connection.execute(
                    text(
                        """
                        INSERT INTO auth_users (
                            id, email, display_name, password_hash
                        ) VALUES (
                            :id, :email, :display_name, :password_hash
                        )
                        RETURNING id, email, display_name, created_at
                        """
                    ),
                    {
                        "id": user_id,
                        "email": email,
                        "display_name": display_name,
                        "password_hash": password_hash,
                    },
                )
                row = result.mappings().one()
        except IntegrityError as error:
            raise AuthConflict("Email is already registered") from error
        return self._row_to_user(row)

    def _register_memory_user(
        self,
        email: str,
        display_name: str,
        password_hash: str,
    ) -> AuthUser:
        if email in self._users_by_email:
            raise AuthConflict("Email is already registered")
        user = AuthUser(
            id=str(uuid.uuid4()),
            email=email,
            display_name=display_name,
            created_at=datetime.now(timezone.utc),
        )
        record = _UserRecord(user=user, password_hash=password_hash)
        self._users_by_email[email] = record
        self._users_by_id[user.id] = record
        return user

    async def _get_user_record_by_email(
        self,
        email: str,
    ) -> Optional[_UserRecord]:
        if self.engine is not None:
            async with self.engine.connect() as connection:
                result = await connection.execute(
                    text(
                        """
                        SELECT id, email, display_name, password_hash, created_at
                        FROM auth_users
                        WHERE email = :email
                        """
                    ),
                    {"email": email},
                )
                row = result.mappings().first()
            if row is None:
                return None
            return _UserRecord(
                user=self._row_to_user(row),
                password_hash=str(row["password_hash"]),
            )
        return self._users_by_email.get(email)

    async def _issue_auth_response(self, user: AuthUser) -> Dict[str, object]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + self.session_ttl
        token_hash = _hash_token(token)

        if self.engine is not None:
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(
                        """
                        INSERT INTO auth_sessions (
                            token_hash, user_id, expires_at
                        ) VALUES (
                            :token_hash, :user_id, :expires_at
                        )
                        """
                    ),
                    {
                        "token_hash": token_hash,
                        "user_id": user.id,
                        "expires_at": expires_at,
                    },
                )
        else:
            now = datetime.now(timezone.utc)
            self._sessions = {
                key: session
                for key, session in self._sessions.items()
                if session.revoked_at is None and session.expires_at > now
            }
            self._sessions[token_hash] = _SessionRecord(
                user_id=user.id,
                expires_at=expires_at,
            )

        return {
            "token": token,
            "tokenType": "bearer",
            "expiresAt": expires_at.isoformat(),
            "user": user.to_api(),
        }

    @staticmethod
    def _row_to_user(row: object) -> AuthUser:
        return AuthUser(
            id=str(row["id"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            created_at=row["created_at"],
        )
