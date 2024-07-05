import sys
from dataclasses import dataclass
from pathlib import Path

# Qt intellisense pip install PySide6-stubs
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from typing_extensions import override

import src.helpers.os_helpers  # noqa: F401
from src.helpers.qt import QNTimer
from src.qt_async_button import QAsyncButton, QWorker


class MainWindowFrame(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("WinApi message test")
        if not self.objectName():
            self.setObjectName(u"QMainWindow")
        self.resize(400, 300)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.test_button = QAsyncButton(text="Test button", parent=self)


@dataclass(init=True)
class SendData:
    msg: str = ''


class TestWorker(QWorker):
    @override
    def on_run(self):
        self.finished.emit()

    @Slot()
    @override
    def on_finished(self):
        print('finished')


class MainWindow(MainWindowFrame):
    close_event = Signal()
    show_event = Signal()
    send_test_data = Signal(SendData)

    def __init__(self):
        super().__init__()

        def test_worker_factory():
            worker = TestWorker()
            # worker.pick_hwnd.connect(self.on_pick_hwnd)
            return worker
        self.test_button.attach_worker(test_worker_factory)
        self.cb_on_show = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_event.emit()
        event.accept()

    @override
    def showEvent(self, event: QShowEvent) -> None:
        self.show_event.connect(self.after_show_event)
        self.show_event.emit()

    @Slot()
    def after_show_event(self):
        if self.cb_on_show:
            self.cb_on_show()

    @Slot()
    def on_send_data_request(self):
        data = SendData('Test data')
        self.send_message_data.emit(data)


class App(QApplication):
    def __init__(self):
        super().__init__(sys.argv)

        self.ui = MainWindow()
        self.ui.show()