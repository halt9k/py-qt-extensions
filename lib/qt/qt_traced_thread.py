import threading
from abc import abstractmethod

import pydevd
from PySide6.QtCore import QThread, QObject, Signal, Slot, QDeadlineTimer, qWarning, QMutex, QMutexLocker, \
    qInstallMessageHandler
from typing_extensions import override


class QTracedThread(QThread):
    THREAD_QUIT_DEADLINE_MS = 500
    THREAD_TERMINATION_DEADLINE_MS = 5000

    @override
    def run(self):
        # without this, breakpoints may not work under IDE
        pydevd.settrace(suspend=False)
        super(QTracedThread, self).run()

    @staticmethod
    def quit_or_terminate_qthread(thread: QThread):
        assert thread != QThread.currentThread()

        if not thread.isRunning():
            return
        thread.quit()

        deadline = QDeadlineTimer(QTracedThread.THREAD_QUIT_DEADLINE_MS)
        quited = thread.wait(deadline)
        if quited:
            return

        qWarning("Warning: thread did not quit fluently, termination attempt scheduled.\n"
                 "This is expected, for example, if: \n"
                 " - sleep is used"
                 " - WinApi calls on QMainWindow may deadlock wait() during closeEvent()\n"
                 "Proper way is QTimer instead of sleep(), but it may overcomlicate some cases.\n"
                 "Another option is to use QApplication.aboutToExit() instead of QMainWindow.closeEvent(),\n"
                 "but closeEvent() better couples lifetime of thread and button.")
        thread.terminate()
        deadline = QDeadlineTimer(QTracedThread.THREAD_TERMINATION_DEADLINE_MS)
        quited = thread.wait(deadline)

        if not quited:
            raise TimeoutError(f"Thread termination in {QTracedThread.THREAD_TERMINATION_DEADLINE_MS}ms failed.")


class QWorker(QObject):
    finished = Signal()
    started = Signal()

    def __init__(self):
        super(QWorker, self).__init__()
        # self.on_finished better before other connections, therefore in __init__, not on_run
        self.finished.connect(self.on_finished)

    @abstractmethod
    def on_run(self):
        raise NotImplementedError

    @Slot()
    def run(self):
        pydevd.settrace(suspend=False)

        try:
            self.started.emit()
            self.on_run()
        except:
            self.finished.emit()
            raise

    @Slot()
    def on_finished(self):
        # @virutalmethod
        pass


'''
class QReusableWorker(QObject):
    """ 
    A draft of reusable which is expected to have same lifetime with button, 
    and moved into new thread before QReusableWorker.run() 
    and back on QReusableWorker.finished().
    No destructions, but extra thread spammed during button lifetime. 
    Unfinished draft. 
    """

    finished = Signal()

    def __init__(self):
        super().__init__()
        self.original_thread = QTracedThread.currentThread()

    @abstractmethod
    def on_run(self):
        raise NotImplementedError

    @Slot()
    def run(self):
        pydevd.settrace(suspend=False)


        # Worker is not expected to branch own thread, but can ensure
        assert self.original_thread != QThread.currentThread()

        try:
            self.on_run()
        except:
            self.finished.emit()

    def on_finished(self):
        self.moveToThread(self.original_thread)
'''


class QSafeThreadedPrint:
    """ Redirects qDebug, qWarning, etc to output """
    mutex = QMutex()

    @staticmethod
    def log_handler(mode, context, msg):
        with QMutexLocker(QSafeThreadedPrint.mutex):
            print(f"{threading.current_thread().name:>10}  {msg}")

    @staticmethod
    def print_qt_in_ouput():
        qInstallMessageHandler(QSafeThreadedPrint.log_handler)