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
            with self.assertRaises(SystemExit) as cm:
                preflight.check_tool("docker", required=True)
            self.assertEqual(cm.exception.code, 1)

    def test_check_tool_missing_optional_warns(self):
        with patch("shutil.which", return_value=None):
            # Should not exit when required=False
            preflight.check_tool("gh", required=False)

    def test_check_compose_version_valid(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=0, stdout="v2.30.1\n", stderr="")
        with patch("subprocess.run", return_value=mock_res):
            preflight.check_compose_version()

    def test_check_compose_version_too_old_fails(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=0, stdout="v2.29.0\n", stderr="")
        with patch("subprocess.run", return_value=mock_res):
            with self.assertRaises(SystemExit) as cm:
                preflight.check_compose_version()
            self.assertEqual(cm.exception.code, 1)

    def test_check_compose_version_cmd_error_fails(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="plugin missing")
        with patch("subprocess.run", return_value=mock_res):
            with self.assertRaises(SystemExit) as cm:
                preflight.check_compose_version()
            self.assertEqual(cm.exception.code, 1)

    def test_check_docker_daemon_unreachable_fails(self):
        mock_res = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Is the docker daemon running?")
        with patch("subprocess.run", return_value=mock_res):
            with self.assertRaises(SystemExit) as cm:
                preflight.check_docker_daemon()
            self.assertEqual(cm.exception.code, 1)

    def test_check_env_missing_secret_fails(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text("JWT_SECRET=\nMEILI_MASTER_KEY=key\nMONGO_ROOT_PASSWORD=pass\n", encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with self.assertRaises(SystemExit) as cm:
                    preflight.check_env()
                self.assertEqual(cm.exception.code, 1)

    def test_check_env_router_missing_master_key_fails(self):
        env_file = self.tmp_path / ".env"
        env_file.write_text("COMPOSE_PROFILES=router\nJWT_SECRET=jwt\nMEILI_MASTER_KEY=key\nMONGO_ROOT_PASSWORD=pass\nLITELLM_MASTER_KEY=\n", encoding="utf-8")
        with patch.object(preflight, "ENV_PATH", env_file):
            with patch.object(preflight, "ENV_EXAMPLE_PATH", env_file):
                with self.assertRaises(SystemExit) as cm:
                    preflight.check_env()
                self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
