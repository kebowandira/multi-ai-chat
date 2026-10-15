import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class DeployScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

        # Set up mock project directory structure
        self.bin_dir = self.tmp_path / "bin"
        self.bin_dir.mkdir()

        # Copy scripts directory into project root
        self.proj_scripts = self.tmp_path / "scripts"
        shutil.copytree(ROOT / "scripts", self.proj_scripts)

        # Create dummy source templates
        (self.tmp_path / "librechat.yaml").write_text("endpoints:\n  custom: []\n", encoding="utf-8")
        (self.tmp_path / "litellm_config.yaml").write_text("model_list: []\n", encoding="utf-8")

        # Create dummy .env file
        self.env_path = self.tmp_path / ".env"
        self.env_path.write_text(
            "COMPOSE_PROFILES=standalone\n"
            "CHAT_DOMAIN=chat.local\n"
            "JWT_SECRET=jwtsecret123\n"
            "MEILI_MASTER_KEY=meilimasterkey123\n"
            "MONGO_ROOT_PASSWORD=mongorootpass123\n",
            encoding="utf-8",
        )

        # Create fake docker executable
        self.fake_docker = self.bin_dir / "docker"
        self.docker_log = self.tmp_path / "docker_calls.log"

        fake_docker_script = f"""#!/usr/bin/env bash
echo "$@" >> "{self.docker_log}"

if [ "$1" = "info" ]; then
  echo "Server Version: 27.0.0"
  exit 0
fi

if [ "$1" = "compose" ] && [ "$2" = "version" ]; then
  echo "v2.30.1"
  exit 0
fi

if [ "${{MOCK_BAD_COMPOSE:-}}" = "1" ] && [ "$1" = "compose" ] && [ "$2" = "config" ]; then
  echo "error: invalid compose syntax" >&2
  exit 1
fi

if [ "${{MOCK_PULL_FAIL:-}}" = "1" ] && [ "$1" = "compose" ] && [ "$2" = "pull" ]; then
  echo "error: failed to pull image" >&2
  exit 1
fi

if [ "$1" = "compose" ] && [ "$2" = "config" ] && [ "$3" = "--services" ]; then
  if [ "${{MOCK_DISABLED_ROUTER:-}}" = "1" ]; then
    echo -e "librechat\\nmongo"
  else
    echo -e "caddy\\nlibrechat\\nmongo"
  fi
  exit 0
fi

if [ "$1" = "compose" ] && [ "$2" = "ps" ]; then
  if [ "${{MOCK_UNHEALTHY_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "librechat running unhealthy"
    echo "mongo running healthy"
  elif [ "${{MOCK_MISSING_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "mongo running healthy"
  else
    echo "caddy running healthy"
    echo "librechat running healthy"
    echo "mongo running healthy"
  fi
  exit 0
fi

exit 0
"""
        self.fake_docker.write_text(fake_docker_script, encoding="utf-8")
        self.fake_docker.chmod(0o755)

        # Create fake git executable
        fake_git = self.bin_dir / "git"
        fake_git.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_git.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def run_deploy(self, env_extra=None, cwd=None):
        venv_bin = Path(sys.executable).parent
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{venv_bin}:{os.environ.get('PATH', '')}",
            "DEPLOY_TIMEOUT_SEC": "2",
            "DEPLOY_SLEEP_SEC": "0",
        }
        if env_extra:
            env.update(env_extra)

        deploy_script = cwd / "scripts" / "deploy.sh" if cwd else self.proj_scripts / "deploy.sh"
        res = subprocess.run(
            ["bash", str(deploy_script)],
            cwd=cwd or self.tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        return res

    def test_missing_env_fails(self):
        self.env_path.unlink()
        res = self.run_deploy()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("error: .env not found", res.stderr)

    def test_successful_deployment(self):
        res = self.run_deploy()
        self.assertEqual(res.returncode, 0, msg=f"stdout={res.stdout}, stderr={res.stderr}")
        self.assertIn("all services healthy", res.stdout)

        calls = self.docker_log.read_text(encoding="utf-8")
        self.assertIn("compose pull", calls)
        self.assertIn("compose up -d --force-recreate --remove-orphans", calls)
        self.assertIn("caddy validate", calls)

    def test_bad_compose_config_fails(self):
        res = self.run_deploy(env_extra={"MOCK_BAD_COMPOSE": "1"})
        self.assertNotEqual(res.returncode, 0)

    def test_pull_failure_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_PULL_FAIL": "1"})
        self.assertNotEqual(res.returncode, 0)

    def test_unhealthy_service_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_UNHEALTHY_SERVICE": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("unhealthy", res.stderr)

    def test_missing_service_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_MISSING_SERVICE": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("missing", res.stderr)

    def test_standalone_profile_disabled_skips_caddy_validation(self):
        self.env_path.write_text(
            "COMPOSE_PROFILES=\n"
            "JWT_SECRET=jwtsecret123\n"
            "MEILI_MASTER_KEY=meilimasterkey123\n"
            "MONGO_ROOT_PASSWORD=mongorootpass123\n",
            encoding="utf-8",
        )
        res = self.run_deploy(env_extra={"MOCK_DISABLED_ROUTER": "1"})
        self.assertEqual(res.returncode, 0, msg=f"stdout={res.stdout}, stderr={res.stderr}")
        calls = self.docker_log.read_text(encoding="utf-8")
        self.assertNotIn("caddy validate", calls)


if __name__ == "__main__":
    unittest.main()
