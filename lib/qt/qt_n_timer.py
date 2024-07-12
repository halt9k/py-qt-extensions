import functools

from PySide6.QtCore import QTimer, Signal, Slot, qDebug
from typing_extensions import override


class QNTimer(QTimer):
    """
    This ~async QNTimer is intended to reaplce a standard sequential for loop.
    Direct use case is to replace blocking sleeps in threads,
    there may be other use cases, like repeats on failures. Replaces loop:

    # started.emit()
    for n in range (0, repeats)
       timeout_n.emit(self, n)
       # waits for self.continue_loops()
    finished.emit()

    There are multile ways to implement loop timer, QNTimer uses ->:
    ->  1) overriding timeout with new signal timeout_n
        2) replacing signals completely with callbacks since for loop is closely coupled anyway
    And multile ways to have finished() call either:
    ->  1) only if expected amount of loops passed, stopping timer on each loop until started exernally
        2) call loops and finished async no matter what, just when time reached
        3) same async as 2, but possibly stopiing or repeating if previous step fails
    """
    finished = Signal()
    timeout_n = Signal(int)

    def __init__(self, wait_for_continue=True, *args, **kwargs):
        """
        Parameters:
        wait_for_continue:
            - False: QNTimer simply firing all events and than finish no matter what
            - True: QNTimer expects .continue_steps() after each timeout (and finish only if all finished)
        """
        super().__init__(*args, **kwargs)
        self.setSingleShot(wait_for_continue)

        self.n = None
        self.target_n = None

        super().timeout.connect(self.on_timeout)
        # TODO cleanup - not nessesary?
        # if pydevd.settrace in thread leads to AV, that's best 2nd solution
        self.timeout = None

    @Slot()
    def on_timeout(self):
        self.timeout_n.emit(self.n)
        qDebug('QNTimer.on_timeout')

        if not self.isSingleShot():
            # else called externally
            self.continue_loop()

    @override
    def start(self, loop_n, interval_msec):
        if loop_n < 0:
            self.break_loop()
            return

        self.n = 0
        self.target_n = loop_n
        self.setInterval(interval_msec)
        self.on_timeout()

    @Slot()
    def continue_loop(self):
        qDebug('QNTimer.continue_loop')
        self.n += 1

        if self.n == self.target_n:
            self.break_loop()
            return

        assert self.n < self.target_n

        if self.isSingleShot():
            super().start()

    def break_loop(self):
        # not properly tested under async mode yet
        assert self.isSingleShot()

        self.stop()
        self.finished.emit()


def qntimer_timeout_slot(timer_name):
    def decorator(method):
        """
        Wrapper example for simple timeout_n Slots,
        but continue_loop() may be async if a chain of async events is involved
        """

        @functools.wraps(method)
        def wrapper(obj, step_n: int, *args, **kwargs):
            timer: QNTimer = obj.__getattribute__(timer_name)
            assert type(timer) is QNTimer
            try:
                method(obj, step_n, *args,  **kwargs)
            except:
                timer.break_loop()
                raise
            timer.continue_loop()
        return wrapper
    return decorator
