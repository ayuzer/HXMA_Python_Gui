# System Imports
from PyQt4 import QtGui
from PyQt4 import QtCore

from utils.gui import UiMixin
from utils.gui import dialog_yes_no

import settings

class Popup(QtGui.QMainWindow, UiMixin):

    def __init__(self, *args, **kwargs):

        print "Popup.__init__() called"

        self.monitor = kwargs['monitor']
        del kwargs['monitor']

        center_point = kwargs['center']
        del kwargs['center']

        super(Popup, self).__init__(*args, **kwargs)

        self.load_ui("windows/popup.ui")

        print "loaded popup UI file"
        self.setWindowTitle(settings.APP_NAME)

        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        self._ok_clicked = False
        self._cancel_clicked = False
        self._close_callback = None

        self.pushButton_ok.clicked.connect(self.handle_pushButton_ok)
        self.pushButton_cancel.clicked.connect(self.handle_pushButton_cancel)

        self.monitor

    def set_close_callback(self, callback):
        self._close_callback = callback

    def closeEvent(self, event):

        print "Popup.closeEvent() called"

        if self._cancel_clicked or self._ok_clicked:
            if not dialog_yes_no(sender=self, msg='Really Close?', title="Setup"):
                event.ignore()
                return

        self.monitor.disconnect(self)
        if self._close_callback:
            self._close_callback(self)

        super(Popup, self).closeEvent(event)

    def handle_pushButton_ok(self):
        self._ok_clicked = True
        self.close()

    def handle_pushButton_cancel(self):
        self._cancel_clicked = True
        self.close()
