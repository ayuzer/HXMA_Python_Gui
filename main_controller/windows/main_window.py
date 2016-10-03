# System imports
import simplejson
import os
from functools import partial
import threading

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

from utils.local_save import ServMixin
from utils.local_save import ScanMixin
from utils.local_save import CentMixin
from utils.local_save import MotMixin

from utils import Constant
from utils import to_rad

from utils.monitor import KEY as MONITOR_KEY

from utils.graph import Plotter

from windows.css import GROUP_BOX_STYLE
from windows.css import GROUP_BOX_STYLE_NO_TITLE
from windows.css import CSS_COLOUR
from windows.css import CSS_LABEL_PV_LOST

from windows.pv_list_window import PvListWindow
from windows.drag_text_mixin import DragTextMixin

from windows.minor_windows import LoadPositions as LoadPositionsWindow
from windows.minor_windows import SetMotorSlot as SetMotorSlotWindow

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

RELEASE_DATE            = 'NOT Released : IN TESTING'

PLOT_TITLE = "SCAN POSITION vs INTENSITY"
PLOT_LABEL_X = "POSITION"
PLOT_LABEL_Y = "COUNTS"

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


class MainWindow(QtGui.QMainWindow, UiMixin, DragTextMixin, ServMixin, ScanMixin, CentMixin, MotMixin):

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

        # Track mouse position while in graphics view
        # self.mouse_tracker = MouseTracker(self.graphicsView)
        # self.mouse_tracker.SIGNAL_MOVE.connect(self.handle_mouse_signal_move)
        # self.mouse_tracker.SIGNAL_PRESS.connect(self.handle_mouse_signal_press)
        # self.mouse_tracker.SIGNAL_RELEASE.connect(self.handle_mouse_signal_release)

        self.init_labels()

        actions = {
            self.action_about: self.handle_action_about,
            self.action_pv_list: self.handle_action_pv_list,
            self.action_var_list: self.handle_action_var_list,
            self.action_set_server: self.handle_action_set_server,
            self.action_motor_slots: self.handle_action_motor_slots,
        }

        for action, handler in actions.iteritems():
            action.triggered.connect(handler)

        self.set_window_position()
        self.monitor.start()

        """INIT SPEC"""
        if self.set_server_address():
            self.core.init_Spec()
        else:
            print "SERVER ADDRESS NOT IN JSON, REVERTING TO DEFAULT"
            self.handle_action_set_server()
            self.core.init_Spec()

        """MOTOR INIT"""
        # INIT RUN ----Has to be first to init Motors for connecting buttons
        self.init_motor_slots()
        motor_props=self.set_motors()
        self.motor_names = [
            self.label_motor_1_name,
            self.label_motor_2_name,
            self.label_motor_3_name,
            self.label_motor_4_name,
            self.label_motor_5_name,
            self.label_motor_6_name,
        ]
        self.Motors = [self.Motor_1, self.Motor_2, self.Motor_3, self.Motor_4, self.Motor_5, self.Motor_6]
        if not motor_props==False:
            for i in range(len(self.Motors)):
                self.Motors[i] = self.Motors[i]._replace(Name=motor_props[0][i], Mne=motor_props[1][i], Enabled=motor_props[2][i])
        self.update_motors(self.Motors)
        self.handle_pushButton_motor_all_checkpos(False)  # just checking position, False is a dummy var
        # Connect Buttons
        self.pushButton_motor_1_movego.clicked.connect(partial(self.handle_pushButton_motor_movego, self.Motor_1))
        self.pushButton_motor_2_movego.clicked.connect(partial(self.handle_pushButton_motor_movego, self.Motor_2))
        self.pushButton_motor_3_movego.clicked.connect(partial(self.handle_pushButton_motor_movego, self.Motor_3))
        self.pushButton_motor_4_movego.clicked.connect(partial(self.handle_pushButton_motor_movego, self.Motor_4))
        self.pushButton_motor_5_movego.clicked.connect(partial(self.handle_pushButton_motor_movego, self.Motor_5))
        self.pushButton_motor_6_movego.clicked.connect(partial(self.handle_pushButton_motor_movego, self.Motor_6))

        self.pushButton_motor_all_checkpos.clicked.connect(self.handle_pushButton_motor_all_checkpos)
        self.pushButton_motor_all_move.clicked.connect(self.handle_pushButton_motor_all_move)
        self.pushButton_motor_all_stop.clicked.connect(self.handle_pushButton_motor_all_stop)

        self.checkBox_motor_all_checkpos.stateChanged.connect(self.handle_checkBox_motor_all_checkpos)
        """COUNTER INIT"""
        # Connect Buttons
        self.checkBox_count.stateChanged.connect(self.handle_checkBox_count)
        # INIT RUN
        self.handle_checkBox_count()  # handing down the count variables to core with this

        """SCAN INIT"""
        # Connect Buttons
        self.pushButton_scan_start_stop.clicked.connect(self.handle_pushButton_scan_start_stop)
        self.pushButton_scan_save.clicked.connect(self.handle_save_scan)
        self.pushButton_scan_select_file.clicked.connect(partial(self.select_file, self.lineEdit_scan_select_file))

        self.lineEdit_scan_select_file.textChanged.connect(
            partial(self.core.update_filepath, str(self.lineEdit_scan_select_file.text()), 'scan'))

        self.comboBox_scan_motor.currentIndexChanged.connect(self.handle_comboBox_scan_motor)
        self.comboBox_scan_data_x.activated.connect(self.handle_comboBox_scan_data)
        self.comboBox_scan_data_y.activated.connect(self.handle_comboBox_scan_data)

        self.pushButton_scan_start_stop.setText(self.scan_button_text()) # This means the button says Start instead of START/STOP
        # INIT RUN
        self.handle_comboBox_scan_motor()
        self.update_scan_cols()
        self.set_scan_props() # updating variables from the saved file (last session)
        self.core.update_filepath(str(self.lineEdit_scan_select_file.text()), 'scan')
        # Plot
        self.scan_plot_id = Plotter(monitor=self.monitor, VAR=VAR, id='scan')
        self.verticalLayout_scan_graph.addWidget(self.scan_plot_id)
        self.scan_plot_id.set_title(PLOT_TITLE)
        self.scan_plot_id.set_axis_label_x(PLOT_LABEL_X)
        self.scan_plot_id.set_axis_label_y(PLOT_LABEL_Y)
        # self.scan_plot_id.set_mouse_position_callback(self.callback_mouse_pos_id)
        self.scan_plot_id.set_legend()
        self.scan_plot_id.timer = QtCore.QTimer()

        """CENTER INIT"""
        # Connect Buttons
        self.pushButton_cent_start_stop.clicked.connect(self.handle_pushButton_cent_start_stop)
        self.pushButton_cent_save.clicked.connect(self.handle_save_cent)
        self.pushButton_cent_select_file.clicked.connect(partial(self.select_file, self.lineEdit_cent_select_file))

        self.lineEdit_scan_select_file.textChanged.connect(
            partial(self.core.update_filepath, str(self.lineEdit_scan_select_file.text()), 'cent'))

        self.comboBox_cent_motor_scan.currentIndexChanged.connect(self.handle_comboBox_cent_motor)
        self.comboBox_cent_motor_angle.currentIndexChanged.connect(self.handle_comboBox_cent_motor)
        self.comboBox_cent_data_x.activated.connect(self.handle_comboBox_cent_data)
        self.comboBox_cent_data_y.activated.connect(self.handle_comboBox_cent_data)

        self.checkBox_cent_single.stateChanged.connect(partial(self.cent_graph, self.checkBox_cent_single))
        #Variables
        (self.cent_plot_id_1, self.cent_plot_id_2, self.cent_plot_id_3) = Plotter(monitor=self.monitor, VAR=VAR, id='neg'), \
                                                                          Plotter(monitor=self.monitor, VAR=VAR, id='nau'), \
                                                                          Plotter(monitor=self.monitor, VAR=VAR, id='pos')
        self.plots = [self.cent_plot_id_1, self.cent_plot_id_2, self.cent_plot_id_3]
        self.cent_plot_id = Plotter(monitor=self.monitor, VAR=VAR, id='multi')
        self.cent_timer = QtCore.QTimer()
        # INIT RUN
        self.init_cent_graph(self.checkBox_cent_single.isChecked())
        self.handle_comboBox_cent_motor()
        self.update_cent_cols()
        self.set_cent_props()  # updating variables from the saved file (last session)
        self.core.update_filepath(str(self.lineEdit_cent_select_file.text()), 'cent')
        self.core.is_centering(self.pushButton_cent_start_stop)

        """CONDITIONING"""
        self.pushButton_cond_pb_aper_hor_movego.clicked.connect(partial(self.handle_cond_move, PV.COND_PB_APER_HOR_POS, self.doubleSpinBox_cond_pb_aper_hor_moveto, self.comboBox_cond_pb_aper_hor_movetype))

        self.init_beam_cond()


        """PICTURE"""
        pic = QtGui.QLabel(self.label_motor_picture)
        pixmap = QtGui.QPixmap('/staff/hamelm/Documents/stage_background.png')
        pic.setPixmap(pixmap.scaled(500, 500, QtCore.Qt.KeepAspectRatio))
        pic.show()
        self.old_scan_x, self.old_scan_y = ([] for i in range(2))

        """POPOUTS"""
        self.pushButton_open_pos_load.clicked.connect(self.handle_action_save_load)

    """POPUPS"""
    def handle_action_save_load(self):
        center_point = self.geometry().center()
        self.handle_action_popup(LoadPositionsWindow(monitor=self.monitor,
                                                     center=center_point,
                                                     motors=self.Motors,
                                                     ))

    def handle_action_motor_slots(self):
        center_point = self.geometry().center()
        window = SetMotorSlotWindow(monitor=self.monitor, center=center_point, motors=self.Motors)
        window.apply_callback(self.update_motors)
        self.handle_action_popup(window)

    def handle_action_popup(self, window):
        self.child_windows.append(window)
        window.set_close_callback(self.callback_window_closed)
        window.show()

    """MOTOR"""
    @decorator_busy_cursor
    def handle_pushButton_motor_movego(self, motor, dummy):  # Will pass the ref to relevant motor
        if self.core.is_moving(motor.Name):
            self.core.set_status(motor.Name + " is already moving")
        else:
            self.core.move_motor(motor)
        self.handle_pushButton_motor_all_checkpos(self.Motors)

    def handle_pushButton_motor_all_move(self, dummy): # this just calls the moving function if enabled for each
        for i in range(len(self.Motors)):
            Motor_inst = self.Motors[i]
            if Motor_inst.Enabled:
                self.core.move_motor(Motor_inst)

    def handle_pushButton_motor_all_checkpos(self,dummy):  # calls a check_pos for each motor if enabled
        for i in range(len(self.Motors)):
            Motor_inst = self.Motors[i]
            if Motor_inst.Enabled:
                self.core.checkpos_motor(Motor_inst)

    def handle_checkBox_motor_all_checkpos(self):  # Enables/disables constant position tracking
        self.core.motor_track_state(self.checkBox_motor_all_checkpos.isChecked())

    def handle_pushButton_motor_all_stop(self):
        for i in range(len(self.Motors)):
            Motor_inst = self.Motors[i]
            if Motor_inst.Enabled:
                self.core.motor_stop(Motor_inst)

    def init_motor_slots(self):
        Motor_Slot = namedtuple('Motor_Slot',
                                ['Name', 'Mne', 'Enabled', 'Pos_VAR', 'Moveto_SB', 'Move_PB', 'MoveType_CB'])
        self.Motor_1 = Motor_Slot(Pos_VAR=VAR.MOTOR_1_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_1_moveto,
                                  Move_PB=self.pushButton_motor_1_movego,
                                  MoveType_CB=self.comboBox_motor_1_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  )
        self.Motor_2 = Motor_Slot(Pos_VAR=VAR.MOTOR_2_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_2_moveto,
                                  Move_PB=self.pushButton_motor_2_movego,
                                  MoveType_CB=self.comboBox_motor_2_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  )
        self.Motor_3 = Motor_Slot(Pos_VAR=VAR.MOTOR_3_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_3_moveto,
                                  Move_PB=self.pushButton_motor_3_movego,
                                  MoveType_CB=self.comboBox_motor_3_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  )
        self.Motor_4 = Motor_Slot(Pos_VAR=VAR.MOTOR_4_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_4_moveto,
                                  Move_PB=self.pushButton_motor_4_movego,
                                  MoveType_CB=self.comboBox_motor_4_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  )
        self.Motor_5 = Motor_Slot(Pos_VAR=VAR.MOTOR_5_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_5_moveto,
                                  Move_PB=self.pushButton_motor_5_movego,
                                  MoveType_CB=self.comboBox_motor_5_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  )
        self.Motor_6 = Motor_Slot(Pos_VAR=VAR.MOTOR_6_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_6_moveto,
                                  Move_PB=self.pushButton_motor_6_movego,
                                  MoveType_CB=self.comboBox_motor_6_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  )

    def update_motors(self, Motors):
        self._move_terminate_flag = True
        t = threading.Timer(3.0,  self.core.update_motors(self.motor_names, Motors, (self.comboBox_scan_motor, self.comboBox_cent_motor_scan, self.comboBox_cent_motor_angle)))
        # t.start()
        self.Motors = Motors

    """COUNT"""
    def handle_checkBox_count(self):  #Also passes the reference to the count-time down
        self.core.counting_state(self.checkBox_count.isChecked(), self.doubleSpinBox_count_time_set)
        self.doubleSpinBox_count_time_set.setRange(0.01, 259200)  # 0.1 sec to 3 days

    """SCAN"""
    def scan_button_text(self):
        if self.core.is_scanning(self.pushButton_scan_start_stop):
            return 'Stop'
        else:
            return 'Start'

    def handle_pushButton_scan_start_stop(self):
        if self.core.is_scanning(self.pushButton_scan_start_stop):
            self.core.scan_stop()
        else:
            self.core.scan_start(self.checkBox_scan_return_home.checkState(),  # What Mode True = dscan False = ascan
                                 self.comboBox_scan_motor.currentText(),  # Which Motor are we using? Passes NAME back
                                 self.doubleSpinBox_scan_startpos.value(),  # the rest are just values
                                 self.doubleSpinBox_scan_stoppos.value(),
                                 self.doubleSpinBox_scan_steps.value(),
                                 self.doubleSpinBox_scan_waittime.value(),
                                 self.Motors  # We need to pass this so we can see which motor we are scanning with
                                 )
            self.scan_plot_id.timer.start(250.0)
            self.connect(self.scan_plot_id.timer, QtCore.SIGNAL('timeout()'), self.scan_plot)

    def scan_plot(self):
        go, x, y = self.core.get_data(self.comboBox_scan_data_x.currentIndex(),
                                      self.comboBox_scan_data_y.currentIndex())
        self.core.update_bar_pos(VAR.VERT_BAR_SCAN_POS, x, y)

        if not self.old_scan_x == x or not self.old_scan_y == y and go:
            self.scan_plot_id.new_plot(x, y)
            self.core.scan_calculations(x, y)
            self.tableWidget_scan_data.setHorizontalHeaderLabels([self.comboBox_scan_data_x.currentText(),
                                                                  self.comboBox_scan_data_y.currentText(),
                                                                  ])
            self.tableWidget_scan_data.setColumnCount(2)
            self.tableWidget_scan_data.setRowCount(len(x))
            for row in range(len(x)):
                self.tableWidget_scan_data.setItem(row, 0, QtGui.QTableWidgetItem(QtCore.QString("%1").arg(x[row])))
                self.tableWidget_scan_data.setItem(row, 1, QtGui.QTableWidgetItem(QtCore.QString("%1").arg(y[row])))
        (self.old_scan_x, self.old_scan_y) = x, y

    def handle_comboBox_scan_motor(self):
        self.core.scan_settings(self.comboBox_scan_motor.currentText(),
                                self.doubleSpinBox_scan_startpos,
                                self.doubleSpinBox_scan_stoppos,
                                self.Motors,
                                self.doubleSpinBox_scan_waittime
                                )

    def update_scan_cols(self):
        self.core.update_CB(self.comboBox_scan_data_x, self.comboBox_scan_data_y, 'scan')

    def handle_comboBox_scan_data(self):
        pass

    def handle_save_scan(self):
        self.core.save_scan_curr(str(self.lineEdit_scan_filename.text()),
                                 self.comboBox_scan_data_x,
                                 self.comboBox_scan_data_y,
                                 )

    """CENTER"""
    def handle_comboBox_cent_motor(self):
        self.core.cent_settings(self.comboBox_cent_motor_scan.currentText(),
                                self.comboBox_cent_motor_angle.currentText(),
                                self.doubleSpinBox_cent_relmax,
                                self.doubleSpinBox_cent_relmin,
                                self.doubleSpinBox_cent_center,
                                self.doubleSpinBox_cent_angle_pm,
                                self.doubleSpinBox_cent_angle_o,
                                self.Motors,
                                self.doubleSpinBox_cent_waittime,
                                self.comboBox_cent_calc_choose,
                                )

    def handle_pushButton_cent_start_stop(self):
        if self.core.is_centering(self.pushButton_cent_start_stop):
            self.core.cent_stop()
        else:
            self.core.cent_start(self.comboBox_cent_motor_scan.currentText(),
                                 self.comboBox_cent_motor_angle.currentText(),
                                 self.doubleSpinBox_cent_relmax.value(),
                                 self.doubleSpinBox_cent_relmin.value(),
                                 self.doubleSpinBox_cent_center.value(),
                                 self.doubleSpinBox_cent_angle_pm.value(),
                                 self.doubleSpinBox_cent_angle_o.value(),
                                 self.doubleSpinBox_cent_steps.value(),
                                 self.doubleSpinBox_cent_waittime.value(),
                                 self.Motors,
                                 )
            self.cent_timer.start(250.0)
            self.connect(self.cent_timer,  QtCore.SIGNAL('timeout()'), self.cent_plot)

    def cent_plot(self):
        self.scan_plot()  # makes it so that the plot also displays on the scan tab
        if self.checkBox_cent_single.isChecked():
            plot = self.cent_plot_id
        else:
            plot = self.plots
        self.core.cent_plotting(plot, self.tableWidget_cent_data,
                                self.comboBox_cent_data_x, self.comboBox_cent_data_y,
                                self.comboBox_cent_calc_choose, self.checkBox_cent_single.isChecked())

    def handle_save_cent(self):
        self.core.save_cent_curr(str(self.lineEdit_cent_filename.text()),
                                 self.comboBox_cent_data_x,
                                 self.comboBox_cent_data_y,
                                 )

    def handle_comboBox_cent_data(self):
        pass

    def update_cent_cols(self):
        self.core.update_CB(self.comboBox_cent_data_x, self.comboBox_cent_data_y, 'cent')

    def init_cent_graph(self, single):
        self.verticalLayout_cent_graph.addWidget(self.cent_plot_id)
        self.cent_plot_id.set_title(PLOT_TITLE)
        self.cent_plot_id.set_axis_label_x(PLOT_LABEL_X)
        self.cent_plot_id.set_axis_label_y(PLOT_LABEL_Y)
        self.cent_plot_id.set_legend()
        self.cent_plot_id.setSizePolicy(Qt.QSizePolicy.Ignored, Qt.QSizePolicy.Ignored)
        i = 0
        name = ['', 'w-', 'wo', 'w+']
        for plot in self.plots:
            self.verticalLayout_cent_graph.addWidget(plot)
            plot.setSizePolicy(Qt.QSizePolicy.Ignored, Qt.QSizePolicy.Ignored)
            if i == 0:
                i = 1
                plot.set_title(PLOT_TITLE)
            elif i == 1:
                i = 2
            elif i == 2:
                plot.set_axis_label_x(PLOT_LABEL_X)
            plot.set_axis_label_y(PLOT_LABEL_Y + ' ' + name[i])
        if single:
            for plots in self.plots:
                plots.hide()
            self.cent_plot_id.show()
        else:
            for plot in self.plots:
                plot.show()
            self.cent_plot_id.hide()

    def cent_graph(self, Check):
        single = Check.isChecked()
        if single:
            for plot in self.plots:
                plot.hide()
            self.cent_plot_id.show()
        else:
            for plot in self.plots:
                plot.show()
            self.cent_plot_id.hide()

    """CONDITIONING"""
    def init_beam_cond(self):
        Beam_Cond = namedtuple('Beam_Cond',
                                ['PV', 'Moveto_SB', 'Move_PB', 'MoveType_CB'])
        self.table_hor_gap = Beam_Cond(PV=PV.COND_TABLE_HOR_GAP_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_hor_gap,
                                       MoveType_CB=self.comboBox_cond_table_hor_gap_movetype,
                                       Move_PB=self.pushButton_cond_table_hor_gap_movego,
                                       )
        self.table_hor_cent = Beam_Cond(PV=PV.COND_TABLE_HOR_CENT_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_hor_cent,
                                       MoveType_CB=self.comboBox_cond_table_hor_cent_movetype,
                                       Move_PB=self.pushButton_cond_table_hor_cent_movego,
                                       )
        self.table_hor_mot1 = Beam_Cond(PV=PV.COND_TABLE_HOR_MOT1_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_hor_mot1,
                                       MoveType_CB=self.comboBox_cond_table_hor_mot1_movetype,
                                       Move_PB=self.pushButton_cond_table_hor_mot1_movego,
                                       )
        self.table_hor_mot2 = Beam_Cond(PV=PV.COND_TABLE_HOR_MOT2_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_hor_mot2,
                                       MoveType_CB=self.comboBox_cond_table_hor_mot2_movetype,
                                       Move_PB=self.pushButton_cond_table_hor_mot2_movego,
                                       )
        self.table_vert_gap = Beam_Cond(PV=PV.COND_TABLE_VERT_GAP_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_vert_gap,
                                       MoveType_CB=self.comboBox_cond_table_vert_gap_movetype,
                                       Move_PB=self.pushButton_cond_table_vert_gap_movego,
                                       )
        self.table_vert_cent = Beam_Cond(PV=PV.COND_TABLE_VERT_CENT_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_vert_cent,
                                       MoveType_CB=self.comboBox_cond_table_vert_cent_movetype,
                                       Move_PB=self.pushButton_cond_table_vert_cent_movego,
                                       )
        self.table_vert_mot1 = Beam_Cond(PV=PV.COND_TABLE_VERT_MOT1_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_vert_mot1,
                                       MoveType_CB=self.comboBox_cond_table_vert_mot1_movetype,
                                       Move_PB=self.pushButton_cond_table_vert_mot1_movego,
                                       )
        self.table_vert_mot2 = Beam_Cond(PV=PV.COND_TABLE_VERT_MOT2_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_table_vert_mot2,
                                       MoveType_CB=self.comboBox_cond_table_vert_mot2_movetype,
                                       Move_PB=self.pushButton_cond_table_vert_mot2_movego,
                                       )
        
        
        self.diff_hor_gap = Beam_Cond(PV=PV.COND_DIFF_HOR_GAP_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_hor_gap,
                                       MoveType_CB=self.comboBox_cond_diff_hor_gap_movetype,
                                       Move_PB=self.pushButton_cond_diff_hor_gap_movego,
                                       )
        self.diff_hor_cent = Beam_Cond(PV=PV.COND_DIFF_HOR_CENT_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_hor_cent,
                                       MoveType_CB=self.comboBox_cond_diff_hor_cent_movetype,
                                       Move_PB=self.pushButton_cond_diff_hor_cent_movego,
                                       )
        self.diff_hor_mot1 = Beam_Cond(PV=PV.COND_DIFF_HOR_MOT1_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_hor_mot1,
                                       MoveType_CB=self.comboBox_cond_diff_hor_mot1_movetype,
                                       Move_PB=self.pushButton_cond_diff_hor_mot1_movego,
                                       )
        self.diff_hor_mot2 = Beam_Cond(PV=PV.COND_DIFF_HOR_MOT2_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_hor_mot2,
                                       MoveType_CB=self.comboBox_cond_diff_hor_mot2_movetype,
                                       Move_PB=self.pushButton_cond_diff_hor_mot2_movego,
                                       )
        self.diff_vert_gap = Beam_Cond(PV=PV.COND_DIFF_VERT_GAP_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_vert_gap,
                                       MoveType_CB=self.comboBox_cond_diff_vert_gap_movetype,
                                       Move_PB=self.pushButton_cond_diff_vert_gap_movego,
                                       )
        self.diff_vert_cent = Beam_Cond(PV=PV.COND_DIFF_VERT_CENT_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_vert_cent,
                                       MoveType_CB=self.comboBox_cond_diff_vert_cent_movetype,
                                       Move_PB=self.pushButton_cond_diff_vert_cent_movego,
                                       )
        self.diff_vert_mot1 = Beam_Cond(PV=PV.COND_DIFF_VERT_MOT1_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_vert_mot1,
                                       MoveType_CB=self.comboBox_cond_diff_vert_mot1_movetype,
                                       Move_PB=self.pushButton_cond_diff_vert_mot1_movego,
                                       )
        self.diff_vert_mot2 = Beam_Cond(PV=PV.COND_DIFF_VERT_MOT2_POS,
                                       Moveto_SB=self.doubleSpinBox_cond_diff_vert_mot2,
                                       MoveType_CB=self.comboBox_cond_diff_vert_mot2_movetype,
                                       Move_PB=self.pushButton_cond_table_vert_mot2_movego,
                                       )
        

        self.pb_aper_hor = Beam_Cond(PV=PV.COND_PB_APER_HOR_POS_PUSH,
                                         Moveto_SB=self.doubleSpinBox_cond_pb_aper_hor_moveto,
                                         MoveType_CB=self.comboBox_cond_pb_aper_hor_movetype,
                                         Move_PB=self.pushButton_cond_pb_aper_hor_movego,
                                         )

        self.pb_aper_vert = Beam_Cond(PV=PV.COND_PB_APER_VERT_POS_PUSH,
                                     Moveto_SB=self.doubleSpinBox_cond_pb_aper_vert_moveto,
                                     MoveType_CB=self.comboBox_cond_pb_aper_vert_movetype,
                                     Move_PB=self.pushButton_cond_pb_aper_vert_movego,
                                     )
        self.dac_pin_hor = Beam_Cond(PV=PV.COND_DAC_PIN_HOR_POS_PUSH,
                                     Moveto_SB=self.doubleSpinBox_cond_dac_pin_hor_moveto,
                                     MoveType_CB=self.comboBox_cond_dac_pin_hor_movetype,
                                     Move_PB=self.pushButton_cond_dac_pin_hor_movego,
                                     )

        self.dac_pin_vert = Beam_Cond(PV=PV.COND_DAC_PIN_VERT_POS_PUSH,
                                      Moveto_SB=self.doubleSpinBox_cond_dac_pin_vert_moveto,
                                      MoveType_CB=self.comboBox_cond_dac_pin_vert_movetype,
                                      Move_PB=self.pushButton_cond_dac_pin_vert_movego,
                                      )

        self.beam_stop_hor = Beam_Cond(PV=PV.COND_BEAM_STOP_HOR_POS_PUSH,
                                     Moveto_SB=self.doubleSpinBox_cond_beam_stop_hor_moveto,
                                     MoveType_CB=self.comboBox_cond_beam_stop_hor_movetype,
                                     Move_PB=self.pushButton_cond_beam_stop_hor_movego,
                                     )

        self.beam_stop_vert = Beam_Cond(PV=PV.COND_BEAM_STOP_VERT_POS_PUSH,
                                      Moveto_SB=self.doubleSpinBox_cond_beam_stop_vert_moveto,
                                      MoveType_CB=self.comboBox_cond_beam_stop_vert_movetype,
                                      Move_PB=self.pushButton_cond_beam_stop_vert_movego,
                                      )

        self.beam_cond =[
            self.table_hor_gap, self.table_hor_cent, self.table_hor_mot1, self.table_hor_mot2,
            self.table_vert_gap, self.table_vert_cent, self.table_vert_mot1, self.table_vert_mot2,
            self.diff_hor_gap, self.diff_hor_cent, self.diff_hor_mot1, self.diff_hor_mot2,
            self.diff_vert_gap, self.diff_vert_cent, self.diff_vert_mot1, self.diff_vert_mot2,
            self.pb_aper_hor, self.pb_aper_vert, self.beam_stop_hor, self.beam_stop_vert,
            self.dac_pin_hor, self.dac_pin_vert,
        ]

        for move in self.beam_cond:
            move.MoveType_CB.addItems(['Relative', 'Absolute'])
            if move.Move_PB == None:  # No pushbutton therefore commands go off of enter in box
                # move.MoveType_CB.lineEdit().returnPressed.connect(partial(self.handle_cond_move, move.PV, move.Moveto_SB.value(), move.MoveType_CB.currentText()))
                pass
            else:
                move.Move_PB.clicked.connect(partial(self.handle_cond_move, move.PV, move.Moveto_SB, move.MoveType_CB))

    def handle_cond_move(self, PV, SB, CB):
        self.core.cond_move(PV, SB.value(), CB.currentText())

    """RANDOM"""
    def select_file(self, line_edit):
        line_edit.setText(QtGui.QFileDialog.getExistingDirectory(None, 'Select a folder to save data :', os.getcwd(), QtGui.QFileDialog.ShowDirsOnly))

    def handle_tabWidget_changed(self, current):
        tabText = self.tabWidget.tabText(current)
        self.core.set_status("Tab Clicked: %s" % QtCore.QString(tabText))

    def init_labels(self):

        css_normal= "QLabel { background-color : %s; color : %s; }" % \
                  (CSS_COLOUR.GROUP_BOX, CSS_COLOUR.BLUE)

        label_map = {
            PV.SYSTEM_TIME:         (self.label_system_time,        '{:s}',     12, True),
            PV.BEAM_STOP:           (self.label_beam_stop,          '{:g}',    12, True),
            PV.PRE_OPTICS:          (self.label_pre_optics,         '{:g}',    12, True),
            VAR.STATUS_MSG:         (self.label_status_msg,         '{:s}',     12, True),
            VAR.MOTOR_1_POS:        (self.label_motor_1_pos,        '{:,.3f}',  12, True),
            VAR.MOTOR_2_POS:        (self.label_motor_2_pos,        '{:,.3f}',  12, True),
            VAR.MOTOR_3_POS:        (self.label_motor_3_pos,        '{:,.3f}',  12, True),
            VAR.MOTOR_4_POS:        (self.label_motor_4_pos,        '{:,.3f}',  12, True),
            VAR.MOTOR_5_POS:        (self.label_motor_5_pos,        '{:,.3f}',  12, True),
            VAR.MOTOR_6_POS:        (self.label_motor_6_pos,        '{:,.3f}',  12, True),
            VAR.COUNTER_1_COUNT:    (self.label_counter_1_count,    '{:,d}',    12, True),
            VAR.COUNTER_2_COUNT:    (self.label_counter_2_count,    '{:,d}',    12, True),
            VAR.COUNT_TIME:         (self.label_count_time,         '{:.3f}',   12, True),
            VAR.SCAN_MAX_Y:         (self.label_scan_max_y,         '{:s}',     12, True),
            VAR.SCAN_FWHM:          (self.label_scan_FWHM,          '{:.2f}',   12, True),
            VAR.SCAN_COM:           (self.label_scan_COM,           '{:.2f}',   12, True),
            VAR.SCAN_CWHM:          (self.label_scan_CWHM,          '{:.2f}',   12, True),
            VAR.CENT_NEG_MAXY:      (self.label_cent_maxint_m,      '{:.3f}',   12, True),
            VAR.CENT_NAU_MAXY:      (self.label_cent_maxint_o,      '{:.3f}',   12, True),
            VAR.CENT_POS_MAXY:      (self.label_cent_maxint_p,      '{:.3f}',   12, True),
            VAR.CENT_NEG_COM:       (self.label_cent_com_m,         '{:.3f}',   12, True),
            VAR.CENT_NAU_COM:       (self.label_cent_com_o,         '{:.3f}',   12, True),
            VAR.CENT_POS_COM:       (self.label_cent_com_p,         '{:.3f}',   12, True),
            VAR.VERT_BAR_NEG_X:   (self.label_cent_curs_m,        '{:.3f}',   12, True),
            VAR.VERT_BAR_NAU_X:   (self.label_cent_curs_o,        '{:.3f}',   12, True),
            VAR.VERT_BAR_POS_X:   (self.label_cent_curs_p,        '{:.3f}',   12, True),
            VAR.VERT_BAR_SCAN_X:   (self.label_scan_curser,        '{:.3f}',   12, True),
            VAR.CENT_CENTERED_X:    (self.label_cent_calc_cent_x,   '{:.3f}',   12, True),
            VAR.CENT_CENTERED_Y:    (self.label_cent_calc_cent_y,   '{:.3f}',   12, True),


            PV.COND_TABLE_HOR_STATUS: (self.label_cond_table_hor_status, '{:g}',     12, True),
            PV.COND_TABLE_HOR_GAP_POS: (self.label_cond_table_hor_gap_currpos, '{:,.2f}',     12, True),
            PV.COND_TABLE_HOR_CENT_POS: (self.label_cond_table_hor_cent_currpos, '{:,.2f}', 12, True),
            PV.COND_TABLE_HOR_MOT1_POS: (self.label_cond_table_hor_mot1_currpos, '{:,.2f}', 12, True),
            PV.COND_TABLE_HOR_MOT2_POS: (self.label_cond_table_hor_mot2_currpos, '{:,.2f}', 12, True),

            PV.COND_TABLE_VERT_STATUS: (self.label_cond_table_vert_status, '{:g}', 12, True),
            PV.COND_TABLE_VERT_GAP_POS: (self.label_cond_table_vert_gap_currpos, '{:,.2f}', 12, True),
            PV.COND_TABLE_VERT_CENT_POS: (self.label_cond_table_vert_cent_currpos, '{:,.2f}', 12, True),
            PV.COND_TABLE_VERT_MOT1_POS: (self.label_cond_table_vert_mot1_currpos, '{:,.2f}', 12, True),
            PV.COND_TABLE_VERT_MOT2_POS: (self.label_cond_table_vert_mot2_currpos, '{:,.2f}', 12, True),

            PV.COND_DIFF_HOR_STATUS: (self.label_cond_diff_hor_status, '{:g}', 12, True),
            PV.COND_DIFF_HOR_GAP_POS: (self.label_cond_diff_hor_gap_currpos, '{:,.2f}', 12, True),
            PV.COND_DIFF_HOR_CENT_POS: (self.label_cond_diff_hor_cent_currpos, '{:,.2f}', 12, True),
            PV.COND_DIFF_HOR_MOT1_POS: (self.label_cond_diff_hor_mot1_currpos, '{:,.2f}', 12, True),
            PV.COND_DIFF_HOR_MOT2_POS: (self.label_cond_diff_hor_mot2_currpos, '{:,.2f}', 12, True),

            PV.COND_DIFF_VERT_STATUS: (self.label_cond_diff_vert_status, '{:g}', 12, True),
            PV.COND_DIFF_VERT_GAP_POS: (self.label_cond_diff_vert_gap_currpos, '{:,.2f}', 12, True),
            PV.COND_DIFF_VERT_CENT_POS: (self.label_cond_diff_vert_cent_currpos, '{:,.2f}', 12, True),
            PV.COND_DIFF_VERT_MOT1_POS: (self.label_cond_diff_vert_mot1_currpos, '{:,.2f}', 12, True),
            PV.COND_DIFF_VERT_MOT2_POS: (self.label_cond_diff_vert_mot2_currpos, '{:,.2f}', 12, True),

            PV.COND_PB_APER_HOR_POS: (self.label_cond_pb_aper_hor_currpos, '{:,.2f}', 12, True),
            PV.COND_PB_APER_VERT_POS : (self.label_cond_pb_aper_vert_currpos, '{:,.2f}', 12, True),
            PV.COND_DAC_PIN_HOR_POS : (self.label_cond_dac_pin_hor_currpos, '{:,.2f}', 12, True),
            PV.COND_DAC_PIN_VERT_POS : (self.label_cond_dac_pin_vert_currpos, '{:,.2f}', 12, True),
            PV.COND_BEAM_STOP_HOR_POS : (self.label_cond_beam_stop_hor_currpos, '{:,.2f}', 12, True),
            PV.COND_BEAM_STOP_VERT_POS : (self.label_cond_beam_stop_vert_currpos, '{:,.2f}', 12, True),

            PV.COND_PB_APER_HOR_STATUS: (self.label_cond_pb_aper_hor_status, '{:g}', 12, True),
            PV.COND_PB_APER_VERT_STATUS: (self.label_cond_pb_aper_vert_status, '{:g}', 12, True),
            PV.COND_DAC_PIN_HOR_STATUS: (self.label_cond_dac_pin_hor_status, '{:g}', 12, True),
            PV.COND_DAC_PIN_VERT_STATUS: (self.label_cond_dac_pin_vert_status, '{:g}', 12, True),
            PV.COND_BEAM_STOP_HOR_STATUS: (self.label_cond_beam_stop_hor_status, '{:g}', 12, True),
            PV.COND_BEAM_STOP_VERT_STATUS: (self.label_cond_beam_stop_vert_status, '{:g}', 12, True),
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
        self.save_scan_props()
        self.save_cent_props()
        self.save_motors(self.Motors)

        self.scan_plot_id.terminate()
        self.cent_plot_id.terminate()
        self.cent_plot_id_1.terminate()
        self.cent_plot_id_2.terminate()
        self.cent_plot_id_3.terminate()

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
