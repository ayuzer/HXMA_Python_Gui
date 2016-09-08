# System imports
import sys
import os
import inspect

# Library imports
from PyQt4.QtGui import QApplication

# App imports
import settings

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

    print "MASE_PATH", settings.BASE_PATH
    # Add import directories to path
    for dir in settings.IMPORT_DIRS:
        dir_real = os.path.join(settings.BASE_PATH, dir)
        if dir_real not in sys.path:
            sys.path.insert(0, dir_real)

    for item in sys.path:
        print "PATH", item

    # Import main window after path set
    from windows.main_window import MainWindow

    # Create QT app and show MainWindow
    app = QApplication(sys.argv)
    # app.setStyle("plastique")

    # Create and show the main window
    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())
