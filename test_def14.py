"""DEF-14: validate registration data before creating accounts.

Run from the repository root: python -m unittest test_def14 -v
Each test isolates USER_DB and disables database startup for auth-only checks.
"""

import unittest
from contextlib import ExitStack
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.app.main as api
from backend.app.auth import verify_password


class TestDef14(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(api.USER_DB, {}, clear=True))
        stack.enter_context(patch.object(api, "init_db"))
        self.client = stack.enter_context(TestClient(api.app))
        self.valid = {
            "username": "erik",
            "email": "erik@example.com",
            "password": "Una frase segura 2026",
        }

    def assert_rejected(self, field, value):
        payload = {**self.valid, field: value}
        before = dict(api.USER_DB)
        with patch.object(api, "hash_password", wraps=api.hash_password) as hasher:
            response = self.client.post("/auth/register", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(api.USER_DB, before)
        hasher.assert_not_called()
        invalid_fields = {error["loc"][-1] for error in response.json()["detail"]}
        self.assertIn(field, invalid_fields)

    def test_rejects_empty_username(self):
        self.assert_rejected("username", "")

    def test_rejects_whitespace_username(self):
        self.assert_rejected("username", "   ")

    def test_rejects_short_username(self):
        self.assert_rejected("username", "ab")

    def test_rejects_long_username(self):
        self.assert_rejected("username", "a" * 51)

    def test_rejects_empty_email(self):
        self.assert_rejected("email", "")

    def test_rejects_email_without_at(self):
        self.assert_rejected("email", "not-an-email")

    def test_rejects_incomplete_email_domain(self):
        self.assert_rejected("email", "erik@")

    def test_rejects_empty_password(self):
        self.assert_rejected("password", "")

    def test_rejects_short_password(self):
        self.assert_rejected("password", "a" * 11)

    def test_rejects_long_password(self):
        self.assert_rejected("password", "a" * 129)

    def test_rejects_whitespace_password(self):
        self.assert_rejected("password", " " * 16)

    def test_rejects_missing_fields_without_creating_an_account(self):
        response = self.client.post("/auth/register", json={"username": "erik"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(api.USER_DB, {})

    def test_valid_registration_still_works(self):
        response = self.client.post("/auth/register", json=self.valid)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "erik")
        self.assertTrue(response.json()["access_token"])
        self.assertIn("erik", api.USER_DB)
        self.assertNotIn("password", api.USER_DB["erik"])

    def test_accepts_minimum_lengths(self):
        payload = {**self.valid, "username": "abc", "password": "a" * 12}
        self.assertEqual(self.client.post("/auth/register", json=payload).status_code, 200)

    def test_accepts_maximum_lengths(self):
        payload = {**self.valid, "username": "a" * 50, "password": "a" * 128}
        self.assertEqual(self.client.post("/auth/register", json=payload).status_code, 200)

    def test_normalizes_username_and_allows_login(self):
        response = self.client.post("/auth/register", json={**self.valid, "username": "  erik  "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "erik")
        login = self.client.post("/auth/login", json={
            "username": " erik ", "password": self.valid["password"],
        })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["username"], "erik")

    def test_normalized_duplicate_username_is_rejected(self):
        self.assertEqual(self.client.post("/auth/register", json=self.valid).status_code, 200)
        response = self.client.post("/auth/register", json={**self.valid, "username": " erik "})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(api.USER_DB), {"erik"})

    def test_does_not_trim_password_spaces(self):
        password = "  frase de prueba segura  "
        response = self.client.post("/auth/register", json={**self.valid, "password": password})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(verify_password(password, api.USER_DB["erik"]["hashed_password"]))
        self.assertFalse(verify_password(password.strip(), api.USER_DB["erik"]["hashed_password"]))
        login = self.client.post("/auth/login", json={"username": "erik", "password": password})
        self.assertEqual(login.status_code, 200)


if __name__ == "__main__":
    unittest.main()
