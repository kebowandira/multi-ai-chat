import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

pin = importlib.import_module("pin-images")


class PinImagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_match_repo_digest_simple(self):
        digests = ["docker.io/library/mongo@sha256:abc12345"]
        matched = pin.match_repo_digest("mongo:latest", digests)
        self.assertEqual(matched, "docker.io/library/mongo@sha256:abc12345")

    def test_match_repo_digest_registry_with_port(self):
        digests = ["registry.example.com:5000/my-image@sha256:789def"]
        matched = pin.match_repo_digest("registry.example.com:5000/my-image:v2", digests)
        self.assertEqual(matched, "registry.example.com:5000/my-image@sha256:789def")

    def test_match_repo_digest_unrelated_repo_fails(self):
        digests = ["other.example/evil@sha256:abc"]
        with self.assertRaises(SystemExit):
            pin.match_repo_digest("trusted.example/team/app:v1", digests)

    def test_load_compose_services_config_failure_dies(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Compose config error")
        with patch("subprocess.run", return_value=mock_res):
            with self.assertRaises(SystemExit):
                pin.load_compose_services()

    def test_atomic_file_preservation_on_failure(self):
        override_file = self.tmp_path / "docker-compose.override.yml"
        lock_file = self.tmp_path / "image-lock.json"

        override_file.write_text("existing override", encoding="utf-8")
        lock_file.write_text('{"existing": "lock"}', encoding="utf-8")

        compose_file = self.tmp_path / "docker-compose.yml"
        compose_file.write_text("services:\n  app:\n    image: app:latest\n", encoding="utf-8")

        with patch.object(pin, "COMPOSE_PATH", compose_file):
            with patch.object(pin, "OVERRIDE_PATH", override_file):
                with patch.object(pin, "LOCK_PATH", lock_file):
                    with patch.object(pin, "resolve_digest", side_effect=SystemExit(1)):
                        with self.assertRaises(SystemExit):
                            pin.main()

        # Existing files must be preserved unchanged
        self.assertEqual(override_file.read_text(encoding="utf-8"), "existing override")
        self.assertEqual(lock_file.read_text(encoding="utf-8"), '{"existing": "lock"}')


if __name__ == "__main__":
    unittest.main()
