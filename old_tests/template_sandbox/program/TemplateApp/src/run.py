# System imports
import sys
import os
import inspect

# Library imports
from PyQt4.QtGui import QApplication

# App imports
import settings


# This QT program segfaults on non-2.6 versions of Python
if sys.version_info[0] != 2 or sys.version_info[1] != 7:
    print "This program requires Python 2.7"
    print "This is Python", sys.version
    exit(1)

if __name__ == "__main__":
    """
    Program entry point
    """

    # Determine from which directory app is running
    cur_frame = inspect.currentframe()
    cur_file = inspect.getfile(cur_frame)
    base = os.path.split(cur_file)[0]
    base_abs = os.path.abspath(base)

    # Override settings.BASE_PATH
    settings.BASE_PATH = os.path.realpath(base_abs)

    # Add import directories to path
    for dir in settings.IMPORT_DIRS:
        dir_real = os.path.join(settings.BASE_PATH, dir)
        if dir_real not in sys.path:
            sys.path.insert(0, dir_real)

    for item in sys.path:
        print item

    # Import components after path set
    from windows.main_window import MainWindow
    from monitor import EpicsMonitor

    # Create QT app and show MainWindow
    app = QApplication(sys.argv)
    app.setStyle("plastique")

    # Create epics monitor that emits PyQt signals.
    # Widgets can connect to the signals for real time updates
    monitor = EpicsMonitor()

    # Create and show the main window
    main_window = MainWindow(monitor=monitor)
    main_window.set_clipboard(app.clipboard())
    main_window.show()

    sys.exit(app.exec_())
