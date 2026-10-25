"""Credential provisioning tests use newly generated, test-only RSA material."""
import support
from datetime import timedelta
import importlib
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from test_camera import pkg

credentials = importlib.import_module("custom_components.bambu_open_network.credentials")
ROOT = Path(__file__).resolve().parents[1]


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root / "bambu_open_network/credentials"
    def tearDown(self):
        self.tmp.cleanup()
    def manager(self, mode="success", folder=None):
        return credentials.CredentialManager(
            [sys.executable, str(ROOT / "tests/fake_credentials_worker.py"), mode],
            folder or self.folder, self.root)

    def test_missing_material_is_provisioned_into_standard_persistent_folder(self):
        manager = self.manager()
        self.assertTrue(manager.ensure())
        self.assertEqual(manager.status, "ready")
        self.assertTrue(credentials.valid_material(self.folder))
        self.assertEqual({p.name for p in self.folder.iterdir()}, set(credentials.FILES))

    def test_valid_existing_material_is_reused_without_network_or_rewrite(self):
        self.assertTrue(self.manager().ensure())
        original = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        manager = self.manager("failed")
        with patch.object(credentials.subprocess, "run",
                          side_effect=AssertionError("Unexpected network request")):
            self.assertFalse(manager.ensure())
        self.assertEqual(manager.status, "ready")
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.folder.iterdir()})

    def test_rejected_partial_fetch_restores_previous_files(self):
        self.folder.mkdir(parents=True)
        (self.folder / "slicer_cert.pem").write_bytes(b"previous material")
        manager = self.manager("failed")
        self.assertFalse(manager.ensure())
        self.assertEqual(manager.status, "provision_failed")
        self.assertEqual((self.folder / "slicer_cert.pem").read_bytes(), b"previous material")
        self.assertFalse((self.folder / "slicer_key.pem").exists())

    def test_invalid_success_response_is_not_installed(self):
        manager = self.manager("invalid")
        self.assertFalse(manager.ensure())
        self.assertEqual(manager.status, "provision_failed")
        self.assertFalse(any((self.folder / name).exists() for name in credentials.FILES))

    def test_mismatched_key_is_not_accepted(self):
        self.assertTrue(self.manager().ensure())
        other = self.root / "other"
        self.assertTrue(self.manager(folder=other).ensure())
        (self.folder / "slicer_key.pem").write_bytes((other / "slicer_key.pem").read_bytes())
        self.assertFalse(credentials.valid_material(self.folder))
        self.assertTrue(self.manager().ensure())
        self.assertTrue(credentials.valid_material(self.folder))

    def test_refresh_threshold_detects_expiring_material(self):
        self.assertTrue(self.manager().ensure())
        self.assertFalse(credentials.valid_material(
            self.folder, refresh_before=timedelta(days=31)))

    def test_outside_config_folder_is_rejected_before_process_launch(self):
        manager = self.manager(folder=self.root.parent / "not-this-config")
        with patch.object(credentials.subprocess, "run",
                          side_effect=AssertionError("Unexpected process")):
            self.assertFalse(manager.ensure())
        self.assertEqual(manager.status, "invalid_folder")

    def test_concurrent_refresh_is_not_duplicated(self):
        manager = self.manager()
        manager._lock.acquire()
        try:
            with patch.object(credentials.subprocess, "run",
                              side_effect=AssertionError("Concurrent request")):
                self.assertFalse(manager.ensure())
        finally:
            manager._lock.release()
