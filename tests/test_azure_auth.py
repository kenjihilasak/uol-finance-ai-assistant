from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.shared.azure_auth import configured_auth_method


class AzureAuthTests(unittest.TestCase):
    def test_interactive_browser_is_the_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_auth_method(), "interactive_browser")

    def test_interactive_browser_can_be_selected(self) -> None:
        with patch.dict(
            os.environ,
            {"AZURE_AUTH_METHOD": "interactive_browser"},
            clear=True,
        ):
            self.assertEqual(configured_auth_method(), "interactive_browser")

    def test_unknown_method_is_rejected(self) -> None:
        with patch.dict(
            os.environ,
            {"AZURE_AUTH_METHOD": "password"},
            clear=True,
        ):
            with self.assertRaises(RuntimeError):
                configured_auth_method()


if __name__ == "__main__":
    unittest.main()
