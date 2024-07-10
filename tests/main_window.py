import sys

# Qt intellisense pip install PySide6-stubs
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from lib.qt.qt_async_button import QAsyncButton


class MainWindowFrame(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Test UI")
        if not self.objectName():
            self.setObjectName(u"QMainWindow")
        self.resize(400, 300)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.test_button = QAsyncButton(parent=self.central_widget, text="Test button")


'''
@dataclass(init=True)
class SendData:
    msg: str = ''
'''


class MainWindow(MainWindowFrame):
    close_event = Signal()
    show_event = Signal()
    # send_test_data = Signal(SendData)

    def __init__(self):
        super().__init__()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_event.emit()
        event.accept()

    '''
    @Slot()
    def on_send_data_request(self):
        data = SendData('Test data')
        self.send_test_data.emit(data)
    '''


class App(QApplication):
    def __init__(self):
        super().__init__(sys.argv)

        self.ui = MainWindow()
        self.ui.show()
