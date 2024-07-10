# Py Qt Extensions
A few PySide6 extensions or widgets mostly around threading:
- QAsyncButton: QPushButton extension which spawns a new thread with worker and gets disabled while thread is running. Finishes correctly if user closes the QMainWindow.
- QNTimer: signal based replacement of for loop, which fires n times. Handy to remove QThread.sleep commands if no sleep threaded logic is made.
- QTracedThread and QWorker: have pydevd.settrace() at the right places which possibly fully cover breakpoints not hitting problem. For example, QTimer events in sub-classed threads are auto-covered. Also finalisation presets for QTracedThread and QWorker.
- Other trivial extensions, like QComboBoxEx which takes dictionary or QListWidgetItemEx which stores data in the elements.

Some tests included which are handy for fast further extensions.