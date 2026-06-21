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
