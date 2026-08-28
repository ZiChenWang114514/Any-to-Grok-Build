import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "grok_session.py"
SPEC = importlib.util.spec_from_file_location("grok_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GrokSessionTests(unittest.TestCase):
    def test_any_to_payload_preserves_session(self):
        payload = MODULE.any_to_payload(
            {"ok": True, "session_id": "grok-1", "actual_models": ["grok-4.6-build"]},
            "invoke",
        )
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["target"], "grok-build")
        self.assertEqual(payload["session_id"], "grok-1")
        self.assertEqual(payload["actual_model"], "grok-4.6-build")


if __name__ == "__main__":
    unittest.main()
