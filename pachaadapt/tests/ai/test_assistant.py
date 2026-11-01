import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from urllib.error import URLError

from tests._bootstrap import TempContainerMixin, make_settings
from ai.model_gateway import NotConfiguredProvider, OpenAICompatibleProvider, build_provider
from app.services.container import Container
from ai.errors import (EmptyProviderResponse, NotFound, ProviderError, ProviderNotConfigured,
                                    ProviderTimeout, ValidationError)


class _Handler(BaseHTTPRequestHandler):
    """Servidor HTTP LOCAL SOLO PARA PRUEBAS que habla el protocolo /chat/completions.
    No forma parte del producto: permite ejercitar el cliente HTTP real."""
    mode = "ok"
    seen: list = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        mode = type(self).mode
        if mode == "slow":
            time.sleep(2)
        if mode == "http500":
            self.send_response(500); self.end_headers(); return
        if mode == "garbage":
            payload = b"no es json"
        else:
            content = "" if mode == "empty" else "Respuesta de prueba del servidor local"
            payload = json.dumps({"model": "m-test", "choices": [{"message": {"content": content}}]}).encode()
        try:
            self.send_response(200); self.send_header("Content-Length", str(len(payload))); self.end_headers()
            self.wfile.write(payload)
        except OSError:
            pass


class AssistantTests(TempContainerMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/v1"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()

    def setUp(self):
        super().setUp()
        _Handler.mode, _Handler.seen = "ok", []
        self.settings = make_settings(self._tmp.name, ai_provider="openai_compatible", ai_base_url=self.url,
                                      ai_model="m-test", ai_api_key="SECRET-KEY", ai_timeout=1.0)
        self.c = Container(self.settings)

    def test_valid_request_and_labels(self):
        r = self.c.assistant.chat("t1", "¿Cómo explico fracciones?")
        self.assertEqual(r["answer"], "Respuesta de prueba del servidor local")
        self.assertTrue(r["generated_by_model"])
        self.assertIsNone(r["document_context"])
        self.assertNotIn("SECRET-KEY", json.dumps(r))                 # la clave no sale del servidor
        sent = _Handler.seen[0]
        self.assertTrue(sent["path"].endswith("/chat/completions"))
        self.assertEqual(sent["auth"], "Bearer SECRET-KEY")
        self.assertIn("No inventes", sent["body"]["messages"][0]["content"])

    def test_empty_question(self):
        for q in ("", "   ", None, "x" * 4001):
            with self.assertRaises(ValidationError):
                self.c.assistant.chat("t1", q)
        self.assertEqual(_Handler.seen, [])                           # ni se llamó al proveedor

    def test_provider_not_configured(self):
        c = Container(make_settings(self._tmp.name))
        self.assertIsInstance(c.provider, NotConfiguredProvider)
        with self.assertRaises(ProviderNotConfigured):
            c.assistant.chat("t1", "hola")
        self.assertFalse(c.assistant.provider_configured)
        # no quedó ninguna conversación guardada
        with c.db.read() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM i3_conversations").fetchone()[0], 0)

    def test_provider_errors(self):
        for mode, exc in (("slow", ProviderTimeout), ("http500", ProviderError),
                          ("garbage", ProviderError), ("empty", EmptyProviderResponse)):
            _Handler.mode = mode
            with self.assertRaises(exc, msg=mode):
                self.c.assistant.chat("t1", "hola")
        with self.c.db.read() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM i3_messages").fetchone()[0], 0)

    def test_connection_refused_is_controlled(self):
        p = OpenAICompatibleProvider("http://127.0.0.1:9/v1", "m", timeout=1)
        with patch("urllib.request.urlopen", side_effect=URLError(ConnectionRefusedError("refused"))):
            with self.assertRaises(ProviderError):
                p.generate([{"role": "user", "content": "x"}], 10)

    def test_document_context_authorized_and_unauthorized(self):
        d = self.c.documents.create("t1", "Ecosistemas", "Los ecosistemas incluyen productores.")
        r = self.c.assistant.chat("t1", "Resume el documento", document_id=d["id"])
        self.assertEqual(r["document_context"]["document_id"], d["id"])
        self.assertIn("Los ecosistemas incluyen productores.", _Handler.seen[-1]["body"]["messages"][0]["content"])
        n = len(_Handler.seen)
        with self.assertRaises(NotFound):                              # documento de otro docente
            self.c.assistant.chat("t2", "Resume", document_id=d["id"])
        self.assertEqual(len(_Handler.seen), n)                        # su contenido nunca llegó al modelo

    def test_conversation_context_and_privacy(self):
        r1 = self.c.assistant.chat("t1", "primera")
        self.c.assistant.chat("t1", "segunda", conversation_id=r1["conversation_id"])
        roles = [m["role"] for m in _Handler.seen[-1]["body"]["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant", "user"])
        self.assertEqual(len(self.c.assistant.get_conversation("t1", r1["conversation_id"])["messages"]), 4)
        with self.assertRaises(NotFound):
            self.c.assistant.chat("t2", "intruso", conversation_id=r1["conversation_id"])
        with self.assertRaises(NotFound):
            self.c.assistant.get_conversation("t2", r1["conversation_id"])

    def test_preferences_are_applied(self):
        self.c.preferences.update("t1", {"tone": "cercano", "length": "corta"})
        r = self.c.assistant.chat("t1", "hola")
        self.assertEqual(r["preferences_applied"]["tone"], "cercano")
        self.assertIn("tono: cercano", _Handler.seen[-1]["body"]["messages"][0]["content"])

    def test_document_truncation_is_flagged(self):
        d = self.c.documents.create("t1", "Largo", "a" * 20_000)
        r = self.c.assistant.chat("t1", "resume", document_id=d["id"])
        self.assertTrue(r["document_context"]["truncated"])

    def test_build_provider_requires_full_config(self):
        self.assertIsInstance(build_provider(make_settings(self._tmp.name, ai_provider="openai_compatible")),
                              NotConfiguredProvider)
        self.assertNotIn("SECRET-KEY", repr(self.settings))


if __name__ == "__main__":
    unittest.main()
