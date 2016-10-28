# System imports
import simplejson
import os
import sys
from functools import partial
import threading
import time

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
from utils.local_save import RockMixin

from utils import Constant
from utils import to_rad

from utils.monitor import KEY as MONITOR_KEY

from utils.graph import Plotter
from utils.contour import Contour

from windows.css import GROUP_BOX_STYLE
from windows.css import GROUP_BOX_STYLE_NO_TITLE
from windows.css import CSS_COLOUR
from windows.css import CSS_LABEL_PV_LOST

from windows.pv_list_window import PvListWindow
from windows.drag_text_mixin import DragTextMixin

from windows.minor_windows import LoadPositions as LoadPositionsWindow
from windows.minor_windows import SetMotorSlot as SetMotorSlotWindow
from windows.minor_windows import SetServer as SaveServerWindow

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

RELEASE_DATE            = 'October 28th, 2016'

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

    def replace(self, pv_name, label, **kwargs):
        for PV, labels in self.label_dict.iteritems():  # delete all the old entries
            for i, _label in enumerate(labels):
                if label == _label:
                    del labels[i]
                    self.label_dict[PV] = labels
        labels = self.label_dict.get(pv_name, [])
        labels.append(label)
        self.label_dict[pv_name] = labels

        data = self.data_dict.get(label)
        if data is not None:
            print "Already have data for label", repr(label) + "Countinuing?"
            del self.data_dict[label]

        self.data_dict[label] = kwargs


class MainWindow(QtGui.QMainWindow, UiMixin, DragTextMixin, ServMixin, ScanMixin, CentMixin, MotMixin, RockMixin):

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
        self.core.error_callback(self.handle_signal_dialog_info)

        self._item_count = 0

        self.init_labels()

        actions = {
            self.action_about: self.handle_action_about,
            self.action_pv_list: self.handle_action_pv_list,
            self.action_var_list: self.handle_action_var_list,
            self.action_set_server: self.handle_action_set_server_wind,
            self.action_motor_slots: self.handle_action_motor_slots,
        }
        self.populateCentMenu()

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

            self.label_slit_1_motor_1_name,
            self.label_slit_1_motor_2_name,
            self.label_slit_1_motor_3_name,
            self.label_slit_1_motor_4_name,
            self.label_slit_2_motor_1_name,
            self.label_slit_2_motor_2_name,
            self.label_slit_2_motor_3_name,
            self.label_slit_2_motor_4_name,
            self.label_aper_motor_1_name,
            self.label_aper_motor_2_name,
            self.label_dac_motor_1_name,
            self.label_dac_motor_2_name,
            self.label_stop_motor_1_name,
            self.label_stop_motor_2_name,
            self.label_extra_motor_1_name,
            self.label_extra_motor_2_name,
            self.label_extra_motor_3_name,
            self.label_extra_motor_4_name,
            self.label_extra_motor_5_name,
            self.label_extra_motor_6_name,
        ]
        self.Motors = [self.Motor_1, self.Motor_2, self.Motor_3, self.Motor_4, self.Motor_5, self.Motor_6,

                       self.Slit_1_Motor_1, self.Slit_1_Motor_2, self.Slit_1_Motor_3, self.Slit_1_Motor_4,
                       self.Slit_2_Motor_1, self.Slit_2_Motor_2, self.Slit_2_Motor_3, self.Slit_2_Motor_4,
                       self.Aper_Motor_1, self.Aper_Motor_2,
                       self.Dac_Motor_1, self.Dac_Motor_2,
                       self.Stop_Motor_1, self.Stop_Motor_2,
                       self.Extra_Motor_1, self.Extra_Motor_2, self.Extra_Motor_3, self.Extra_Motor_4,
                       self.Extra_Motor_5, self.Extra_Motor_6,
                       ]

        self.Motors_Stage = [self.Motor_1, self.Motor_2, self.Motor_3, self.Motor_4, self.Motor_5, self.Motor_6]
        if not motor_props==False:
            for i in range(len(self.Motors)):
                self.Motors[i] = self.Motors[i]._replace(Name=motor_props[0][i], Mne=motor_props[1][i], Enabled=motor_props[2][i])
        self.update_motors(self.Motors)
        self.handle_pushButton_motor_all_checkpos(False)  # just checking position, False is a dummy var
        # Connect Buttons
        pushbuttons = [self.pushButton_motor_1_movego, self.pushButton_motor_2_movego, self.pushButton_motor_3_movego, 
                       self.pushButton_motor_4_movego, self.pushButton_motor_5_movego, self.pushButton_motor_6_movego,

                       self.pushButton_slit_1_motor_1_movego, self.pushButton_slit_1_motor_2_movego, self.pushButton_slit_1_motor_3_movego, self.pushButton_slit_1_motor_4_movego,
                       self.pushButton_slit_2_motor_1_movego, self.pushButton_slit_2_motor_2_movego, self.pushButton_slit_2_motor_3_movego, self.pushButton_slit_2_motor_4_movego,

                       self.pushButton_aper_motor_1_movego, self.pushButton_aper_motor_2_movego,
                       self.pushButton_dac_motor_1_movego, self.pushButton_dac_motor_2_movego,
                       self.pushButton_stop_motor_1_movego, self.pushButton_stop_motor_2_movego,

                       self.pushButton_extra_motor_1_movego, self.pushButton_extra_motor_2_movego, self.pushButton_extra_motor_3_movego,
                       self.pushButton_extra_motor_4_movego, self.pushButton_extra_motor_5_movego, self.pushButton_extra_motor_6_movego,
                       ]
        for i, but in enumerate(pushbuttons):
            but.clicked.connect(partial(self.handle_pushButton_motor_movego, i+1))

        self.pushButton_motor_all_checkpos.clicked.connect(self.handle_pushButton_motor_all_checkpos)
        self.pushButton_motor_all_move.clicked.connect(self.handle_pushButton_motor_all_move)
        self.pushButton_motor_all_stop.clicked.connect(self.handle_pushButton_motor_all_stop)

        self.checkBox_motor_all_checkpos.stateChanged.connect(self.handle_checkBox_motor_all_checkpos)
        self.checkBox_SPEC_checkpos.stateChanged.connect(self.handle_checkBox_SPEC_checkpos)
        
        """SCAN INIT"""
        # Connect Buttons
        self.pushButton_scan_start_stop.clicked.connect(self.handle_pushButton_scan_start_stop)
        self.pushButton_scan_save.clicked.connect(self.handle_save_scan)
        self.pushButton_scan_select_file.clicked.connect(partial(self.select_file, self.lineEdit_scan_select_file))

        self.lineEdit_scan_select_file.textChanged.connect(
            partial(self.core.update_filepath, self.lineEdit_scan_select_file, 'scan'))

        self.comboBox_scan_motor.currentIndexChanged.connect(self.handle_comboBox_scan_motor)
        self.comboBox_scan_data_x.activated.connect(self.handle_comboBox_scan_data)
        self.comboBox_scan_data_y.activated.connect(self.handle_comboBox_scan_data)

        self.pushButton_scan_start_stop.setText(self.scan_button_text())  # This means the button says Start instead of START/STOP

        self.checkBox_rel_scan.stateChanged.connect(partial(self.scan_rel, self.checkBox_rel_scan))
        # INIT RUN
        self.handle_comboBox_scan_motor()
        self.update_scan_cols()
        self.set_scan_props() # updating variables from the saved file (last session)
        self.core.update_filepath(self.lineEdit_scan_select_file, 'scan')
        self.scan_rel(self.checkBox_rel_scan)
        # Plot
        self.scan_plot_id = Plotter(monitor=self.monitor, VAR=VAR, id='scan')
        self.verticalLayout_scan_graph.addWidget(self.scan_plot_id)
        self.scan_plot_id.set_title(PLOT_TITLE)
        self.scan_plot_id.set_axis_label_x(PLOT_LABEL_X)
        self.scan_plot_id.set_axis_label_y(PLOT_LABEL_Y)
        # self.scan_plot_id.set_mouse_position_callback(self.callback_mouse_pos_id)
        self.scan_plot_id.set_legend()
        self.scan_plot_id.timer = QtCore.QTimer()

        """MESH INIT"""
        # Connect Buttons
        self.pushButton_mesh_start_stop.clicked.connect(self.handle_pushButton_mesh_start_stop)
        # self.pushButton_mesh_save.clicked.connect(self.handle_save_mesh)
        # self.pushButton_mesh_select_file.clicked.connect(partial(self.select_file, self.lineEdit_mesh_select_file))
        #
        # self.lineEdit_mesh_select_file.textChanged.connect(
        #     partial(self.core.update_filepath, self.lineEdit_mesh_select_file, 'mesh'))

        self.comboBox_mesh_slow_motor.currentIndexChanged.connect(self.handle_comboBox_mesh_motor)
        self.comboBox_mesh_fast_motor.currentIndexChanged.connect(self.handle_comboBox_mesh_motor)
        # self.comboBox_mesh_data_x.activated.connect(self.handle_comboBox_mesh_data)
        # self.comboBox_mesh_data_y.activated.connect(self.handle_comboBox_mesh_data)
        self.comboBox_mesh_data_intes.activated.connect(self.handle_comboBox_mesh_data)

        self.pushButton_mesh_move.clicked.connect(self.handle_pushButton_mesh_move)

        self.pushButton_mesh_start_stop.setText(
            self.mesh_button_text())  # This means the button says Start instead of START/STOP

        self.checkBox_rel_mesh.stateChanged.connect(partial(self.mesh_rel, self.checkBox_rel_mesh))
        # INIT RUN
        self.handle_comboBox_mesh_motor()
        self.update_mesh_cols()
        # self.set_mesh_props()  # updating variables from the saved file (last session)
        # self.core.update_filepath(self.lineEdit_mesh_select_file, 'mesh')
        self.mesh_rel(self.checkBox_rel_mesh)
        # Plot
        self.mesh_plot_id = Contour(monitor=self.monitor, VAR=VAR)
        self.verticalLayout_mesh_graph.addWidget(self.mesh_plot_id)
        self.checkBox_mesh_log.stateChanged.connect(partial(self.handle_checkBox_mesh_log, self.checkBox_mesh_log))
        self.mesh_plot_id.timer = QtCore.QTimer()

        """CENTER INIT"""
        # Connect Buttons
        self.pushButton_cent_start_stop.clicked.connect(self.handle_pushButton_cent_start_stop)
        self.pushButton_cent_save.clicked.connect(self.handle_save_cent)
        self.pushButton_cent_select_file.clicked.connect(partial(self.select_file, self.lineEdit_cent_select_file))

        self.lineEdit_scan_select_file.textChanged.connect(
            partial(self.core.update_filepath, self.lineEdit_scan_select_file, 'cent'))

        self.comboBox_cent_data_x.activated.connect(self.handle_comboBox_cent_data)
        self.comboBox_cent_data_y.activated.connect(self.handle_comboBox_cent_data)

        self.checkBox_cent_single.stateChanged.connect(partial(self.cent_graph, self.checkBox_cent_single))

        # Variables
        (self.cent_plot_id_1, self.cent_plot_id_2, self.cent_plot_id_3) = Plotter(monitor=self.monitor, VAR=VAR,
                                                                                  id='neg'), \
                                                                          Plotter(monitor=self.monitor, VAR=VAR,
                                                                                  id='nau'), \
                                                                          Plotter(monitor=self.monitor, VAR=VAR,
                                                                                  id='pos')
        self.plots = [self.cent_plot_id_1, self.cent_plot_id_2, self.cent_plot_id_3]
        self.cent_plot_id = Plotter(monitor=self.monitor, VAR=VAR, id='multi')
        self.cent_timer = QtCore.QTimer()

        # INIT RUN
        self.update_cent_cols()
        self.set_cent_props()  # updating variables from the saved file (last session)
        self.populateCentSubMenus(self.Motors_Stage)
        # self.handle_comboBox_cent_motor()
        self.init_cent_graph(self.checkBox_cent_single.isChecked())
        self.core.update_filepath(self.lineEdit_cent_select_file, 'cent')
        self.core.is_centering(self.pushButton_cent_start_stop, label=self.label_cent_center_name)
        
        """ROCKING INIT"""
        # Connect Buttons
        self.pushButton_rock_start_stop.clicked.connect(self.handle_pushButton_rock_start_stop)
        self.pushButton_rock_save.clicked.connect(self.handle_save_rock)
        self.pushButton_rock_select_file.clicked.connect(partial(self.select_file, self.lineEdit_rock_select_file))

        self.lineEdit_scan_select_file.textChanged.connect(
            partial(self.core.update_filepath, self.lineEdit_scan_select_file, 'rock'))

        self.comboBox_rock_motor.currentIndexChanged.connect(self.handle_comboBox_rock_motor)
        self.comboBox_rock_data_x.activated.connect(self.handle_comboBox_rock_data)
        self.comboBox_rock_data_y.activated.connect(self.handle_comboBox_rock_data)
        self.checkBox_rock_zone1.stateChanged.connect(self.omit_hide)
        self.checkBox_rock_zone2.stateChanged.connect(self.omit_hide)
        self.checkBox_rock_zone3.stateChanged.connect(self.omit_hide)
        self.checkBox_rock_zone4.stateChanged.connect(self.omit_hide)
        # INIT RUN
        self.handle_comboBox_rock_motor()

        self.update_rock_cols()
        self.set_rock_props()  # updating variables from the saved file (last session)
        self.core.update_filepath(self.lineEdit_rock_select_file, 'rock')
        self.omit_hide()
        # Plot
        self.rock_plot_id = Plotter(monitor=self.monitor, VAR=VAR, id='rock')
        self.verticalLayout_rock_graph.addWidget(self.rock_plot_id)
        self.rock_plot_id.set_title(PLOT_TITLE)
        self.rock_plot_id.set_axis_label_x(PLOT_LABEL_X)
        self.rock_plot_id.set_axis_label_y(PLOT_LABEL_Y)
        # self.rock_plot_id.set_mouse_position_callback(self.callback_mouse_pos_id)
        self.rock_plot_id.set_legend()
        self.rock_plot_id.timer = QtCore.QTimer()

        """CONDITIONING"""
        self.init_beam_cond()

        """PICTURE"""
        pic = QtGui.QLabel(self.label_motor_picture)
        pixmap = QtGui.QPixmap('graphics/stage_background.png')
        pic.setPixmap(pixmap.scaled(500, 500, QtCore.Qt.KeepAspectRatio))
        pic.show()

        """POPOUTS"""
        self.pushButton_open_pos_load.clicked.connect(self.handle_action_save_load)
        self.saved_pos = []

        """RANDOM"""

        self.all_plots = [self.scan_plot_id, self.rock_plot_id, self.mesh_plot_id, self.cent_plot_id,
                          self.cent_plot_id_1, self.cent_plot_id_2, self.cent_plot_id_3, ]

        self.init_label_props()

        self.lineEdit_send_SPEC.returnPressed.connect(self.handle_lineEdit_send_SPEC)

        self.old_scan_x, self.old_scan_y = ([] for _ in range(2))
        self.old_mesh_x, self.old_mesh_y, self.old_mesh_intes = ([] for _ in range(3))


    """POPUPS"""
    def handle_action_save_load(self):  # starts our cell saving/loading popup
        center_point = self.geometry().center() # Opens at center of OG window
        window = LoadPositionsWindow(monitor=self.monitor,
                                     center=center_point,
                                     motors=self.Motors_Stage,
                                     formatter=self.formatter,
                                     saved_pos=self.saved_pos,
                                     )
        window.update_callback(self.update_saved_pos)
        self.handle_action_popup(window)

    def handle_action_motor_slots(self):  # starts the motor slotting popup
        center_point = self.geometry().center()
        window = SetMotorSlotWindow(monitor=self.monitor,
                                    center=center_point,
                                    motors=self.Motors)
        window.apply_callback(self.update_motors)
        self.handle_action_popup(window)

    def handle_action_set_server_wind(self): # starts the server setting popup
        center_point = self.geometry().center()
        window = SaveServerWindow(monitor=self.monitor,
                                  center=center_point,
                                  host=self.monitor.get_value(VAR.SERVER_HOST),
                                  port=self.monitor.get_value(VAR.SERVER_PORT))
        window.apply_callback(self.core.set_server)
        self.handle_action_popup(window)

    def handle_action_popup(self, window):  # General actions for popups
        self.child_windows.append(window)  # get references of what popups are open for ref
        window.set_close_callback(self.callback_window_closed)
        window.show()

    """MOTOR"""
    @decorator_busy_cursor
    def handle_pushButton_motor_movego(self, num, dummy):  # Will pass the ref to relevant motor
        self.core.move_motor(self.Motors[num-1]) # Motor numbering starts at 1, the list does not have a blank 0th entry

    def handle_pushButton_motor_all_move(self): # this just calls the moving function if enabled for each
        for motor in self.Motors_Stage:
            if motor.Enabled:
                self.core.move_motor(motor)

    def handle_pushButton_motor_all_checkpos(self,dummy):  # calls a check_pos for each motor if enabled
        for motor in self.Motors_Stage:
            if motor.Enabled:
                self.core.checkpos_motor(motor)

    def handle_checkBox_motor_all_checkpos(self):  # Enables/disables constant position tracking
        self.core.stage_motor_track_state(self.checkBox_motor_all_checkpos.isChecked())

    def handle_checkBox_SPEC_checkpos(self):  # Enables/disables constant position tracking
        self.core.extra_motor_track_state(self.checkBox_SPEC_checkpos.isChecked())

    def handle_pushButton_motor_all_stop(self):
        for motor in self.Motors_Stage:
            if motor.Enabled:
                self.core.motor_stop(motor)

    def init_motor_slots(self):  # crude way of initalizing all of the motor "slots" for which we will assign motors later
        Motor_Slot = namedtuple('Motor_Slot',
                                ['Name', 'Mne', 'Enabled', 'Pos_VAR', 'Moveto_SB', 'Move_PB', 'MoveType_CB', 'Extra'])
        self.Motor_1 = Motor_Slot(Pos_VAR=VAR.MOTOR_1_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_1_moveto,
                                  Move_PB=self.pushButton_motor_1_movego,
                                  MoveType_CB=self.comboBox_motor_1_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  Extra=False,
                                  )
        self.Motor_2 = Motor_Slot(Pos_VAR=VAR.MOTOR_2_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_2_moveto,
                                  Move_PB=self.pushButton_motor_2_movego,
                                  MoveType_CB=self.comboBox_motor_2_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False,
                                  Extra=False,
                                  )
        self.Motor_3 = Motor_Slot(Pos_VAR=VAR.MOTOR_3_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_3_moveto,
                                  Move_PB=self.pushButton_motor_3_movego,
                                  MoveType_CB=self.comboBox_motor_3_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=False,
                                  )
        self.Motor_4 = Motor_Slot(Pos_VAR=VAR.MOTOR_4_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_4_moveto,
                                  Move_PB=self.pushButton_motor_4_movego,
                                  MoveType_CB=self.comboBox_motor_4_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=False,
                                  )
        self.Motor_5 = Motor_Slot(Pos_VAR=VAR.MOTOR_5_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_5_moveto,
                                  Move_PB=self.pushButton_motor_5_movego,
                                  MoveType_CB=self.comboBox_motor_5_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=False,
                                  )
        self.Motor_6 = Motor_Slot(Pos_VAR=VAR.MOTOR_6_POS,
                                  Moveto_SB=self.doubleSpinBox_motor_6_moveto,
                                  Move_PB=self.pushButton_motor_6_movego,
                                  MoveType_CB=self.comboBox_motor_6_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=False,
                                  )
        self.Slit_1_Motor_1 = Motor_Slot(Pos_VAR=VAR.SLIT_1_MOTOR_1_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_1_motor_1_moveto,
                                  Move_PB=self.pushButton_slit_1_motor_1_movego,
                                  MoveType_CB=self.comboBox_slit_1_motor_1_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Slit_1_Motor_2 = Motor_Slot(Pos_VAR=VAR.SLIT_1_MOTOR_2_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_1_motor_2_moveto,
                                  Move_PB=self.pushButton_slit_1_motor_2_movego,
                                  MoveType_CB=self.comboBox_slit_1_motor_2_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Slit_1_Motor_3 = Motor_Slot(Pos_VAR=VAR.SLIT_1_MOTOR_3_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_1_motor_3_moveto,
                                  Move_PB=self.pushButton_slit_1_motor_3_movego,
                                  MoveType_CB=self.comboBox_slit_1_motor_3_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Slit_1_Motor_4 = Motor_Slot(Pos_VAR=VAR.SLIT_1_MOTOR_4_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_1_motor_4_moveto,
                                  Move_PB=self.pushButton_slit_1_motor_4_movego,
                                  MoveType_CB=self.comboBox_slit_1_motor_4_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                         )
        
        self.Slit_2_Motor_1 = Motor_Slot(Pos_VAR=VAR.SLIT_2_MOTOR_1_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_2_motor_1_moveto,
                                  Move_PB=self.pushButton_slit_2_motor_1_movego,
                                  MoveType_CB=self.comboBox_slit_2_motor_1_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Slit_2_Motor_2 = Motor_Slot(Pos_VAR=VAR.SLIT_2_MOTOR_2_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_2_motor_2_moveto,
                                  Move_PB=self.pushButton_slit_2_motor_2_movego,
                                  MoveType_CB=self.comboBox_slit_2_motor_2_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Slit_2_Motor_3 = Motor_Slot(Pos_VAR=VAR.SLIT_2_MOTOR_3_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_2_motor_3_moveto,
                                  Move_PB=self.pushButton_slit_2_motor_3_movego,
                                  MoveType_CB=self.comboBox_slit_2_motor_3_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Slit_2_Motor_4 = Motor_Slot(Pos_VAR=VAR.SLIT_2_MOTOR_4_POS,
                                  Moveto_SB=self.doubleSpinBox_slit_2_motor_4_moveto,
                                  Move_PB=self.pushButton_slit_2_motor_4_movego,
                                  MoveType_CB=self.comboBox_slit_2_motor_4_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )

        self.Aper_Motor_1 = Motor_Slot(Pos_VAR=VAR.APER_MOTOR_1_POS,
                                         Moveto_SB=self.doubleSpinBox_aper_motor_1_moveto,
                                         Move_PB=self.pushButton_aper_motor_1_movego,
                                         MoveType_CB=self.comboBox_aper_motor_1_movetype,
                                         Name='',
                                         Mne='',
                                         Enabled=False, 
                                  Extra=True,
                                         )
        self.Aper_Motor_2 = Motor_Slot(Pos_VAR=VAR.APER_MOTOR_2_POS,
                                         Moveto_SB=self.doubleSpinBox_aper_motor_2_moveto,
                                         Move_PB=self.pushButton_aper_motor_2_movego,
                                         MoveType_CB=self.comboBox_aper_motor_2_movetype,
                                         Name='',
                                         Mne='',
                                         Enabled=False, 
                                  Extra=True,
                                         )

        self.Dac_Motor_1 = Motor_Slot(Pos_VAR=VAR.DAC_MOTOR_1_POS,
                                         Moveto_SB=self.doubleSpinBox_dac_motor_1_moveto,
                                         Move_PB=self.pushButton_dac_motor_1_movego,
                                         MoveType_CB=self.comboBox_dac_motor_1_movetype,
                                         Name='',
                                         Mne='',
                                         Enabled=False, 
                                  Extra=True,
                                         )
        self.Dac_Motor_2 = Motor_Slot(Pos_VAR=VAR.DAC_MOTOR_2_POS,
                                         Moveto_SB=self.doubleSpinBox_dac_motor_2_moveto,
                                         Move_PB=self.pushButton_dac_motor_2_movego,
                                         MoveType_CB=self.comboBox_dac_motor_2_movetype,
                                         Name='',
                                         Mne='',
                                         Enabled=False, 
                                  Extra=True,
                                         )

        self.Stop_Motor_1 = Motor_Slot(Pos_VAR=VAR.STOP_MOTOR_1_POS,
                                         Moveto_SB=self.doubleSpinBox_stop_motor_1_moveto,
                                         Move_PB=self.pushButton_stop_motor_1_movego,
                                         MoveType_CB=self.comboBox_stop_motor_1_movetype,
                                         Name='',
                                         Mne='',
                                         Enabled=False, 
                                  Extra=True,
                                         )
        self.Stop_Motor_2 = Motor_Slot(Pos_VAR=VAR.STOP_MOTOR_2_POS,
                                         Moveto_SB=self.doubleSpinBox_stop_motor_2_moveto,
                                         Move_PB=self.pushButton_stop_motor_2_movego,
                                         MoveType_CB=self.comboBox_stop_motor_2_movetype,
                                         Name='',
                                         Mne='',
                                         Enabled=False, 
                                  Extra=True,
                                         )

        self.Extra_Motor_1 = Motor_Slot(Pos_VAR=VAR.EXTRA_MOTOR_1_POS,
                                  Moveto_SB=self.doubleSpinBox_extra_motor_1_moveto,
                                  Move_PB=self.pushButton_extra_motor_1_movego,
                                  MoveType_CB=self.comboBox_extra_motor_1_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Extra_Motor_2 = Motor_Slot(Pos_VAR=VAR.EXTRA_MOTOR_2_POS,
                                  Moveto_SB=self.doubleSpinBox_extra_motor_2_moveto,
                                  Move_PB=self.pushButton_extra_motor_2_movego,
                                  MoveType_CB=self.comboBox_extra_motor_2_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Extra_Motor_3 = Motor_Slot(Pos_VAR=VAR.EXTRA_MOTOR_3_POS,
                                  Moveto_SB=self.doubleSpinBox_extra_motor_3_moveto,
                                  Move_PB=self.pushButton_extra_motor_3_movego,
                                  MoveType_CB=self.comboBox_extra_motor_3_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Extra_Motor_4 = Motor_Slot(Pos_VAR=VAR.EXTRA_MOTOR_4_POS,
                                  Moveto_SB=self.doubleSpinBox_extra_motor_4_moveto,
                                  Move_PB=self.pushButton_extra_motor_4_movego,
                                  MoveType_CB=self.comboBox_extra_motor_4_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Extra_Motor_5 = Motor_Slot(Pos_VAR=VAR.EXTRA_MOTOR_5_POS,
                                  Moveto_SB=self.doubleSpinBox_extra_motor_5_moveto,
                                  Move_PB=self.pushButton_extra_motor_5_movego,
                                  MoveType_CB=self.comboBox_extra_motor_5_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )
        self.Extra_Motor_6 = Motor_Slot(Pos_VAR=VAR.EXTRA_MOTOR_6_POS,
                                  Moveto_SB=self.doubleSpinBox_extra_motor_6_moveto,
                                  Move_PB=self.pushButton_extra_motor_6_movego,
                                  MoveType_CB=self.comboBox_extra_motor_6_movetype,
                                  Name='',
                                  Mne='',
                                  Enabled=False, 
                                  Extra=True,
                                  )

    def update_motors(self, Motors):  # we update all of the motors
        self.core._move_terminate_flag = True  # we let all of the motor threads die (1.5 sec), then we start them again
        t = threading.Timer(1.5,  self.core.update_motors, [self.motor_names, Motors,
            (self.comboBox_scan_motor, self.comboBox_rock_motor, self.comboBox_mesh_slow_motor, self.comboBox_mesh_fast_motor)])
        t.start()
        self.Motors = Motors
        self.Motors_Stage = []
        for motor in self.Motors:
            if not motor.Extra:
                self.Motors_Stage.append(motor)
        self.populateCentSubMenus(self.Motors_Stage)

    """SCAN"""
    def scan_button_text(self):
        if self.core.is_scanning(self.pushButton_scan_start_stop):
            return 'Stop'
        else:
            return 'Start'

    def handle_pushButton_scan_start_stop(self):
        (start, stop) = self.doubleSpinBox_scan_startpos.value(), self.doubleSpinBox_scan_stoppos.value()
        if self.checkBox_rel_scan.isChecked():
            start = start + float(str(self.label_rel_curr_pos.text()))
            stop = stop + float(str(self.label_rel_curr_pos.text()))
        if self.core.is_scanning(self.pushButton_scan_start_stop):
            self.core.scan_stop()
        else:
            if self.checkBox_scan_return_home.checkState():# What Mode True = dscan False = ascan
                type = 'Rel'
            else :
                type = 'Abs'
            if self.comboBox_scan_motor.currentIndex() == -1:
                dialog_info(msg="Motor was not chosen, \nscanning cannot begin")
            else:
                self.core.scan_start(type,
                                     self.comboBox_scan_motor.currentText(),  # Which Motor are we using? Passes NAME back
                                     start,  # the rest are just values
                                     stop,
                                     self.doubleSpinBox_scan_steps.value(),
                                     self.doubleSpinBox_scan_waittime.value(),
                                     self.Motors  # We need to pass this so we can see which motor we are scanning with
                                     )
                self.scan_plot_id.timer.start(100.0) # we replot every 10th of a second
                self.connect(self.scan_plot_id.timer, QtCore.SIGNAL('timeout()'), self.scan_plot)

    def scan_rel(self, check):
        if check.isChecked():  # if we want a relative scan we set some names as well.
            start = 'Relative Start'
            stop = 'Relative Stop'
        else:
            start = 'Start Location'
            stop = 'Stop Location'
        self.label_rel_curr_pos.setEnabled(check.isChecked())
        self.label_scan_startpos_name.setText(start)
        self.label_scan_stoppos_name.setText(stop)

    def scan_plot(self):  # we get data and if it's different we update everything
        go, x, y = self.core.get_data(self.comboBox_scan_data_x.currentIndex(),
                                      self.comboBox_scan_data_y.currentIndex())

        if not self.old_scan_x == x or not self.old_scan_y == y and go:
            self.core.update_bar_pos(VAR.VERT_BAR_SCAN_X, x)
            self.scan_plot_id.new_plot(x, y)
            self.core.scan_calculations(x, y)
            self.update_table(self.tableWidget_scan_data, [x,y])
        (self.old_scan_x, self.old_scan_y) = x, y

    def update_table(self, Table, cols ):
        Table.setHorizontalHeaderLabels([self.comboBox_scan_data_x.currentText(), self.comboBox_scan_data_y.currentText(),])
        Table.setColumnCount(len(cols))
        Table.setRowCount(len(cols[0]))
        Table.horizontalHeader().setResizeMode(Qt.QHeaderView.ResizeToContents)
        Table.setFixedWidth(Table.horizontalHeader().length() + 50)
        for col in range(len(cols)):
            for row in range(len(cols[0])):
                Table.setItem(row, col, QtGui.QTableWidgetItem(QtCore.QString("%1").arg(cols[col][row])))

    def handle_comboBox_scan_motor(self): # if you choose a different scan motor we update some stuff to recognize that
        self.core.scan_settings(self.comboBox_scan_motor.currentText(),
                                self.doubleSpinBox_scan_startpos,
                                self.doubleSpinBox_scan_stoppos,
                                self.Motors,
                                self.doubleSpinBox_scan_waittime
                                )
        try:
            self.add_label({self.core.get_motor(self.comboBox_scan_motor.currentText(), self.Motors).Pos_VAR: (self.label_rel_curr_pos, '{:.3f}', 12, True),}, double=True)
        except AttributeError:
            print "Scan motor Not set"

    def update_scan_cols(self):
        self.core.update_CB(self.comboBox_scan_data_x, self.comboBox_scan_data_y, 'scan')

    def handle_comboBox_scan_data(self):
        pass

    def handle_save_scan(self):
        self.core.save_scan_curr(str(self.lineEdit_scan_filename.text()),
                                 self.comboBox_scan_data_x,
                                 self.comboBox_scan_data_y,
                                 )

    """MESH"""  # There are lots of coding similarities between all the scan types, it would have been ideal to make scanning classes
    def handle_checkBox_mesh_log(self, PB): # is it logarthmic?
        self.mesh_plot_id.log_check(PB.isChecked())

    def mesh_button_text(self):
        if self.core.is_meshing(self.pushButton_mesh_start_stop):
            return 'Stop'
        else:
            return 'Start'

    def handle_pushButton_mesh_start_stop(self):
        (f_start, f_stop) = self.doubleSpinBox_fast_mesh_startpos.value(), self.doubleSpinBox_fast_mesh_stoppos.value()
        (s_start, s_stop) = self.doubleSpinBox_slow_mesh_startpos.value(), self.doubleSpinBox_slow_mesh_stoppos.value()
        if self.checkBox_rel_mesh.isChecked():
            s_start = s_start + float(str(self.label_slow_mesh_currpos.text()))
            s_stop = s_stop + float(str(self.label_slow_mesh_currpos.text()))
            f_start = f_start + float(str(self.label_fast_mesh_currpos.text()))
            f_stop = f_stop + float(str(self.label_fast_mesh_currpos.text()))
        if self.core.is_meshing(self.pushButton_mesh_start_stop):
            self.core.mesh_stop()
        else:
            if self.comboBox_mesh_slow_motor.currentIndex() == -1 or self.comboBox_mesh_fast_motor.currentIndex() == -1:
                dialog_info(msg="Motor was not chosen, \nmeshing cannot begin")
            else:
                self.core.mesh_start(self.comboBox_mesh_fast_motor.currentText(),
                                     self.comboBox_mesh_slow_motor.currentText(),# Which Motor are we using? Passes NAME back
                                     f_start,  # the rest are just values
                                     f_stop,
                                     s_start,  # the rest are just values
                                     s_stop,
                                     self.doubleSpinBox_fast_mesh_steps.value(),
                                     self.doubleSpinBox_slow_mesh_steps.value(),
                                     self.doubleSpinBox_mesh_waittime.value(),
                                     self.Motors  # We need to pass this so we can see which motor we are meshing with
                                     )
                # self.fast_ind, self.slow_ind = self.doubleSpinBox_fast_mesh_steps.value(), self.doubleSpinBox_slow_mesh_steps.value()
                self.mesh_plot_id.timer.start(500.0)
                self.connect(self.mesh_plot_id.timer, QtCore.SIGNAL('timeout()'), self.mesh_plot)

    def mesh_rel(self, check):
        if check.isChecked():
            start = 'Relative Start'
            stop = 'Relative Stop'
        else:
            start = 'Start Location'
            stop = 'Stop Location'
        self.label_slow_mesh_currpos.setEnabled(check.isChecked())
        self.label_fast_mesh_currpos.setEnabled(check.isChecked())
        self.label_mesh_startpos_name.setText(start)
        self.label_mesh_stoppos_name.setText(stop)

    def mesh_plot(self):
        self.scan_plot()
        go, x, y, intes = self.core.get_mesh_data(
            0, 1,  # hardcoding motors in
            # self.comboBox_mesh_data_x.currentIndex(),
            #                                self.comboBox_mesh_data_y.currentIndex(),
                                           self.comboBox_mesh_data_intes.currentIndex(), )
        if not self.core.get_motor(self.comboBox_mesh_slow_motor.currentText(), self.Motors).Mne == self.label_mesh_data_x.text() or \
                not self.core.get_motor(self.comboBox_mesh_fast_motor.currentText(), self.Motors).Mne == self.label_mesh_data_y.text():
            self.update_mesh_cols()
            self.mesh_plot_id.set_axis_label_x(self.core.get_motor(self.comboBox_mesh_fast_motor.currentText(), self.Motors).Name + "(mm)")
            self.mesh_plot_id.set_axis_label_y(self.core.get_motor(self.comboBox_mesh_slow_motor.currentText(), self.Motors).Name + "(mm)" )
        if not self.old_mesh_x == x or not self.old_mesh_y == y or not self.old_mesh_intes == intes and go:
            self.mesh_plot_id.plot(x, y, intes)
            self.core.mesh_calculations(x, y, intes)
        (self.old_mesh_x, self.old_mesh_y, self.old_mesh_intes) = x, y, intes
        
    def handle_comboBox_mesh_motor(self):
        self.core.mesh_settings(self.comboBox_mesh_fast_motor.currentText(),
                                self.doubleSpinBox_fast_mesh_startpos,
                                self.doubleSpinBox_fast_mesh_stoppos,
                                self.comboBox_mesh_slow_motor.currentText(),
                                self.doubleSpinBox_slow_mesh_startpos,
                                self.doubleSpinBox_slow_mesh_stoppos,
                                self.Motors,
                                self.doubleSpinBox_mesh_waittime
                                )
        try:
            self.add_label({self.core.get_motor(self.comboBox_mesh_slow_motor.currentText(), self.Motors).Pos_VAR: (
            self.label_slow_mesh_currpos, '{:.3f}', 12, True), }, double=True)
        except AttributeError:
            print "Slow Mesh motor Not set"
        try:
            self.add_label({self.core.get_motor(self.comboBox_mesh_fast_motor.currentText(), self.Motors).Pos_VAR: (
                self.label_fast_mesh_currpos, '{:.3f}', 12, True), }, double=True)
        except AttributeError:
            print "Fast Mesh motor Not set"
            
    def update_mesh_cols(self):
        self.core.update_CB(None, None, 'mesh', intes_CB=self.comboBox_mesh_data_intes)
        self.label_mesh_data_x.setText(self.core.scanner_names[str(0)])
        self.label_mesh_data_y.setText(self.core.scanner_names[str(1)])

    def handle_comboBox_mesh_data(self):
        pass

    def handle_pushButton_mesh_move(self):
        self.core.mesh_move(self.comboBox_mesh_moveoption.currentText(), self.label_mesh_data_x.text(), self.label_mesh_data_y.text(), self.Motors)

    # def handle_save_mesh(self):
    #     self.core.save_mesh_curr(str(self.lineEdit_mesh_filename.text()),
    #                              self.comboBox_mesh_data_x,
    #                              self.comboBox_mesh_data_y,
    #                              )

    """CENTER"""
    def handle_comboBox_cent_motor(self): # Initazlizing the boxes to set limits and such things
        self.core.cent_settings(self.cent_dict.get('Scan X'),
                            self.cent_dict.get('Angular Motor'),
                            self.doubleSpinBox_cent_relmax,
                            self.doubleSpinBox_cent_relmin,
                            self.doubleSpinBox_cent_angle_pm,
                            self.doubleSpinBox_cent_angle_o,
                            self.Motors_Stage,
                            self.doubleSpinBox_cent_waittime,
                            self.comboBox_cent_calc_choose,
                            )
        try:
            self.add_label({self.core.get_motor(self.cent_dict.get('Scan X'), self.Motors_Stage).Pos_VAR: (
            self.label_cent_center, '{:.3f}', 12, True), }, double=True)
        except AttributeError:
            print "Cent scan motor Not set"

    def handle_pushButton_cent_start_stop(self):
        if self.core.is_centering(self.pushButton_cent_start_stop, label=self.label_cent_center_name):
            self.core.cent_stop()
        else:
            if str(self.label_cent_motor_scan.text()) == None or str(self.label_cent_motor_angle.text()) == None:
                dialog_info(msg="One or more motors were not chosen, \ncentering cannot begin")
            else:
                self.core.cent_start(self.cent_dict.get('Scan X'),
                                     self.cent_dict.get('Angular Motor'),
                                     self.doubleSpinBox_cent_relmax.value(),
                                     self.doubleSpinBox_cent_relmin.value(),
                                     float(str(self.label_cent_center.text())),
                                     self.doubleSpinBox_cent_angle_pm.value(),
                                     self.doubleSpinBox_cent_angle_o.value(),
                                     self.doubleSpinBox_cent_steps.value(),
                                     self.doubleSpinBox_cent_waittime.value(),
                                     self.Motors_Stage,
                                     )
                self.cent_timer.start(250.0)
                self.connect(self.cent_timer,  QtCore.SIGNAL('timeout()'), self.cent_plot)

    def cent_plot(self):
        self.scan_plot()  # makes it so that the plot also displays on the scan tab
        if self.checkBox_cent_single.isChecked():
            plot = self.cent_plot_id
        else:
            plot = self.plots
        self.core.cent_plotting(plot, self.tableWidget_cent_data,  # plotting and tables are offloaded to core as it became complex
                                self.comboBox_cent_data_x, self.comboBox_cent_data_y,
                                self.comboBox_cent_calc_choose, self.checkBox_cent_single.isChecked())
        self.tableWidget_cent_data.horizontalHeader().setResizeMode(Qt.QHeaderView.ResizeToContents)
        self.tableWidget_cent_data.setFixedWidth(self.tableWidget_cent_data.horizontalHeader().length() + 50)

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
        name = ['w-', 'wo', 'w+']
        for i, plot in enumerate(self.plots):
            self.verticalLayout_cent_graph.addWidget(plot)
            plot.setSizePolicy(Qt.QSizePolicy.Ignored, Qt.QSizePolicy.Ignored)
            if i == 0:
                plot.set_title(PLOT_TITLE)  # only put title on the top
            elif i == 2:
                plot.set_axis_label_x(PLOT_LABEL_X)  # only put x axis title on bottem
            plot.set_axis_label_y(PLOT_LABEL_Y + ' ' + name[i])
        self.cent_graph(single)

    def cent_graph(self, Check):
        try: # we will allow sending the check object or the bool value
            single = Check.isChecked()
        except AttributeError:
            single = Check
        if single:
            for plot in self.plots:
                plot.hide()
            self.cent_plot_id.show()
        else:
            for plot in self.plots:
                plot.show()
            self.cent_plot_id.hide()

    def populateCentMenu(self):  # Making the drop down menus
        self.cent_menus = ['Centre X', 'Centre Y', 'Scan X', 'Angular Motor']
        for i, menu in enumerate(self.cent_menus):
            self.cent_menus[i] = self.menuCentering.addMenu(menu)

    def populateCentSubMenus(self, Motors):   # Continuing to make the drop down menus for choosing centering motors
        motor_list = []
        dict_check=False
        try:
            if not self.cent_dict == None:
                dict_check = True
        except AttributeError:
            self.cent_dict = {}
        for motor in Motors:
            if motor.Enabled and not motor.Extra:
                motor_list.append(motor.Name)
        for menu in self.cent_menus:
            menu.clear()
            motor_group = QtGui.QActionGroup(self, exclusive=True)
            for motor in motor_list:
                action = QtGui.QAction(motor, menu, checkable=True)
                menuItem = motor_group.addAction(action)
                receiver = lambda motor=(str(menu.title()), str(motor)): self.SetCentMotor(motor)
                self.connect(menuItem, Qt.SIGNAL('triggered()'), receiver)
                if dict_check:
                    for key, value in self.cent_dict.items():
                        if key == str(menu.title()) and motor == value:
                            menuItem.setChecked(True)
                menu.addAction(menuItem)
        self.update_cent_labels(self.cent_dict)
        self.handle_comboBox_cent_motor()

    def SetCentMotor(self, motor):
        (motortype, value) = motor
        self.cent_dict[motortype] = value
        print 'Menu Clicked ', value, " Motor: ", motortype
        self.update_cent_labels(self.cent_dict)
        self.handle_comboBox_cent_motor()

    def update_cent_labels(self, cent_dict):
        for key, value in cent_dict.items():
            if key == 'Scan X':
                self.monitor.update(VAR.CENT_SCAN_MOTOR, value)
            elif key == 'Angular Motor':
                self.monitor.update(VAR.CENT_AMGLE_MOTOR, value)
            
    """ROCKING"""
    def handle_comboBox_rock_motor(self):  # Again rocking is similar to the otehr types of scans
        self.core.rock_settings(self.comboBox_rock_motor.currentText(),
                                self.doubleSpinBox_rock_startpos,
                                self.doubleSpinBox_rock_stoppos,
                                self.Motors_Stage,
                                self.doubleSpinBox_rock_waittime
                                )
        try:
            self.add_label({self.core.get_motor(self.comboBox_rock_motor.currentText(), self.Motors_Stage).Pos_VAR: (self.label_motor_currpos, '{:.3f}', 12, True),}, double=True)
        except AttributeError:
            print "Rocking motor Not set"

    def check_omit(self, passback=False):  # get our omitted zones in a nice list
        all_regions = [
            [self.checkBox_rock_zone1.isChecked(), self.doubleSpinBox_rock_min_zone1, self.doubleSpinBox_rock_max_zone1],
            [self.checkBox_rock_zone2.isChecked(), self.doubleSpinBox_rock_min_zone2, self.doubleSpinBox_rock_max_zone2],
            [self.checkBox_rock_zone3.isChecked(), self.doubleSpinBox_rock_min_zone3, self.doubleSpinBox_rock_max_zone3],
            [self.checkBox_rock_zone4.isChecked(), self.doubleSpinBox_rock_min_zone4, self.doubleSpinBox_rock_max_zone4],
            ]
        omit = []
        for region in all_regions:
            if region[0]:
                omit.append([region[1].value(), region[2].value()],)
        if passback:
            return omit, all_regions
        else:
            return omit

    def omit_hide(self):
        (omit, all_regions) = self.check_omit(True)
        for region in all_regions:
            region[1].setEnabled(region[0])
            region[2].setEnabled(region[0])

    def handle_pushButton_rock_start_stop(self):
        if self.core.is_rocking(self.pushButton_rock_start_stop):
            self.core.rock_stop(self.Motors_Stage)
        elif self.core.is_scanning() == True or self.core.is_centering == True:
            print "Cannot rock, there is currently an operation ongoing (scanning or centering)"
        else:
            if self.comboBox_rock_motor.currentIndex() == -1 :
                dialog_info(msg="The motor were not chosen, \nrocking cannot begin")
            else:
                self.core.rock_start(self.comboBox_rock_motor.currentText(),  # Which Motor are we using? Passes NAME back
                                     self.doubleSpinBox_rock_startpos.value(),  # the rest are just values
                                     self.doubleSpinBox_rock_stoppos.value(),
                                     self.doubleSpinBox_rock_steps.value(),
                                     self.doubleSpinBox_rock_waittime.value(),
                                     self.Motors_Stage,  # We need to pass this so we can see which motor we are rockning with
                                     self.check_omit(),
                                     self.doubleSpinBox_rock_time.value(),
                                     self.label_motor_currpos,
                                     self.progressBar_rock,
                                     )
                self.rock_plot_id.timer.start(250.0)
                self.connect(self.rock_plot_id.timer, QtCore.SIGNAL('timeout()'), self.rock_plot)

    def rock_plot(self):
        self.scan_plot()  # makes it so that the plot also displays on the scan tab
        self.core.rock_plotting(self.rock_plot_id, self.comboBox_rock_data_x, self.comboBox_rock_data_y)
        self.progressBar_rock.setValue(int(time.time() - self.core.start_rock))
        if not self.core.rock_event.isSet():
            self.progressBar_rock.setMaximum(0)
    
    def update_rock_cols(self):
        self.core.update_CB(self.comboBox_rock_data_x, self.comboBox_rock_data_y, 'rock')
        
    def handle_save_rock(self):
        self.core.save_rock_curr(str(self.lineEdit_rock_filename.text()),
                                 self.comboBox_rock_data_x,
                                 self.comboBox_rock_data_y,
                                 )

    def handle_comboBox_rock_data(self):
        pass

    """CONDITIONING"""  # these are the EPICS motor controls here. Barebones
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
            # move.MoveType_CB.addItems(['Relative', 'Absolute'])
            # move.Moveto_SB.setDecimals(2)
            # move.Moveto_SB.setRange(-1000, 1000)
            if move.Move_PB == None:  # No pushbutton therefore commands go off of enter in box
                # move.MoveType_CB.lineEdit().returnPressed.connect(partial(self.handle_cond_move, move.PV, move.Moveto_SB.value(), move.MoveType_CB.currentText()))
                pass
            else:
                move.Move_PB.clicked.connect(partial(self.handle_cond_move, move.PV, move.Moveto_SB, move.MoveType_CB))

    def handle_cond_move(self, PV, SB, CB):
        self.core.cond_move(PV, SB.value(), CB.currentText())

    """RANDOM"""

    def handle_lineEdit_send_SPEC(self): # sends a command straight to SPEC from a line edit on enter
        self.core.send_cmd(str(self.lineEdit_send_SPEC.text()))

    def update_saved_pos(self, saved_pos):
        self.saved_pos = saved_pos

    def select_file(self, line_edit):
        line_edit.setText(QtGui.QFileDialog.getExistingDirectory(None, 'Select a folder to save data :', os.getcwd(), QtGui.QFileDialog.ShowDirsOnly))

    def handle_tabWidget_changed(self, current):
        tabText = self.tabWidget.tabText(current)
        self.core.set_status("Tab Clicked: %s" % QtCore.QString(tabText))

    def init_label_props(self): # these are options we set for buttons and such. Most notibly tooltips (hover)
        labels = [[self.pushButton_motor_all_stop, {'hover': 'Stop Motors if they are moving, if they are not moving nothing will happen',
                                                    'text' : 'Stop All',
                                                    }],
                  [self.pushButton_motor_all_move, {'hover': 'Move All Motors to the positions set below',
                                                    'text': 'Move All',
                                                    }],
                  [self.pushButton_motor_all_checkpos, {'hover': 'Check the positions of all the motors',
                                                    'text': 'Where All',
                                                    }],

                  [self.label_scan_CWHM, {'hover': 'Position of the center of half maximum, \nDouble click to move to',
                                                    'move_motor': self.comboBox_scan_motor,
                                                    }],
                  [self.label_scan_max_y, {'hover': 'Position of the maximum, \nDouble click to move to',
                                          'move_motor': self.comboBox_scan_motor,
                                          }],
                  [self.label_scan_COM, {'hover': 'Position of the center of mass, \nDouble click to move to',
                                          'move_motor': self.comboBox_scan_motor,
                                          }],
                  [self.label_scan_curser, {'hover': 'Position of the curser, \nDouble click to move to',
                                          'move_motor': self.comboBox_scan_motor,
                                          }],

                  [self.label_cent_calc_cent_x, {'hover': 'Position of the relative calculated X position \nDouble click to move to',
                                            'move_motor_comp': (self.label_cent_motor_scan, 'Centre X')
                                            }],

                  [self.label_cent_calc_cent_y, {'hover': 'Position of the relative calculated Y position, \nDouble click to move to',
                                            'move_motor_rel': 'Centre Y'
                                            }],

                  [self.doubleSpinBox_cent_angle_pm, {'hover': 'How far omega will move from center on + and -\nReccomended to start low(2) and increase on later centerings'}],

                  [self.doubleSpinBox_cent_angle_o, {'hover': 'Where will omega start?'}],

                  [self.doubleSpinBox_cent_relmax, {'hover': 'Relative to current center where should scan start?'}],

                  [self.doubleSpinBox_cent_relmin, {'hover': 'Relative to current center where should scan stop?'}],

                  [self.doubleSpinBox_cent_steps, {'hover': 'How many steps per scan?'}],

                  [self.doubleSpinBox_cent_waittime, {'hover': 'How much time spent collecting counts at each stop?'}],

                  [self.doubleSpinBox_cent_waittime, {'hover': 'How much time spent collecting counts at each stop?'}],

                  [self.comboBox_cent_data_x, {'hover': 'Choose data to display on X Axis\nScan X is reccomended'}],

                  [self.comboBox_cent_data_y, {'hover': 'Choose data to display on Y Axis\nIntensity at Beam Stop is reccomended'}],

                  [self.doubleSpinBox_rock_startpos, {'hover': 'Start of Rocking, one endpoint'}],

                  [self.doubleSpinBox_rock_stoppos, {'hover': 'Stop of Rocking, other endpoint'}],

                  [self.doubleSpinBox_rock_steps, {'hover': 'Steps per rock'}],

                  [self.doubleSpinBox_rock_waittime, {'hover': 'Time spent at each point'}],

                  [self.doubleSpinBox_rock_time, {'hover': 'Minimum rocking time, after this no new rocks will occur, ongoing rocks do not change'}],

                  [self.checkBox_mesh_log, {'hover': 'Enable log/normal scaling, will not change data, only display'}],

                  [self.comboBox_rock_motor, {'hover': 'Choose motor to rock, angular motor is reccomended'}],

                  [self.progressBar_rock, {'hover': 'Progress until last rock'}],
        ]

        move_cbs, move_sbs = ([] for _ in range(2))
        for item in self.Motors+self.beam_cond:
            move_cbs.append(item.MoveType_CB)
            move_sbs.append(item.Moveto_SB)
        cb_dict = {'cb_items': ['Absolute', 'Relative'],
                    'hover':'Type of movement'}
        sb_dict = {'sb_range': (-1000, 1000),
                   'sb_dec': 3,
                   'hover': "Move distance(mm) \nInputs Limited by range of motor"
                   }
        for cb in move_cbs:
            labels.append([cb, cb_dict])
        for sb in move_sbs:
            labels.append([sb, sb_dict])

        plot_dict = {'hover':"This plot will dynamically update after a scan begins\n"
                             "\nLeft Shift + Left Drag  = Zoom into area "
                             "\nRight Click                   = Zoom out 1 layer"
                             "\nMiddle Click                 = Zoom out to full size"
                             "\n\nIf the graph is completely zoomed out, it will Autoscale"
                   }
        contour_dict = {'hover': "This plot will dynamically update once mesh data is made\n"
                                 "\nLeft Drag               =      Zoom into area "
                                 "\nRight Click             =      Zoom out 1 layer"
                                 "\nCtrl + RighButton   =      Zoom out to full size"
                                 "\nMiddle Click           =      Panning, hold to move area"
                                 "\n\nIf the graph is completely zoomed out, it will Autoscale"
                     }
        for plot in self.all_plots:
            if plot.contour:
                labels.append([plot, contour_dict])
            else:
                labels.append([plot, plot_dict])

        for label in labels:
            item, dict = label[0], label[1]
            for key, value in dict.iteritems():  # this would be items() in python 3
                if key == 'hover':
                    QtGui.QToolTip.setFont(QtGui.QFont('SansSerif', 10))
                    item.setToolTip(Qt.QString(value))
                elif key == 'text':
                    item.setText(value)
                elif key == 'cb_items':
                    item.clear()
                    for each in value:
                        item.addItem(each)
                elif key == 'sb_range':
                    item.setRange(*value)
                elif key == 'sb_dec':
                    item.setDecimals(value)
                elif key == 'move_motor':
                    self.clickable(item).connect(partial(self.move_clicker, value, item))
                elif key == 'move_motor_comp':
                    self.clickable(item).connect(partial(self.move_comp, value, item))
                elif key == 'move_motor_rel':
                    self.clickable(item).connect(partial(self.move_clicker, value, item, rel=True))

    def move_comp(self, motors, label):
        (scan, cent) = motors
        self.move_clicker(cent, label, rel=True)
        self.move_clicker(scan, label, rel=True, neg=True)

    def move_clicker(self, lab, label, rel=False, neg=False):  # allows us to move on a click event, setup within init_label props as well
        if isinstance(lab, basestring):
            mot = self.cent_dict.get(lab)
        else:
            try:
                mot = str(lab.currentText())
            except AttributeError:
                mot = str(lab.text())
        motor = self.core.get_motor(mot, self.Motors)
        if motor:
            try:
                if neg:
                    moveto = float(str(label.text())) * -1
                else:
                    moveto = float(str(label.text()))
                if rel == True:
                    movetype = 'Relative'
                else:
                    movetype = 'Absolute'
                self.core.move_motor(motor, moveto=moveto, movetype=movetype)
            except ValueError:
                dialog_info(msg='Motor Destination : ' + mot + " is not a valid destination")
        else:
            dialog_info(msg ='Motor : ' + mot + " could not be found")

    def clickable(self, widget):
        class Filter(QtCore.QObject):
            clicked = QtCore.pyqtSignal()
            def eventFilter(self, obj, event):
                if obj == widget:
                    if event.type() == QtCore.QEvent.MouseButtonDblClick:
                        if obj.rect().contains(event.pos()):
                            self.clicked.emit()  # The developer can opt for .emit(obj) to get the object within the slot.
                            return True
                return False
        filter = Filter(widget)
        widget.installEventFilter(filter)
        return filter.clicked

    def init_labels(self):  # linking the displays with variables, EPICS or local.
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

            VAR.SLIT_1_MOTOR_1_POS: (self.label_slit_1_motor_1_pos, '{:,.3f}', 12, True),
            VAR.SLIT_1_MOTOR_2_POS: (self.label_slit_1_motor_2_pos, '{:,.3f}', 12, True),
            VAR.SLIT_1_MOTOR_3_POS: (self.label_slit_1_motor_3_pos, '{:,.3f}', 12, True),
            VAR.SLIT_1_MOTOR_4_POS: (self.label_slit_1_motor_4_pos, '{:,.3f}', 12, True),

            VAR.SLIT_2_MOTOR_1_POS: (self.label_slit_2_motor_1_pos, '{:,.3f}', 12, True),
            VAR.SLIT_2_MOTOR_2_POS: (self.label_slit_2_motor_2_pos, '{:,.3f}', 12, True),
            VAR.SLIT_2_MOTOR_3_POS: (self.label_slit_2_motor_3_pos, '{:,.3f}', 12, True),
            VAR.SLIT_2_MOTOR_4_POS: (self.label_slit_2_motor_4_pos, '{:,.3f}', 12, True),

            VAR.APER_MOTOR_1_POS:   (self.label_aper_motor_1_pos,   '{:,.3f}', 12, True),
            VAR.APER_MOTOR_2_POS:   (self.label_aper_motor_2_pos,   '{:,.3f}', 12, True),

            VAR.DAC_MOTOR_1_POS:    (self.label_dac_motor_1_pos,    '{:,.3f}', 12, True),
            VAR.DAC_MOTOR_2_POS:    (self.label_dac_motor_2_pos,    '{:,.3f}', 12, True),

            VAR.STOP_MOTOR_1_POS:   (self.label_stop_motor_1_pos,   '{:,.3f}', 12, True),
            VAR.STOP_MOTOR_2_POS:   (self.label_stop_motor_2_pos,   '{:,.3f}', 12, True),
            
            VAR.EXTRA_MOTOR_1_POS:  (self.label_extra_motor_1_pos,  '{:,.3f}', 12, True),
            VAR.EXTRA_MOTOR_2_POS:  (self.label_extra_motor_2_pos,  '{:,.3f}', 12, True),
            VAR.EXTRA_MOTOR_3_POS:  (self.label_extra_motor_3_pos,  '{:,.3f}', 12, True),
            VAR.EXTRA_MOTOR_4_POS:  (self.label_extra_motor_4_pos,  '{:,.3f}', 12, True),
            VAR.EXTRA_MOTOR_5_POS:  (self.label_extra_motor_5_pos,  '{:,.3f}', 12, True),
            VAR.EXTRA_MOTOR_6_POS:  (self.label_extra_motor_6_pos,  '{:,.3f}', 12, True),

            VAR.MESH_CLICK_X:       (self.label_mesh_click_x,       '{:,.3f}',  9, True),
            VAR.MESH_CLICK_Y:       (self.label_mesh_click_y,       '{:,.3f}',  9, True),
            VAR.MESH_MAX_X:         (self.label_mesh_max_x,         '{:,.3f}',  9, True),
            VAR.MESH_MAX_Y:         (self.label_mesh_max_y,         '{:,.3f}',  9, True),
            VAR.MESH_COM_X:         (self.label_mesh_com_x,         '{:,.3f}',  9, True),
            VAR.MESH_COM_Y:         (self.label_mesh_com_y,         '{:,.3f}',  9, True),

            VAR.SCAN_MAX_Y_NUM:     (self.label_scan_max_y,         '{:.2f}',   12, True),
            VAR.SCAN_FWHM:          (self.label_scan_FWHM,          '{:.2f}',   12, True),
            VAR.SCAN_COM:           (self.label_scan_COM,           '{:.2f}',   12, True),
            VAR.SCAN_CWHM:          (self.label_scan_CWHM,          '{:.2f}',   12, True),
            VAR.CENT_NEG_MAXY:      (self.label_cent_maxint_m,      '{:.3f}',   10, False),
            VAR.CENT_NAU_MAXY:      (self.label_cent_maxint_o,      '{:.3f}',   10, False),
            VAR.CENT_POS_MAXY:      (self.label_cent_maxint_p,      '{:.3f}',   10, False),
            VAR.CENT_NEG_COM:       (self.label_cent_com_m,         '{:.3f}',   10, False),
            VAR.CENT_NAU_COM:       (self.label_cent_com_o,         '{:.3f}',   10, False),
            VAR.CENT_POS_COM:       (self.label_cent_com_p,         '{:.3f}',   10, False),
            VAR.CENT_NEG_CWHM:      (self.label_cent_cwhm_m,        '{:.3f}',   10, False),
            VAR.CENT_NAU_CWHM:      (self.label_cent_cwhm_o,        '{:.3f}',   10, False),
            VAR.CENT_POS_CWHM:      (self.label_cent_cwhm_p,        '{:.3f}',   10, False),
            VAR.VERT_BAR_NEG_X:     (self.label_cent_curs_m,        '{:.3f}',   10, False),
            VAR.VERT_BAR_NAU_X:     (self.label_cent_curs_o,        '{:.3f}',   10, False),
            VAR.VERT_BAR_POS_X:     (self.label_cent_curs_p,        '{:.3f}',   10, False),
            VAR.VERT_BAR_SCAN_X:    (self.label_scan_curser,        '{:.3f}',   10, False),
            VAR.CENT_CENTERED_X:    (self.label_cent_calc_cent_x,   '{:.3f}',   12, True),
            VAR.CENT_CENTERED_Y:    (self.label_cent_calc_cent_y,   '{:.3f}',   12, True),

            VAR.CENT_AMGLE_MOTOR:   (self.label_cent_motor_angle,   '{:s}',     12, True),
            VAR.CENT_SCAN_MOTOR:    (self.label_cent_motor_scan,    '{:s}',     12, True),


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
        self.add_label(label_map)

    def add_label(self, label_map, double=False): # double means we will disconnect any old
        css_normal= "QLabel { background-color : %s; color : %s; }" % \
                  (CSS_COLOUR.GROUP_BOX, CSS_COLOUR.BLUE)
        for pv_name, data in label_map.iteritems():  # This allows us to add labels to our label_map so we can update motor pos
            # self.monitor.add(pv_name)
            widget = data[0]
            font = QtGui.QFont('Courier', data[2])
            widget.setFont(font)
            widget.setText(EMPTY_STRING)


            if not double:  # No drag text for labels which are attached to two. Dont know how to switch drag text
                self.set_drag_text(widget, pv_name)

            try:
                if data[3]:
                    font.setWeight(QtGui.QFont.Bold)
            except:
                pass

            if not double:  # No drag text for labels which are attached to two. Dont know how to switch drag text
                self.formatter.add(pv_name, widget, format=data[1],
                    css_normal=css_normal,
                    css_lost=CSS_LABEL_PV_LOST)
            else:
                self.formatter.replace(pv_name, widget, format=data[1],
                                   css_normal=css_normal,
                                   css_lost=CSS_LABEL_PV_LOST)

            self.monitor.connect(pv_name, self.handle_label)
            if double:
                self.monitor.start()

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
        self.save_rock_props()
        self.save_cent_props()
        self.save_motors(self.Motors)

        self.scan_plot_id.terminate()
        self.cent_plot_id.terminate()
        self.cent_plot_id_1.terminate()
        self.cent_plot_id_2.terminate()
        self.cent_plot_id_3.terminate()

        for plot in self.all_plots:
            try:
                plot.timer.stop()
            except AttributeError:
                print repr(plot)," did not have a timer?"

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
