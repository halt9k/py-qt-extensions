import sys
from pathlib import Path
import pytest
from PySide6.QtCore import QObject

from main_window import App
from src.helpers.qt import QNTimer
from src.qt_async_button import QAsyncButton


class Test:
    def test_trace_crash(self):
        app = App()

        timer = QNTimer()
        def run_test():
            app.ui.test_button.animateClick()
            timer.continue_loop()
        timer.timeout_n.connect(run_test)
        timer.finished.connect(app.ui.close)
        timer.start(20, 10)

        res = app.exec()
        if res != 0:
            sys.exit(res)
