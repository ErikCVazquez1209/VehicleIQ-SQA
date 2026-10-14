"""DEF-12: specialized password hashing with individual random salts.

Run: python -m unittest test_def12 -v
Each test uses an isolated in-memory user dictionary; no telemetry DB access.
"""

import hashlib
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

import backend.app.auth as auth
import backend.app.main as api


class TestDef12(unittest.TestCase):
    def setUp(self):
        self.demo_record = dict(auth.USER_DB.get("admin", {}))
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(api.USER_DB, {}, clear=True))
        stack.enter_context(patch.object(api, "init_db"))
        self.client = stack.enter_context(TestClient(api.app))
        self.password = "Una frase segura 2026"

    def register(self, username="erik"):
        return self.client.post("/auth/register", json={
            "username": username, "email": f"{username}@example.com", "password": self.password,
        })

    def test_hash_is_a_valid_argon2id_encoding(self):
        hashed = auth.hash_password(self.password)
        self.assertTrue(hashed.startswith("$argon2id$"))
        # Verify using argon2-cffi directly, independently of our wrapper.
        self.assertTrue(PasswordHasher().verify(hashed, self.password))

    def test_same_password_produces_different_hashes(self):
        self.assertNotEqual(auth.hash_password(self.password), auth.hash_password(self.password))

    def test_salt_is_random_for_each_hash(self):
        first = auth.hash_password(self.password)
        second = auth.hash_password(self.password)
        self.assertTrue(first.startswith("$argon2id$"))
        self.assertTrue(second.startswith("$argon2id$"))
        self.assertNotEqual(first.split("$")[4], second.split("$")[4])

    def test_correct_password_is_accepted(self):
        hashed = auth.hash_password(self.password)
        self.assertTrue(auth.verify_password(self.password, hashed))

    def test_wrong_password_is_rejected(self):
        hashed = auth.hash_password(self.password)
        self.assertFalse(auth.verify_password("Otra frase diferente 2026", hashed))

    def test_password_spaces_are_preserved(self):
        password = "  frase de prueba segura  "
        hashed = auth.hash_password(password)
        self.assertTrue(auth.verify_password(password, hashed))
        self.assertFalse(auth.verify_password(password.strip(), hashed))

    def test_unknown_hash_returns_false_without_crashing(self):
        self.assertFalse(auth.verify_password(self.password, "not-a-password-hash"))

    def test_malformed_argon2_hash_returns_false(self):
        self.assertFalse(auth.verify_password(self.password, "$argon2id$malformed"))

    def test_legacy_sha256_format_is_not_accepted(self):
        old_hash = "pbkdf2:sha256:" + hashlib.sha256(
            ("vehicleiq_salt_" + self.password).encode(),
        ).hexdigest()
        self.assertFalse(auth.verify_password(self.password, old_hash))

    def test_registration_stores_argon2_and_login_still_works(self):
        self.assertEqual(self.register().status_code, 200)
        stored = api.USER_DB["erik"]["hashed_password"]
        self.assertTrue(stored.startswith("$argon2id$"))
        self.assertNotEqual(stored, self.password)
        login = self.client.post("/auth/login", json={"username": "erik", "password": self.password})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["access_token"])

    def test_two_accounts_with_same_password_have_different_hashes(self):
        self.assertEqual(self.register("erik_a").status_code, 200)
        self.assertEqual(self.register("erik_b").status_code, 200)
        self.assertNotEqual(api.USER_DB["erik_a"]["hashed_password"],
                            api.USER_DB["erik_b"]["hashed_password"])

    def test_login_with_corrupt_stored_hash_returns_401(self):
        api.USER_DB["erik"] = {"username": "erik", "hashed_password": "invalid"}
        response = self.client.post("/auth/login", json={"username": "erik", "password": self.password})
        self.assertEqual(response.status_code, 401)

    def test_demo_admin_uses_a_valid_new_hash(self):
        self.assertIn("hashed_password", self.demo_record)
        self.assertTrue(auth.verify_password("VehicleIQ-demo-2026", self.demo_record["hashed_password"]))

    def test_full_128_character_password_is_verified_without_truncation(self):
        password = "a" * 127 + "X"
        hashed = auth.hash_password(password)
        self.assertTrue(auth.verify_password(password, hashed))
        self.assertFalse(auth.verify_password("a" * 127 + "Y", hashed))


if __name__ == "__main__":
    unittest.main()
