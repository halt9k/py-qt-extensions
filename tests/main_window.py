import sys
from dataclasses import dataclass
from pathlib import Path

# Qt intellisense pip install PySide6-stubs
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from typing_extensions import override

import helpers.os_helpers  # noqa: F401
from qt_async_button import QAsyncButton, QWorker


class MainWindowFrame(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("WinApi message test")
        if not self.objectName():
            self.setObjectName(u"QMainWindow")
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.test_button = QAsyncButton(text="Pick under cursor...", parent=self)


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
    send_test_data = Signal(SendData)

    def __init__(self):
        super().__init__()

        def test_worker_factory():
            worker = TestWorker()
            # worker.pick_hwnd.connect(self.on_pick_hwnd)
            return worker
        self.test_button.attach_worker(test_worker_factory)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_event.emit()
        event.accept()

    @Slot()
    def on_send_data_request(self):
        data = SendData('Test data')
        self.send_message_data.emit(data)


class App(QApplication):
    def __init__(self):
        super().__init__(sys.argv)

        self.ui = MainWindow()
        self.ui.show()

