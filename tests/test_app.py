"""Browser-independent Streamlit interaction checks."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class DashboardTests(unittest.TestCase):
    def test_default_dashboard_and_research_button(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn("joint_study", app.session_state)
        next(item for item in app.button if item.label == "Run joint-risk experiment").click().run()
        self.assertEqual(len(app.exception), 0)
        result = app.session_state["joint_study"]
        self.assertEqual(result["status"], "sample-optimal")
        self.assertEqual(len(result["comparison"]), 4)
        self.assertNotEqual(result["train_seed"], result["test_seed"])

    def test_all_zero_priorities_show_message_not_exception(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        for label in ("Cost", "Risk", "Time", "Carbon"):
            next(item for item in app.slider if item.label == label).set_value(0)
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("weight above zero" in warning.value for warning in app.warning))


if __name__ == "__main__":
    unittest.main()
