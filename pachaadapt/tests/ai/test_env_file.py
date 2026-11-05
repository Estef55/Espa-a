import tempfile
import unittest
from pathlib import Path

from ai.env_file import load_env_file


class EnvFileTests(unittest.TestCase):
    def test_loads_unquoted_and_quoted_values_without_overriding_process_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                '# config\nPACHAADAPT_AI_PROVIDER=groq\nPACHAADAPT_AI_MODEL="model-v1"\n'
                "PACHAADAPT_AI_API_KEY='secret-value'\nIGNORED_LINE\n",
                encoding="utf-8",
            )
            env = {"PACHAADAPT_AI_PROVIDER": "openai"}
            load_env_file(path, env)
            self.assertEqual(env["PACHAADAPT_AI_PROVIDER"], "openai")
            self.assertEqual(env["PACHAADAPT_AI_MODEL"], "model-v1")
            self.assertEqual(env["PACHAADAPT_AI_API_KEY"], "secret-value")
            self.assertNotIn("IGNORED_LINE", env)

    def test_missing_file_is_a_noop(self):
        env = {}
        load_env_file(Path("missing-file-does-not-exist"), env)
        self.assertEqual(env, {})

    def test_load_settings_reads_project_dotenv_without_exposing_key(self):
        import os
        from unittest.mock import patch
        from ai.settings import load_settings

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".env").write_text(
                "PACHAADAPT_AI_PROVIDER=groq\nPACHAADAPT_AI_BASE_URL=https://provider.example/v1\n"
                "PACHAADAPT_AI_MODEL=example-model\nPACHAADAPT_AI_API_KEY=test-secret\n",
                encoding="utf-8",
            )
            with patch("ai.settings._REPO_ROOT", Path(tmp)), patch.dict(os.environ, {}, clear=True):
                settings = load_settings()
            self.assertEqual(settings.ai_provider, "groq")
            self.assertEqual(settings.ai_base_url, "https://provider.example/v1")
            self.assertEqual(settings.ai_model, "example-model")
            self.assertEqual(settings.ai_api_key, "test-secret")
            self.assertNotIn("test-secret", repr(settings))

    def test_invalid_environment_variable_names_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("NOT VALID=value\nSAFE_NAME=ok\n", encoding="utf-8")
            env = {}
            load_env_file(path, env)
            self.assertNotIn("NOT VALID", env)
            self.assertEqual(env["SAFE_NAME"], "ok")


if __name__ == "__main__":
    unittest.main()
