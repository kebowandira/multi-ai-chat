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

        self.bin_dir = self.tmp_path / "bin"
        self.bin_dir.mkdir()

        self.proj_scripts = self.tmp_path / "scripts"
        shutil.copytree(ROOT / "scripts", self.proj_scripts)

        self.proj_router = self.tmp_path / "router"
        shutil.copytree(ROOT / "router", self.proj_router)

        (self.tmp_path / "librechat.yaml").write_text("endpoints:\n  custom: []\n", encoding="utf-8")
        (self.tmp_path / "litellm_config.yaml").write_text("model_list: []\n", encoding="utf-8")

        self.env_path = self.tmp_path / ".env"
        self.env_path.write_text(
            "COMPOSE_PROFILES=standalone\n"
            "CHAT_DOMAIN=chat.local\n"
            "JWT_SECRET=" + "a" * 64 + "\n"
            "JWT_REFRESH_SECRET=" + "b" * 64 + "\n"
            "CREDS_KEY=" + "c" * 64 + "\n"
            "CREDS_IV=" + "d" * 32 + "\n"
            "MEILI_MASTER_KEY=" + "e" * 32 + "\n"
            "MONGO_ROOT_PASSWORD=" + "f" * 32 + "\n"
            "MONGO_APP_PASSWORD=" + "g" * 32 + "\n"
            "POSTGRES_PASSWORD=" + "h" * 32 + "\n"
            "LITELLM_MASTER_KEY=" + "i" * 32 + "\n"
            "LITELLM_SALT_KEY=" + "j" * 32 + "\n",
            encoding="utf-8",
        )

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

if [ "${{MOCK_CONFIG_SERVICES_FAIL:-}}" = "1" ] && [ "$1" = "compose" ] && [ "$2" = "config" ] && [ "$3" = "--services" ]; then
  echo "error: failed to resolve services" >&2
  exit 1
fi

if [ "${{MOCK_PULL_FAIL:-}}" = "1" ] && [ "$1" = "compose" ] && [ "$2" = "pull" ]; then
  echo "error: failed to pull image" >&2
  exit 1
fi

if [ "${{MOCK_PS_FAIL:-}}" = "1" ] && [ "$1" = "compose" ] && [ "$2" = "ps" ]; then
  echo "error: docker compose ps command failed" >&2
  exit 1
fi

if [ "$1" = "compose" ] && [ "$2" = "config" ] && [ "$3" = "--services" ]; then
  if [ "${{MOCK_EMPTY_SERVICES:-}}" = "1" ]; then
    echo ""
  elif [ "${{MOCK_PROFILE_MODE:-}}" = "shared" ]; then
    echo -e "librechat\\nmongodb\\nmeilisearch\\nvectordb\\nrag_api"
  elif [ "${{MOCK_PROFILE_MODE:-}}" = "router" ]; then
    echo -e "litellm\\nlibrechat\\nmongodb\\nmeilisearch\\nvectordb\\nrag_api"
  elif [ "${{MOCK_PROFILE_MODE:-}}" = "standalone_router" ]; then
    echo -e "caddy\\nlitellm\\nlibrechat\\nmongodb\\nmeilisearch\\nvectordb\\nrag_api"
  else
    echo -e "caddy\\nlibrechat\\nmongodb\\nmeilisearch\\nvectordb\\nrag_api"
  fi
  exit 0
fi

if [ "$1" = "compose" ] && [ "$2" = "ps" ]; then
  if [ "${{MOCK_PS_EMPTY:-}}" = "1" ]; then
    echo ""
  elif [ "${{MOCK_UNHEALTHY_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "librechat running unhealthy"
    echo "mongodb running healthy"
  elif [ "${{MOCK_EXITED_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "librechat exited"
    echo "mongodb running healthy"
  elif [ "${{MOCK_RESTARTING_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "librechat restarting"
    echo "mongodb running healthy"
  elif [ "${{MOCK_STARTING_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "librechat running starting"
    echo "mongodb running healthy"
  elif [ "${{MOCK_NO_HEALTHCHECK_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "litellm running healthy"
    echo "librechat running"
    echo "mongodb running healthy"
    echo "meilisearch running healthy"
    echo "vectordb running healthy"
    echo "rag_api running healthy"
  elif [ "${{MOCK_MISSING_SERVICE:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "mongodb running healthy"
  elif [ "${{MOCK_MULTI_REPLICA_FAIL:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "librechat running healthy"
    echo "librechat running unhealthy"
    echo "mongodb running healthy"
  elif [ "${{MOCK_MULTI_REPLICA_OK:-}}" = "1" ]; then
    echo "caddy running healthy"
    echo "librechat running healthy"
    echo "librechat running healthy"
    echo "mongodb running healthy"
    echo "meilisearch running healthy"
    echo "vectordb running healthy"
    echo "rag_api running healthy"
  else
    echo "caddy running healthy"
    echo "litellm running healthy"
    echo "librechat running healthy"
    echo "mongodb running healthy"
    echo "meilisearch running healthy"
    echo "vectordb running healthy"
    echo "rag_api running healthy"
  fi
  exit 0
fi

exit 0
"""
        self.fake_docker.write_text(fake_docker_script, encoding="utf-8")
        self.fake_docker.chmod(0o755)

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
            "DEPLOY_TIMEOUT_SEC": "1",
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

    def test_config_services_discovery_failure_halts_before_mutations(self):
        res = self.run_deploy(env_extra={"MOCK_CONFIG_SERVICES_FAIL": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("failed to query docker compose services", res.stderr)
        calls = self.docker_log.read_text(encoding="utf-8")
        self.assertNotIn("caddy validate", calls)
        self.assertNotIn("compose pull", calls)
        self.assertNotIn("compose up", calls)

    def test_empty_expected_services_halts_before_mutations(self):
        res = self.run_deploy(env_extra={"MOCK_EMPTY_SERVICES": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("no expected services found", res.stderr)
        calls = self.docker_log.read_text(encoding="utf-8")
        self.assertNotIn("caddy validate", calls)
        self.assertNotIn("compose pull", calls)
        self.assertNotIn("compose up", calls)

    def test_pull_failure_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_PULL_FAIL": "1"})
        self.assertNotEqual(res.returncode, 0)

    def test_ps_failure_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_PS_FAIL": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("failed to query docker compose container states", res.stderr)

    def test_ps_empty_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_PS_EMPTY": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("missing/not created", res.stderr)

    def test_unhealthy_service_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_UNHEALTHY_SERVICE": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("unhealthy", res.stderr)

    def test_exited_service_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_EXITED_SERVICE": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("exited", res.stderr)

    def test_restarting_service_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_RESTARTING_SERVICE": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("restarting", res.stderr)

    def test_starting_service_timeout_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_STARTING_SERVICE": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("starting", res.stderr)

    def test_missing_service_causes_deploy_failure(self):
        res = self.run_deploy(env_extra={"MOCK_MISSING_SERVICE": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("missing", res.stderr)

    def test_multi_replica_fail(self):
        res = self.run_deploy(env_extra={"MOCK_MULTI_REPLICA_FAIL": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("unhealthy", res.stderr)

    def test_multi_replica_ok(self):
        res = self.run_deploy(env_extra={"MOCK_MULTI_REPLICA_OK": "1"})
        self.assertEqual(res.returncode, 0, msg=f"stdout={res.stdout}, stderr={res.stderr}")

    def test_no_healthcheck_running_service_succeeds(self):
        res = self.run_deploy(env_extra={"MOCK_NO_HEALTHCHECK_SERVICE": "1"})
        self.assertEqual(res.returncode, 0, msg=f"stdout={res.stdout}, stderr={res.stderr}")
        self.assertIn("all services healthy", res.stdout)

    def test_standalone_profile_disabled_skips_caddy_validation(self):
        self.env_path.write_text(
            "COMPOSE_PROFILES=\n"
            "JWT_SECRET=" + "a" * 64 + "\n"
            "JWT_REFRESH_SECRET=" + "b" * 64 + "\n"
            "CREDS_KEY=" + "c" * 64 + "\n"
            "CREDS_IV=" + "d" * 32 + "\n"
            "MEILI_MASTER_KEY=" + "e" * 32 + "\n"
            "MONGO_ROOT_PASSWORD=" + "f" * 32 + "\n"
            "MONGO_APP_PASSWORD=" + "g" * 32 + "\n"
            "POSTGRES_PASSWORD=" + "h" * 32 + "\n",
            encoding="utf-8",
        )
        res = self.run_deploy(env_extra={"MOCK_PROFILE_MODE": "shared"})
        self.assertEqual(res.returncode, 0, msg=f"stdout={res.stdout}, stderr={res.stderr}")
        calls = self.docker_log.read_text(encoding="utf-8")
        self.assertNotIn("caddy validate", calls)

    def test_router_profile_mode(self):
        self.env_path.write_text(
            "COMPOSE_PROFILES=router\n"
            "JWT_SECRET=" + "a" * 64 + "\n"
            "JWT_REFRESH_SECRET=" + "b" * 64 + "\n"
            "CREDS_KEY=" + "c" * 64 + "\n"
            "CREDS_IV=" + "d" * 32 + "\n"
            "MEILI_MASTER_KEY=" + "e" * 32 + "\n"
            "MONGO_ROOT_PASSWORD=" + "f" * 32 + "\n"
            "MONGO_APP_PASSWORD=" + "g" * 32 + "\n"
            "POSTGRES_PASSWORD=" + "h" * 32 + "\n"
            "LITELLM_MASTER_KEY=" + "i" * 32 + "\n"
            "LITELLM_SALT_KEY=" + "j" * 32 + "\n",
            encoding="utf-8",
        )
        res = self.run_deploy(env_extra={"MOCK_PROFILE_MODE": "router"})
        self.assertEqual(res.returncode, 0, msg=f"stdout={res.stdout}, stderr={res.stderr}")

    def test_standalone_and_router_profile_mode(self):
        self.env_path.write_text(
            "COMPOSE_PROFILES=standalone,router\n"
            "JWT_SECRET=" + "a" * 64 + "\n"
            "JWT_REFRESH_SECRET=" + "b" * 64 + "\n"
            "CREDS_KEY=" + "c" * 64 + "\n"
            "CREDS_IV=" + "d" * 32 + "\n"
            "MEILI_MASTER_KEY=" + "e" * 32 + "\n"
            "MONGO_ROOT_PASSWORD=" + "f" * 32 + "\n"
            "MONGO_APP_PASSWORD=" + "g" * 32 + "\n"
            "POSTGRES_PASSWORD=" + "h" * 32 + "\n"
            "LITELLM_MASTER_KEY=" + "i" * 32 + "\n"
            "LITELLM_SALT_KEY=" + "j" * 32 + "\n",
            encoding="utf-8",
        )
        res = self.run_deploy(env_extra={"MOCK_PROFILE_MODE": "standalone_router"})
        self.assertEqual(res.returncode, 0, msg=f"stdout={res.stdout}, stderr={res.stderr}")
        calls = self.docker_log.read_text(encoding="utf-8")
        self.assertIn("caddy validate", calls)


if __name__ == "__main__":
    unittest.main()
