import io
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

pin = importlib.import_module("pin-images")

SHA256_A = "sha256:1111111111111111111111111111111111111111111111111111111111111111"
SHA256_B = "sha256:2222222222222222222222222222222222222222222222222222222222222222"


class PinImagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_match_repo_digest_simple(self):
        digests = [f"docker.io/library/mongo@{SHA256_A}"]
        matched = pin.match_repo_digest("mongo:latest", digests)
        self.assertEqual(matched, f"docker.io/library/mongo@{SHA256_A}")

    def test_match_repo_digest_docker_hub_aliases(self):
        digests = [f"library/mongo@{SHA256_A}"]
        matched = pin.match_repo_digest("mongo:latest", digests)
        self.assertEqual(matched, f"library/mongo@{SHA256_A}")

        digests2 = [f"index.docker.io/library/mongo@{SHA256_A}"]
        matched2 = pin.match_repo_digest("mongo:latest", digests2)
        self.assertEqual(matched2, f"index.docker.io/library/mongo@{SHA256_A}")

    def test_match_repo_digest_registry_with_port(self):
        digests = [f"registry.example.com:5000/my-image@{SHA256_A}"]
        matched = pin.match_repo_digest("registry.example.com:5000/my-image:v2", digests)
        self.assertEqual(matched, f"registry.example.com:5000/my-image@{SHA256_A}")

    def test_match_repo_digest_unrelated_repo_fails(self):
        digests = [f"other.example/evil@{SHA256_A}"]
        with patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit):
                pin.match_repo_digest("trusted.example/team/app:v1", digests)

    def test_match_repo_digest_unrelated_same_basename_registry_fails(self):
        digests = [f"evil.com/evil/mongo@{SHA256_A}"]
        with patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit):
                pin.match_repo_digest("mongo:latest", digests)

    def test_match_repo_digest_malformed_digest_fails(self):
        digests = ["malformed_digest_without_at_symbol", "mongo@not_a_valid_sha256"]
        with patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit):
                pin.match_repo_digest("mongo:latest", digests)

    def test_resolve_digest_requested_digest_mismatch_fails(self):
        mock_pull = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        mock_inspect = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=f"docker.io/library/mongo@{SHA256_B}", stderr=""
        )

        with patch("subprocess.run", side_effect=[mock_pull, mock_inspect]):
            with patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit):
                    pin.resolve_digest(f"mongo@{SHA256_A}")

    def test_load_compose_services_includes_all_profiles(self):
        mock_output = json.dumps({"services": {"caddy": {"image": "caddy:2"}, "litellm": {"image": "litellm:latest"}}})
        mock_res = subprocess.CompletedProcess(args=[], returncode=0, stdout=mock_output, stderr="")
        with patch("subprocess.run", return_value=mock_res) as mock_run:
            services = pin.load_compose_services()
            self.assertEqual(services, {"caddy": "caddy:2", "litellm": "litellm:latest"})
            called_cmd = mock_run.call_args[0][0]
            self.assertIn("--profile", called_cmd)
            self.assertIn("*", called_cmd)

    def test_load_compose_services_config_failure_dies(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Compose config error")
        with patch("subprocess.run", return_value=mock_res):
            with patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit):
                    pin.load_compose_services()

    def _run_pin_main_with_injected_error(
        self, preexisting: bool, write_override_err=False, write_lock_err=False, replace_override_err=False, replace_lock_err=False
    ):
        override_file = self.tmp_path / "docker-compose.override.yml"
        lock_file = self.tmp_path / "image-lock.json"

        orig_override = "existing override content"
        orig_lock = '{"existing": "lock content"}'

        if preexisting:
            override_file.write_text(orig_override, encoding="utf-8")
            lock_file.write_text(orig_lock, encoding="utf-8")

        mock_services = {"app": "app:latest"}
        mock_digest = f"docker.io/library/app@{SHA256_A}"

        tmp_override = override_file.with_suffix(".tmp")
        tmp_lock = lock_file.with_suffix(".tmp")
        bak_override = override_file.with_suffix(".bak")
        bak_lock = lock_file.with_suffix(".bak")

        real_write_text = Path.write_text
        real_replace = Path.replace

        def custom_write_text(path_obj, data, encoding="utf-8"):
            if write_override_err and path_obj == tmp_override:
                raise OSError("Disk write error override")
            if write_lock_err and path_obj == tmp_lock:
                raise OSError("Disk write error lock")
            return real_write_text(path_obj, data, encoding=encoding)

        def custom_replace(path_obj, target):
            if replace_override_err and path_obj == tmp_override:
                raise OSError("Rename error override")
            if replace_lock_err and path_obj == tmp_lock:
                raise OSError("Rename error lock")
            return real_replace(path_obj, target)

        with patch.object(pin, "OVERRIDE_PATH", override_file):
            with patch.object(pin, "LOCK_PATH", lock_file):
                with patch.object(pin, "load_compose_services", return_value=mock_services):
                    with patch.object(pin, "resolve_digest", return_value=mock_digest):
                        with patch.object(Path, "write_text", side_effect=custom_write_text):
                            with patch.object(Path, "replace", side_effect=custom_replace):
                                with patch("sys.stderr", new=io.StringIO()):
                                    with self.assertRaises(SystemExit):
                                        pin.main()

        if preexisting:
            self.assertTrue(override_file.exists())
            self.assertEqual(override_file.read_text(encoding="utf-8"), orig_override)
            self.assertTrue(lock_file.exists())
            self.assertEqual(lock_file.read_text(encoding="utf-8"), orig_lock)
        else:
            self.assertFalse(override_file.exists())
            self.assertFalse(lock_file.exists())

        self.assertFalse(tmp_override.exists())
        self.assertFalse(tmp_lock.exists())
        self.assertFalse(bak_override.exists())
        self.assertFalse(bak_lock.exists())

    def test_write_override_failure_rollback_preexisting(self):
        self._run_pin_main_with_injected_error(preexisting=True, write_override_err=True)

    def test_write_override_failure_rollback_absent(self):
        self._run_pin_main_with_injected_error(preexisting=False, write_override_err=True)

    def test_write_lock_failure_rollback_preexisting(self):
        self._run_pin_main_with_injected_error(preexisting=True, write_lock_err=True)

    def test_write_lock_failure_rollback_absent(self):
        self._run_pin_main_with_injected_error(preexisting=False, write_lock_err=True)

    def test_replace_override_failure_rollback_preexisting(self):
        self._run_pin_main_with_injected_error(preexisting=True, replace_override_err=True)

    def test_replace_override_failure_rollback_absent(self):
        self._run_pin_main_with_injected_error(preexisting=False, replace_override_err=True)

    def test_replace_lock_failure_second_rename_rollback_preexisting(self):
        self._run_pin_main_with_injected_error(preexisting=True, replace_lock_err=True)

    def test_replace_lock_failure_second_rename_rollback_absent(self):
        self._run_pin_main_with_injected_error(preexisting=False, replace_lock_err=True)


if __name__ == "__main__":
    unittest.main()
