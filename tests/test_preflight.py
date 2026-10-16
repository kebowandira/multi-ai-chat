import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import preflight  # noqa: E402


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_tool_missing_required_raises(self):
        with patch("shutil.which", return_value=None):
            with patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    preflight.check_tool("docker", required=True)
                self.assertEqual(cm.exception.code, 1)

    def test_check_tool_missing_optional_warns(self):
        with patch("shutil.which", return_value=None):
            preflight.check_tool("gh", required=False)

    def test_check_compose_version_valid(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=0, stdout="v2.30.1\n", stderr="")
        with patch("subprocess.run", return_value=mock_res):
            preflight.check_compose_version()

    def test_check_compose_version_too_old_fails(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=0, stdout="v2.29.0\n", stderr="")
        with patch("subprocess.run", return_value=mock_res):
            with patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    preflight.check_compose_version()
                self.assertEqual(cm.exception.code, 1)

    def test_check_compose_version_cmd_error_fails(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="plugin missing")
        with patch("subprocess.run", return_value=mock_res):
            with patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    preflight.check_compose_version()
                self.assertEqual(cm.exception.code, 1)

    def test_check_docker_daemon_unreachable_fails(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Is the docker daemon running?")
        with patch("subprocess.run", return_value=mock_res):
            with patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    preflight.check_docker_daemon()
                self.assertEqual(cm.exception.code, 1)

    def _create_valid_env_content(self, overrides=None):
        base = {
            "JWT_SECRET": "a" * 64,
            "JWT_REFRESH_SECRET": "b" * 64,
            "CREDS_KEY": "c" * 64,
            "CREDS_IV": "d" * 32,
            "MEILI_MASTER_KEY": "e" * 32,
            "MONGO_ROOT_PASSWORD": "f" * 32,
            "MONGO_APP_PASSWORD": "g" * 32,
            "POSTGRES_PASSWORD": "h" * 32,
            "LITELLM_MASTER_KEY": "i" * 32,
            "LITELLM_SALT_KEY": "j" * 32,
        }
        if overrides:
            base.update(overrides)
        lines = [f"{k}={v}" for k, v in base.items()]
        return "\n".join(lines) + "\n"

    def test_check_env_valid_secrets_succeeds(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text(self._create_valid_env_content(), encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                preflight.check_env()

    def test_check_env_missing_jwt_refresh_secret_fails(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text(self._create_valid_env_content({"JWT_REFRESH_SECRET": ""}), encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with patch("sys.stderr", new=io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as cm:
                        preflight.check_env()
                    self.assertEqual(cm.exception.code, 1)
                    self.assertIn("JWT_REFRESH_SECRET", err.getvalue())

    def test_check_env_missing_creds_key_fails(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text(self._create_valid_env_content({"CREDS_KEY": ""}), encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with patch("sys.stderr", new=io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as cm:
                        preflight.check_env()
                    self.assertEqual(cm.exception.code, 1)
                    self.assertIn("CREDS_KEY", err.getvalue())

    def test_check_env_invalid_creds_key_length_or_format_fails(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text(self._create_valid_env_content({"CREDS_KEY": "1234invalidhex"}), encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with patch("sys.stderr", new=io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as cm:
                        preflight.check_env()
                    self.assertEqual(cm.exception.code, 1)
                    self.assertIn("CREDS_KEY must be a 64-character hex string", err.getvalue())
                    self.assertNotIn("1234invalidhex", err.getvalue())

    def test_check_env_invalid_creds_iv_length_or_format_fails(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text(self._create_valid_env_content({"CREDS_IV": "1234invalidiv"}), encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with patch("sys.stderr", new=io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as cm:
                        preflight.check_env()
                    self.assertEqual(cm.exception.code, 1)
                    self.assertIn("CREDS_IV must be a 32-character hex string", err.getvalue())
                    self.assertNotIn("1234invalidiv", err.getvalue())

    def test_check_env_router_missing_salt_key_fails(self):
        env_file = self.tmp_path / ".env"
        content = self._create_valid_env_content({"LITELLM_SALT_KEY": ""}) + "COMPOSE_PROFILES=router\n"
        env_file.write_text(content, encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with patch("sys.stderr", new=io.StringIO()) as err:
                    with self.assertRaises(SystemExit) as cm:
                        preflight.check_env()
                    self.assertEqual(cm.exception.code, 1)
                    self.assertIn("LITELLM_SALT_KEY", err.getvalue())

    def test_check_env_shell_env_overrides_compose_profiles(self):
        env_file = self.tmp_path / ".env"
        content = self._create_valid_env_content({"LITELLM_SALT_KEY": ""}) + "COMPOSE_PROFILES=standalone\n"
        env_file.write_text(content, encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with patch.dict(os.environ, {"COMPOSE_PROFILES": "router"}):
                    with patch("sys.stderr", new=io.StringIO()) as err:
                        with self.assertRaises(SystemExit) as cm:
                            preflight.check_env()
                        self.assertEqual(cm.exception.code, 1)
                        self.assertIn("LITELLM_SALT_KEY", err.getvalue())

    def test_check_ports_same_project_vs_conflict(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text("COMPOSE_PROFILES=standalone\n", encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "is_project_container_running", return_value=True):
                preflight.check_ports()


if __name__ == "__main__":
    unittest.main()
