import string
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import app.core.bootstrap as bootstrap
from app.utils.password import (
    BOOTSTRAP_ADMIN_PASSWORD_CHARACTERS,
    BOOTSTRAP_ADMIN_PASSWORD_LENGTH,
    BOOTSTRAP_ADMIN_PASSWORD_SYMBOLS,
    generate_bootstrap_admin_password,
)


class BootstrapPasswordGenerationTestCase(unittest.TestCase):
    def test_generate_bootstrap_admin_password_uses_digits_and_symbols_only(self) -> None:
        password = generate_bootstrap_admin_password()

        self.assertEqual(len(password), BOOTSTRAP_ADMIN_PASSWORD_LENGTH)
        self.assertTrue(all(char in BOOTSTRAP_ADMIN_PASSWORD_CHARACTERS for char in password))
        self.assertTrue(any(char in string.digits for char in password))
        self.assertTrue(any(char in BOOTSTRAP_ADMIN_PASSWORD_SYMBOLS for char in password))


class InitSuperuserTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_blank_initial_password_auto_generates_bootstrap_password(self) -> None:
        generated_password = "12!@#34$%^&?"
        created_user = SimpleNamespace(username="admin")
        get_or_create_mock = AsyncMock(return_value=(created_user, True))

        with (
            patch("app.core.bootstrap.user_repository.exists_any", new=AsyncMock(return_value=False)),
            patch.object(bootstrap.settings, "INITIAL_ADMIN_PASSWORD", ""),
            patch("app.core.bootstrap.generate_bootstrap_admin_password", return_value=generated_password),
            patch("app.core.bootstrap.get_password_hash", return_value="hashed-password") as hash_mock,
            patch("app.core.bootstrap.User.get_or_create", new=get_or_create_mock),
            patch("app.core.bootstrap.validate_password_strength") as validate_mock,
            patch("app.core.bootstrap.emit_bootstrap_admin_password") as emit_mock,
        ):
            result = await bootstrap.init_superuser()

        self.assertIs(result, created_user)
        validate_mock.assert_not_called()
        hash_mock.assert_called_once_with(generated_password)
        get_or_create_mock.assert_awaited_once_with(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "nickname": "admin",
                "phone": None,
                "password": "hashed-password",
                "is_active": True,
                "is_superuser": True,
            },
        )
        emit_mock.assert_called_once_with("admin", generated_password)

    async def test_explicit_initial_password_still_uses_password_policy(self) -> None:
        explicit_password = "StrongPass1!"
        created_user = SimpleNamespace(username="admin")
        get_or_create_mock = AsyncMock(return_value=(created_user, True))

        with (
            patch("app.core.bootstrap.user_repository.exists_any", new=AsyncMock(return_value=False)),
            patch.object(bootstrap.settings, "INITIAL_ADMIN_PASSWORD", explicit_password),
            patch("app.core.bootstrap.get_password_hash", return_value="hashed-password") as hash_mock,
            patch("app.core.bootstrap.User.get_or_create", new=get_or_create_mock),
            patch(
                "app.core.bootstrap.validate_password_strength",
                return_value=(True, ""),
            ) as validate_mock,
            patch("app.core.bootstrap.generate_bootstrap_admin_password") as generator_mock,
            patch("app.core.bootstrap.emit_bootstrap_admin_password") as emit_mock,
        ):
            result = await bootstrap.init_superuser()

        self.assertIs(result, created_user)
        validate_mock.assert_called_once_with(explicit_password)
        generator_mock.assert_not_called()
        hash_mock.assert_called_once_with(explicit_password)
        get_or_create_mock.assert_awaited_once()
        emit_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
