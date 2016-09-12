# System imports
import math
import epics

# Library imports
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

# App imports
import settings
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant
from utils.gui import UiMixin
from utils.gui import dialog_info
from utils.gui import decorator_busy_cursor

from windows.drag_text_mixin import DragTextMixin

from windows.css import CSS_LABEL_BLUE

class PvListWindow(QtGui.QMainWindow, UiMixin, DragTextMixin):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        self.pv_dict = kwargs['pv_dict']
        del kwargs['pv_dict']

        super(PvListWindow, self).__init__(*args, **kwargs)

        # Set up the user interface from Designer.
        self.load_ui("windows/pv_list_window.ui")
        self.setWindowTitle(settings.APP_NAME)

        self.label_map = {}
        self.cainfo_map = {}

        pv_list = []

        self.drag_text_mixin_initialize()

        for k, v in self.pv_dict.iteritems():
            pv_list.append((k, v))

        pv_list.sort(key = lambda item: item[1])

        item_count = len(pv_list)

        grid = self.gridLayout

        cols = 2
        rows = int(math.ceil(float(len(pv_list))/float(cols)))

        font = QtGui.QFont('Courier', 10)
        # font.setWeight(QtGui.QFont.Light)

        index = 0
        for x in xrange(cols):
            for y in xrange(rows):

                if index >= item_count:
                    break

                item = pv_list[index]
                index += 1

                print "Adding PV", item
                label0 = QtGui.QLabel()
                label0.setText(QtCore.QString(item[0]))
                label0.setFont(font)

                label1 = QtGui.QLabel()

                pv_name = item[1]
                # label1.setText(QtCore.QString(item[0]))
                label1.setText(QtCore.QString(pv_name))

                label1.setToolTip(QtCore.QString(pv_name))
                label1.setFont(font)

                self.set_drag_text(label1, pv_name)

                label2 = QtGui.QLabel()
                label2.setText(QtCore.QString(pv_name))
                label2.setToolTip(QtCore.QString(pv_name))
                label2.setFont(font)

                self.set_drag_text(label2, pv_name)

                self.label_map[pv_name] = (label1, label2)

                grid.addWidget(label0, y, x * 4)
                grid.addWidget(label1, y, x * 4 + 1)
                grid.addWidget(label2, y, x * 4 + 2)

                if not self.monitor.is_local(pv_name):
                    pushButton = QtGui.QPushButton('cainfo')
                    pushButton.setMaximumWidth(50)
                    pushButton.setMaximumHeight(20)
                    grid.addWidget(pushButton, y, x * 4 + 3)
                    pushButton.clicked.connect(lambda arg, pv_name=pv_name:
                        self.handle_pushButton(pv_name))

                self.monitor.connect(pv_name, self.handle_pv)
                self.handle_pv(pv_name)

    @decorator_busy_cursor
    def handle_pushButton(self, pv_name):

        info = epics.cainfo(pv_name, print_out=False)
        print info
        if info:
            msg = info
        else:
            msg = "Unable to get cainfo for PV:<br>'%s'" % pv_name
        dialog_info(sender=self, msg=QtCore.QString(msg))

    def handle_pv(self, pv_name):
        value = self.monitor.get_value(pv_name)
        labels = self.label_map.get(pv_name)

        label_title = labels[0]
        label_value = labels[1]

        if value is None:
            value = pv_name
            label_value.setStyleSheet("QLabel { background-color : black; color : white; }")
        else:
            label_value.setStyleSheet(CSS_LABEL_BLUE)

        label_value.setText(QtCore.QString(unicode(value)))
        label_value.setToolTip(QtCore.QString(pv_name))
        label_title.setToolTip(QtCore.QString(pv_name))

        label_value.setText(QtCore.QString(unicode(value)))
        label_value.setToolTip(QtCore.QString(pv_name))
        label_title.setToolTip(QtCore.QString(pv_name))

    def closeEvent(self, event):

        print "pv list window close event"
        self.monitor.disconnect(self)
