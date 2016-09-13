# System imports
import simplejson
import os

# Library imports
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

# App imports
from core import PV
from core import VAR
from core import Core

import settings
from settings import KEY

from utils.gui import UiMixin
from utils.gui import dialog_yes_no
from utils.gui import dialog_error
from utils.gui import dialog_info
from utils.gui import decorator_dialog_error
from utils.gui import decorator_busy_cursor

from utils.server import ServMixin

from utils import Constant
from utils import to_rad

from utils.monitor import KEY as MONITOR_KEY

from windows.css import GROUP_BOX_STYLE
from windows.css import GROUP_BOX_STYLE_NO_TITLE
from windows.css import CSS_COLOUR
from windows.css import CSS_LABEL_PV_LOST

from windows.pv_list_window import PvListWindow
from windows.drag_text_mixin import DragTextMixin

from collections import namedtuple

#from scene import MyScene

UNKNOWN_DISPLAY = 'Unknown'

#GRAPHICS_LABEL_KEY_BEAM_HEIGHT = 'label_beam_height'

EDIT_FONT = QtGui.QFont('Courier', 12)
EDIT_ALIGN = Qt.Qt.AlignRight | Qt.Qt.AlignVCenter
EMPTY_STRING = QtCore.QString('')

LABEL_CSS = "background-color: rgba(0,0,0,0%)"

class COLOR(object):
    RED     = QtGui.QColor(255, 0, 0)
    GREEN   = QtGui.QColor(0, 255, 0)
    BLUE    = QtGui.QColor(0, 0, 255)
    YELLOW  = QtGui.QColor(255, 255, 0)

#------------------------------------------------------------------------------

RELEASE_DATE            = 'NOT RELEASED : IN TESTING'

class SETTINGS(Constant):
    KEY = 'main_window_settings'

# class MouseTracker(Qt.QObject):
#
#     SIGNAL_MOVE     = QtCore.pyqtSignal(QtCore.QPoint)
#     SIGNAL_PRESS    = QtCore.pyqtSignal(QtCore.QPoint)
#     SIGNAL_RELEASE  = QtCore.pyqtSignal(QtCore.QPoint)
#
#     def __init__(self, graphics_view):
#
#         self.graphics_view = graphics_view
#         self.parent = self.graphics_view.viewport()
#
#         super(MouseTracker, self).__init__(self.parent)
#
#         self.parent.setMouseTracking(True)
#
#         # Install this object as an eventFilter
#         self.parent.installEventFilter(self)
#
#     def eventFilter(self, _, event):
#
#         # print "mouse event type", repr(event.type())
#
#         if event.type() == Qt.QEvent.MouseButtonPress:
#             self.SIGNAL_PRESS.emit(event.pos())
#
#         elif event.type() == Qt.QEvent.MouseButtonRelease:
#             self.SIGNAL_RELEASE.emit(event.pos())
#
#         elif event.type() == Qt.QEvent.MouseMove:
#             self.SIGNAL_MOVE.emit(event.pos())
#
#         # False indicates event should NOT be eaten
#         return False

class LabelFormatter(object):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        self.label_dict = {}
        self.data_dict = {}

    def format(self, pv_name):

        value = self.monitor.get_value(pv_name)
        labels = self.label_dict.get(pv_name)
        for label in labels:
            data = self.data_dict.get(label)

            fmt = data.get('format')

            display = UNKNOWN_DISPLAY

            if value is None:
                css = data.get('css_lost')
            else:
                css = data.get('css_normal')

                if fmt:
                    display = fmt.format(value)
                else:
                    display = value

            if css:
                label.setStyleSheet(css)

            label.setText(QtCore.QString(display))

    def add(self, pv_name, label, **kwargs):

        labels = self.label_dict.get(pv_name, [])
        labels.append(label)
        self.label_dict[pv_name] = labels

        data = self.data_dict.get(label)
        if data is not None:
            raise ValueError("Already have data for label", repr(label))

        self.data_dict[label] = kwargs


class MainWindow(QtGui.QMainWindow, UiMixin, DragTextMixin,ServMixin):

    SIGNAL_DIALOG_INFO = QtCore.pyqtSignal(unicode)

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        super(MainWindow, self).__init__(*args, **kwargs)

        self.drag_text_mixin_initialize()

        # Load the settings from the user's settings file
        self.load_settings()

        # Set up the user interface from Designer.
        self.load_ui("windows/main_window.ui")
        self.child_windows = []
        self.press_region = None

        self.setWindowTitle(settings.APP_NAME)

        self.SIGNAL_DIALOG_INFO.connect(self.handle_signal_dialog_info)

        self.formatter = LabelFormatter(monitor=self.monitor)
        self.tabWidget.currentChanged.connect(self.handle_tabWidget_changed)

        self.core = Core(monitor=self.monitor)
        self.core.set_status("Running")

        self._item_count = 0

        self.doubleSpinBox_motor_1_moveto.valueChanged.connect(self.handle_SpinBox_motor_1_changed)
        self.doubleSpinBox_motor_2_moveto.valueChanged.connect(self.handle_SpinBox_motor_2_changed)

        # # Track mouse position while in graphics view
        # self.mouse_tracker = MouseTracker(self.graphicsView)
        # self.mouse_tracker.SIGNAL_MOVE.connect(self.handle_mouse_signal_move)
        # self.mouse_tracker.SIGNAL_PRESS.connect(self.handle_mouse_signal_press)
        # self.mouse_tracker.SIGNAL_RELEASE.connect(self.handle_mouse_signal_release)

        self.init_labels()
        self.init_groupBoxes()

        # self.pushButton_1.clicked.connect(self.handle_pushButton_1)
        # self.pushButton_2.clicked.connect(self.handle_pushButton_2)

        self.pushButton_motor_1_movego.clicked.connect(self.handle_pushButton_motor_1_movego)
        self.pushButton_motor_2_movego.clicked.connect(self.handle_pushButton_motor_2_movego)

        self.pushButton_motor_all_checkpos.clicked.connect(self.handle_pushButton_motor_all_checkpos)
        self.pushButton_motor_all_move.clicked.connect(self.handle_pushButton_motor_all_move)
        self.pushButton_motor_all_stop.clicked.connect(self.handle_pushButton_motor_all_stop)

        actions = {
            self.action_about       : self.handle_action_about,
            self.action_pv_list     : self.handle_action_pv_list,
            self.action_var_list    : self.handle_action_var_list,
            self.action_set_server  : self.handle_action_set_server,
        }

        for action, handler in actions.iteritems():
            action.triggered.connect(handler)

        self.set_window_position()
        self.monitor.start()

        self.set_server_address()

        self.core.checkpos_motor_all()


    # @decorator_busy_cursor
    # def handle_pushButton_1(self, dummy):
    #     # print "button 1 clicked"
    #     # self.core.set_status("Button 1 clicked")
    #     # dialog_info(sender=self, msg="Button 1 clicked")
    #
    #     self._item_count += 1
    #     self.core.queue_item(self._item_count)
    #
    # @decorator_busy_cursor
    # def handle_pushButton_2(self, dummy):
    #     # print "button 2 clicked"
    #     # self.core.set_status("Button 2 clicked")
    #     # dialog_info(sender=self, msg="Button 2 clicked")
    #
    #     self.core.queue_clear()


############################################################################################################

    #This is where we input new motors, they pass their motor NAME to the core, which allows us to set it later
    #to add more motors simply add more buttons/numbers
    def handle_SpinBox_motor_1_changed(self):
        self.core.set_motor_moveto(self.doubleSpinBox_motor_1_moveto.value(),1)
    def handle_SpinBox_motor_2_changed(self):
        self.core.set_motor_moveto(self.doubleSpinBox_motor_2_moveto.value(),2)
    def handle_SpinBox_motor_3_changed(self):
        self.core.set_motor_moveto(self.doubleSpinBox_motor_3_moveto.value(),3)
    def handle_SpinBox_motor_4_changed(self):
        self.core.set_motor_moveto(self.doubleSpinBox_motor_4_moveto.value(), 4)
    def handle_SpinBox_motor_5_changed(self):
        self.core.set_motor_moveto(self.doubleSpinBox_motor_5_moveto.value(), 5)
    def handle_SpinBox_motor_6_changed(self):
        self.core.set_motor_moveto(self.doubleSpinBox_motor_6_moveto.value(), 6)

    @decorator_busy_cursor
    def handle_pushButton_motor_1_movego(self,dummy):
        self.core.move_motor(1,self.comboBox_motor_1_movetype.currentText())
        self.core.checkpos_motor_all()
    @decorator_busy_cursor
    def handle_pushButton_motor_2_movego(self,dummy):
        self.core.move_motor(2,self.comboBox_motor_2_movetype.currentText())
        self.core.checkpos_motor_all()
    @decorator_busy_cursor
    def handle_pushButton_motor_3_movego(self,dummy):
        self.core.move_motor(3,self.comboBox_motor_3_movetype.currentText())
        self.core.checkpos_motor_all()
    @decorator_busy_cursor
    def handle_pushButton_motor_4_movego(self,dummy):
        self.core.move_motor(4,self.comboBox_motor_4_movetype.currentText())
        self.core.checkpos_motor_all()
    @decorator_busy_cursor
    def handle_pushButton_motor_5_movego(self,dummy):
        self.core.move_motor(5,self.comboBox_motor_5_movetype.currentText())
        self.core.checkpos_motor_all()
    @decorator_busy_cursor
    def handle_pushButton_motor_6_movego(self,dummy):
        self.core.move_motor(6,self.comboBox_motor_6_movetype.currentText())
        self.core.checkpos_motor_all()

    def handle_pushButton_motor_all_move(self): #this just calls the above moving functions in succesion
        self.handle_pushButton_motor_1_movego('NONE') #if new motors are added, please add other lines
        self.handle_pushButton_motor_2_movego('NONE')
        self.handle_pushButton_motor_3_movego('NONE')
        self.handle_pushButton_motor_4_movego('NONE')
        self.handle_pushButton_motor_5_movego('NONE')
        self.handle_pushButton_motor_6_movego('NONE')

############################################################################################################

    def handle_pushButton_motor_all_checkpos(self):
        allcheck = self.core.checkpos_motor_all()
        if allcheck == True:
            self.core.set_status("All Motor Positions Updated")
        else:
            self.core.set_status("Motor Positions Were NOT Updated")

    def handle_pushButton_motor_all_stop(self):
        pass

    def handle_tabWidget_changed(self, current):
        tabText = self.tabWidget.tabText(current)
        self.core.set_status("Tab Clicked: %s" % QtCore.QString(tabText))

    def init_groupBoxes(self):

        groupBoxes = [
            self.groupBox_example
        ]

        ## Disable MRT Lift group box for now
        #self.groupBox_mrt_lift.setVisible(False)

        for groupBox in groupBoxes:
            groupBox.setStyleSheet(GROUP_BOX_STYLE)

        groupBoxes_no_title = [ self.groupBox_statusBar ]

        for groupBox in groupBoxes_no_title:
            groupBox.setStyleSheet(GROUP_BOX_STYLE_NO_TITLE)

    def init_labels(self):

        css_normal= "QLabel { background-color : %s; color : %s; }" % \
                  (CSS_COLOUR.GROUP_BOX, CSS_COLOUR.BLUE)

        label_map = {
            # VAR.X_PIXEL     : (self.label_pixel_x,      '{:,d}', 12, True),
            # VAR.Y_PIXEL     : (self.label_pixel_y,      '{:,d}', 12, True),
            PV.SYSTEM_TIME     :  (self.label_system_time,          '{:s}',   12, True),
            VAR.STATUS_MSG     :  (self.label_status_msg,           '{:s}',   12, True),
            VAR.SERVER_ADDRESS :  (self.label_server_address,       '{:s}',   12, True),
#            VAR.QUEUE_SIZE    : (self.label_queue_size,   '{:,d}',  12, True),
            VAR.MOTOR_1_POS    :  (self.label_motor_1_pos,        '{:,d}',  12, True),
            VAR.MOTOR_2_POS    :  (self.label_motor_2_pos,        '{:,d}',  12, True), #NOTE THAT THESE ARE {} brakets
            VAR.MOTOR_3_POS    :  (self.label_motor_3_pos,         '{:,d}', 12, True),
            VAR.MOTOR_4_POS    :  (self.label_motor_4_pos,         '{:,d}', 12, True),
            VAR.MOTOR_5_POS    :  (self.label_motor_5_pos,         '{:,d}', 12, True),
            VAR.MOTOR_6_POS    :  (self.label_motor_6_pos,         '{:,d}', 12, True),

        }

        for pv_name, data in label_map.iteritems():
            self.monitor.add(pv_name)

            widget = data[0]
            font = QtGui.QFont('Courier', data[2])
            widget.setFont(font)
            widget.setText(EMPTY_STRING)

            self.set_drag_text(widget, pv_name)

            try:
                if data[3]:
                    font.setWeight(QtGui.QFont.Bold)
            except:
                pass

            self.formatter.add(pv_name, widget, format=data[1],
                css_normal=css_normal,
                css_lost=CSS_LABEL_PV_LOST)

            self.monitor.connect(pv_name, self.handle_label)

    def handle_label(self, pv_name):
        self.formatter.format(pv_name)

    # def handle_mouse_signal_move(self, position):
    #     self.core.set_pixel_x(position.x())
    #     self.core.set_pixel_y(position.y())
    #
    # def handle_mouse_signal_press(self, position):
    #     print "mouse press at X: %d Y: %s" % (position.x(), position.y())

    # @decorator_busy_cursor
    # def handle_mouse_signal_release(self, position):
    #     pixel_x = position.x()
    #     pixel_y = position.y()
    #
    #     msg = "Mouse clicked at X: %d Y: %d" % (pixel_x, pixel_y)
    #     dialog_info(sender=self, msg=msg)

    def handle_signal_dialog_info(self, msg):
        dialog_info(sender=self, title=settings.APP_NAME, msg=msg)

    def handle_action_about(self):

        epics_version = self.monitor.epics_version()

        msg = "Qt Version: %s\n" % Qt.qVersion()
        msg = msg + "PyEpics Version: %s\n" % epics_version[0]
        msg = msg + "Epics DLL: %s\n" % epics_version[1]
        # msg = msg + "MKS Checkpoint: %s\n" % MKS_CHECKPOINT
        msg = msg + "%s" % RELEASE_DATE
        dialog_info(self, msg=msg)

    def handle_action_pv_list(self):

        pv_dict = {}
        d = {'PV' : PV}
        for k, v in d.iteritems():
            for key, value in v.items().iteritems():
                pv_dict['%s.%s' % (k, key)] = value

        window = PvListWindow(
            monitor=self.monitor,
            pv_dict=pv_dict
        )

        window.set_clipboard(self.get_clipboard())
        self.child_windows.append(window)
        window.show()

    def handle_action_var_list(self):

        vars = { 'VAR' : VAR }
        pv_dict = {}

        for k, v in vars.iteritems():
            for key, value in v.items().iteritems():
                pv_dict['%s.%s' % (k, key)] = value

        window = PvListWindow(
            monitor=self.monitor,
            pv_dict=pv_dict
        )

        window.set_clipboard(self.get_clipboard())
        self.child_windows.append(window)
        window.show()

    def handle_action_set_server(self):
        self.core.set_server()

    def callback_window_closed(self, window):
        self.child_windows = [w for w in self.child_windows if w != window]

    def closeEvent(self, event):

        if settings.PROMPT_ON_QUIT:

            msg = "Are you sure you want to quit?"

            if not dialog_yes_no(sender=self, msg=msg):
                event.ignore()
                return

        for window in self.child_windows:
            print "closeEvent: closing child window", id(window)
            window.close()

        print "===================================="

        print self.geometry()
        print "------------------------------------"
        self.save_window_position()

        self.save_server_address()

        self.core.terminate()

        self.monitor.disconnect(self)
        self.monitor.stop()
        self.save_settings()

        # Get a list of all callbacks.... should be empty
        # This is really just a debugging/sanity check
        callback_list = self.monitor.get_callback_list()
        if len(callback_list):
            msg = "Error: there are still registered callbacks: %s" % callback_list
            dialog_error(self, msg=msg)

    def load_settings(self):

        f = None

        try:
            home = os.path.expanduser("~")
            filename = os.path.join(home, settings.SETTINGS_FILE_NAME)
            f = open(filename, 'r')

            print "Loading settings from '%s'" % filename

            self.settings = simplejson.load(f)

            print "These are the settings loaded:"
            print self.settings

        except Exception, e:
            print "Error loading settings file %s: %s" % (filename, str(e))
            self.settings = {}

        finally:
            try:
                if f:
                    f.close()
            except Exception, e:
                print "Error closing settings file %s: %s" % (filename, str(e))

    def save_settings(self):

        f = None

        try:

            home = os.path.expanduser("~")
            filename = os.path.join(home, settings.SETTINGS_FILE_NAME)
            directory = os.path.dirname(os.path.realpath(filename))

            print "saving settings to settings file '%s'" % filename

            if not os.path.exists(directory):
                os.makedirs(directory)

            f = open(filename, 'w+')
            simplejson.dump(self.settings, f, indent=4, sort_keys=True)

        except Exception, e:
            print "Error saving user settings file %s: %s" % (filename, str(e))

        finally:
            if f:
                f.close()
