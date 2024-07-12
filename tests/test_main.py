import gc
import re
import sys
from unittest.mock import patch

import pytest
from PySide6.QtCore import Slot, SignalInstance, QThread, qDebug
from typing_extensions import override

import tests.helpers.os_helpers  # noqa: F401
from main_window import App
from lib.qt.qt_async_button import QAsyncButton
from lib.qt.qt_n_timer import QNTimer, qntimer_timeout_guard
from lib.qt.qt_traced_thread import QWorker, QTracedThread, QSafeThreadedPrint


def gc_after(func, msg):
    # Not required, but may better trigger hidden problems

    def wrapper(*args, **kwargs):
        qDebug('Call with gc: ' + msg)
        func(*args, **kwargs)
        gc.collect()
    return wrapper


def log_signals(func):
    wrapped_signals = {}

    def wrapper(*args, **kwargs):
        signal: SignalInstance = args[0]
        if signal not in wrapped_signals:
            wrapped_signals[signal] = True
            match = re.search(r'SignalInstance (\w+)\(', str(signal))
            signal_name = match.group(1) if match else "Unknown"

            signal.connect(lambda: qDebug("Signal emitted : " + signal_name))
        func(*args, **kwargs)
    return wrapper


# reminder: to see output in IDE during pytests (rather than after debug)
# use -s argument for specific pytest runs
QSafeThreadedPrint.print_qt_in_ouput()


@patch('PySide6.QtCore.SignalInstance.connect', log_signals(SignalInstance.connect))
class TestIntegratedLoad:
    disabled_at_least_once = False
    down_at_least_once = False
    workers_count = 0

    @patch('lib.qt.qt_async_button.QAsyncButton.on_after_thread', gc_after(QAsyncButton.on_after_thread, 'on_after_thread'))
    @patch('lib.qt.qt_async_button.QAsyncButton.stop_thread', gc_after(QAsyncButton.stop_thread, 'stop_thread'))
    def test_traced_thread_random_crash(self):
        """
        Comprehensive load test to try to provoke random overlaps on threads (main vs button).
        Uses all 3: QWorker, QNTimer, QAsyncButton toghether
        QThread.msleep is just an attempt to provoke more overlaps, prefer QTimer in QThreads
        """

        app = App()

        class TestWorker(QWorker):
            def __init__(self):
                super().__init__()
                self.timer = QNTimer(self)
                qDebug('TestWorker.__init__')
                self.timer.timeout_n.connect(self.worker_payload)
                self.timer.finished.connect(self.finished)

            @Slot(int)
            def worker_payload(self, n):
                with qntimer_timeout_guard(self.timer):
                    qDebug('TestWorker.worker_payload')
                    test_sleeps = [0, 150, 1, 99, 9]
                    QThread.msleep(test_sleeps[n])

            @override
            def on_run(self):
                qDebug('TestWorker.on_run')
                self.timer.start(loop_n=5, interval_msec=10)

            @Slot()
            @override
            def on_finished(self):
                qDebug('TestWorker.on_finished')
                TestIntegratedLoad.workers_count += 1
                qDebug('TestWorker finished')

        def test_worker_factory():
            worker = TestWorker()
            qDebug('test_worker_factory')
            return worker

        app.ui.test_button.attach_worker(cb_create_worker=test_worker_factory)
        timer = QNTimer(app.ui)
        qDebug('test_traced_thread_random_crash.body')

        @Slot(int)
        @qntimer_timeout_guard(timer)
        def spam_click(n):
            qDebug(f'spam_click {n}')
            if not app.ui.test_button.isEnabled():
                self.disabled_at_least_once = True
            app.ui.test_button.animateClick()
            if app.ui.test_button.isDown():
                self.down_at_least_once = True
            test_sleeps = [0, 200, 1, 0, 10, 60]
            QThread.msleep(test_sleeps[min(n, 5)])
        timer.timeout_n.connect(spam_click)
        timer.finished.connect(app.ui.close)

        # TODO 1 never finishes
        timer.start(25, 120)
        res = app.exec()
        app.shutdown()

        assert self.disabled_at_least_once
        assert self.down_at_least_once
        assert self.workers_count > 5

        if res != 0:
            sys.exit(res)


def ensure_raises(func, exception_type):
    def wrapper(*args, **kwargs):
        with pytest.raises(exception_type):
            func(*args, **kwargs)
    return wrapper


@patch('PySide6.QtCore.SignalInstance.connect', log_signals(SignalInstance.connect))
class TestWorkerDeadlock:
    terminate_called = False

    def terminate_patch(self: QThread):
        # wraps better, but seems won't work on signature imports
        TestWorkerDeadlock.terminate_called = True
        QThread.terminate(self)

    @patch('lib.qt.qt_traced_thread.QTracedThread.THREAD_QUIT_DEADLINE_MS', 50)
    @patch('lib.qt.qt_traced_thread.QTracedThread.THREAD_TERMINATION_DEADLINE_MS', 100)
    @patch('lib.qt.qt_traced_thread.QTracedThread.quit_or_terminate_qthread', ensure_raises(QTracedThread.quit_or_terminate_qthread, TimeoutError))
    @patch.object(QTracedThread, 'terminate', new=terminate_patch)
    def test_locked_thread(self):
        """ Test for QTracedThread.quit_or_terminate_qthread demanding terminate()  """
        app = App()

        class TestWorker(QWorker):
            @override
            def on_run(self):
                qDebug('TestWorkerDeadlock: worker started')
                QThread.msleep(200)

            @Slot()
            @override
            def on_finished(self):
                qDebug('TestWorkerDeadlock: worker finished externally as expected')

        def worker_factory():
            worker = TestWorker()
            worker.started.connect(app.ui.close)
            return worker
        app.ui.test_button.attach_worker(cb_create_worker=worker_factory)
        QNTimer.singleShot(0, app.ui.test_button.animateClick)

        res = app.exec()
        assert TestWorkerDeadlock.terminate_called

        # CPython AV is expected on termination failure if not to wait here until thread end
        QThread.msleep(300)

        app.shutdown()
        if res != 0:
            sys.exit(res)


@patch('PySide6.QtCore.SignalInstance.connect', log_signals(SignalInstance.connect))
class TestUIQuit:
    def test_ui_quit(self):
        app = App()

        class TestWorker(QWorker):
            @override
            def on_run(self):
                qDebug('run')
                QThread.msleep(50)

            @Slot()
            @override
            def on_finished(self):
                qDebug('finished')

        def worker_factory():
            worker = TestWorker()
            worker.started.connect(app.ui.close)
            return worker
        app.ui.test_button.attach_worker(cb_create_worker=worker_factory)
        QNTimer.singleShot(0, app.ui.test_button.animateClick)

        res = app.exec()
        app.shutdown()
        if res != 0:
            sys.exit(res)
