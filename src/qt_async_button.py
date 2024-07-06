from typing import Callable, Optional

from PySide6.QtCore import QThread, Slot, qFatal, qDebug
from PySide6.QtWidgets import QPushButton

from src.qt_traced_thread import QTracedThread, QWorker


class QAsyncButton(QPushButton):
    """
    This was intended as a button which spawns separate thread for experiments.
    Remember not to interact directly with UI in spawned threads.
    Even win32gui.GetWindowText(main_hwnd) can deadlock if called while thread termination is waited.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contexts = []
        self.create_sync_contexts = None
        self.create_worker = None

        self.cb_before_worker = None
        self.cb_after_worker = None

        self.ui_thread = QThread.currentThread()
        self.thread: Optional[QTracedThread] = None
        self.worker: Optional[QWorker] = None

        close_event = self.window().close_event
        if close_event:
            self.window().close_event.connect(self.stop_thread)
        else:
            # TODO was finished emited automatically?
            qFatal("QAsyncButton needs to know when MainWindow is closed to terminate thread if it works.\n"
                   "Propagate a signal from QMainWindow.closeEvent() for this.")

        self.clicked.connect(self.on_start)

    def on_before_thread(self):
        assert self.ui_thread == QThread.currentThread()
        self.setEnabled(False)
        qDebug('self.setEnabled(False)')

        self.enter_contexts()
        if self.cb_before_worker:
            self.cb_before_worker()

    @Slot()
    def on_after_thread(self):
        assert self.ui_thread == QThread.currentThread()

        if self.cb_after_worker:
            self.cb_after_worker()
        self.exit_contexts()
        self.setEnabled(True)
        qDebug('self.setEnabled(True)')

        # reminder in case of persistent worker
        # self.worker.moveToThread(self.ui_thread)
        assert self.worker
        self.worker.deleteLater()
        self.worker = None
        assert self.thread
        self.thread.deleteLater()
        self.thread = None

    @Slot()
    def on_start(self):
        assert self.ui_thread == QThread.currentThread()

        self.on_before_thread()

        assert not self.thread
        self.thread = QTracedThread()

        assert not self.worker
        self.worker: QWorker = self.create_worker()
        self.worker.moveToThread(self.thread)

        # worker quits as expected
        self.worker.finished.connect(self.stop_thread)

        self.thread.finished.connect(self.on_after_thread)
        # thread terminated externally, for example, when main window closed

        self.thread.started.connect(self.worker.run)

        self.thread.start()

    @Slot()
    def stop_thread(self):
        if self.thread:
            QTracedThread.quit_or_terminate_qthread(self.thread)

    def attach_worker(self, cb_create_worker: Callable[[], QWorker], create_sync_contexts=None,
                      cb_before_worker: Callable = None,
                      cb_after_worker: Callable = None):
        """
        create_worker: factory function because on each button press a new worker must be created
        sync_contexts, on_before_worker, on_after_worker: optionals, will wrap worker.run() in UI thread
        """
        self.create_worker = cb_create_worker
        self.create_sync_contexts = create_sync_contexts
        self.cb_before_worker = cb_before_worker
        self.cb_after_worker = cb_after_worker

    def exit_contexts(self):
        for c in reversed(self.contexts):
            # propagate errors?
            c.__exit__(None, None, None)
        self.contexts = []

    def enter_contexts(self):
        self.contexts = self.create_sync_contexts() if self.create_sync_contexts else []
        for c in self.contexts:
            c.__enter__()
