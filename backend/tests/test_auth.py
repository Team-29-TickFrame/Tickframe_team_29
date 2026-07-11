import unittest

from backend.app.auth import (
    AuthConflict,
    AuthInvalidCredentials,
    AuthService,
    hash_password,
    verify_password,
)


class AuthTests(unittest.IsolatedAsyncioTestCase):
    def test_password_hash_verification(self) -> None:
        stored = hash_password("correct-horse")

        self.assertTrue(verify_password("correct-horse", stored))
        self.assertFalse(verify_password("wrong-password", stored))
        self.assertFalse(verify_password("password", "not-a-valid-hash"))
        self.assertFalse(verify_password("password", "pbkdf2_sha256$999999999$bad$bad"))

    async def test_registration_rejects_oversized_inputs(self) -> None:
        service = AuthService(database_url=None)

        with self.assertRaisesRegex(ValueError, "at most"):
            await service.register(
                email="user@example.com",
                password="x" * 1_025,
            )
        with self.assertRaisesRegex(ValueError, "Display name"):
            await service.register(
                email="user@example.com",
                password="strong-password",
                display_name="x" * 81,
            )

    def test_session_ttl_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 365"):
            AuthService(database_url=None, session_ttl_days=0)

    async def test_memory_register_login_and_current_user(self) -> None:
        service = AuthService(database_url=None)

        registered = await service.register(
            email="User@Example.com",
            password="strong-password",
            display_name="Romy",
        )
        token = str(registered["token"])

        user = await service.current_user(token)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "user@example.com")
        self.assertEqual(user.display_name, "Romy")

        logged_in = await service.login(
            email="user@example.com",
            password="strong-password",
        )
        self.assertIn("token", logged_in)

    async def test_duplicate_registration_is_rejected(self) -> None:
        service = AuthService(database_url=None)
        await service.register(
            email="user@example.com",
            password="strong-password",
        )

        with self.assertRaises(AuthConflict):
            await service.register(
                email="USER@example.com",
                password="another-password",
            )

    async def test_wrong_password_is_rejected(self) -> None:
        service = AuthService(database_url=None)
        await service.register(
            email="user@example.com",
            password="strong-password",
        )

        with self.assertRaises(AuthInvalidCredentials):
            await service.login(
                email="user@example.com",
                password="wrong-password",
            )


if __name__ == "__main__":
    unittest.main()
