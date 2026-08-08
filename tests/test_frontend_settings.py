import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "src"))


class DummyContainer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def write(self, *args, **kwargs):
        return None

    def markdown(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def header(self, *args, **kwargs):
        return None

    def divider(self, *args, **kwargs):
        return None

    def subheader(self, *args, **kwargs):
        return None

    def metric(self, *args, **kwargs):
        return None

    def title(self, *args, **kwargs):
        return None

    def expander(self, *args, **kwargs):
        return self

    def button(self, *args, **kwargs):
        return False

    def number_input(self, *args, **kwargs):
        return kwargs.get("value", 0)

    def selectbox(self, *args, **kwargs):
        options = kwargs.get("options", [])
        return options[0] if options else None

    def text_input(self, *args, **kwargs):
        return ""

    def file_uploader(self, *args, **kwargs):
        return None

    def download_button(self, *args, **kwargs):
        return None

    def columns(self, *args, **kwargs):
        return [DummyContainer() for _ in range(1)]


class DummyStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.session_state = {}
        self.query_params = {}
        self.sidebar = DummyContainer()

    def set_page_config(self, *args, **kwargs):
        return None

    def cache_data(self, func=None):
        if func is None:
            return lambda f: f
        return func

    def columns(self, *args, **kwargs):
        return [DummyContainer() for _ in range(len(args[0]) if args else 1)]

    def spinner(self, *args, **kwargs):
        return DummyContainer()

    def toast(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def rerun(self):
        return None


streamlit_stub = DummyStreamlit()
sys.modules.setdefault("streamlit", streamlit_stub)

import frontend


def test_load_settings_returns_saved_value(monkeypatch):
    class FakeResponse:
        def __init__(self, status_code, payload=None, text=""):
            self.status_code = status_code
            self._payload = payload or {}
            self.text = text

        def json(self):
            return self._payload

    def fake_get(url, timeout=5):
        return FakeResponse(200, {"value": "42"})

    monkeypatch.setattr(frontend.requests, "get", fake_get)

    value, success = frontend.load_settings(retries=1, retry_delay=0)
    assert success is True
    assert value == 42
