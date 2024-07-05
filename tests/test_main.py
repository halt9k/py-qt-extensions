import sys
from pathlib import Path
import pytest

from main_window import App
from src.qt_async_button import QAsyncButton


class Test:
    def test_trace_crash(self):
        app = App()
        sys.exit(app.exec())
        assert(True)
