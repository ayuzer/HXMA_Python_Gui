# System imports
import simplejson
import os
import math
import time

# Library imports
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

# App imports
import settings
from windows import GROUP_BOX_STYLE

from utils.gui import UiMixin
from utils.gui import dialog_yes_no
from utils.gui import dialog_error
from utils.gui import dialog_info
from utils.gui import decorator_dialog_error

from utils import Constant
from utils import clean_float

from materials import MaterialsManager
from monitor import KEY as MONITOR_KEY
from filter_pvs import FILTER_ID as FID
from filter_pvs import FILTER_BM as FBM
from filter_pvs import FILTER_SIM as FSM
from filter_pvs import BEAMLINE
from filter_pvs import WBT_STATUS
from filter_pvs import VAR
from filter_pvs import RING_PV
from filter_pvs import PV
from filter_pvs import SIM_PV_PREFIX

from spectrum import Spectrum
from graph import PlotterLog

from worker import SimulatedFilter
from worker import FilterManager, FILTER_MANAGER_SETTINGS_KEY
from worker import ID_MONO_STATUS

SETTINGS_FILE_NAME = ".BMIT_Spectrum_App/settings.json"

PLOT_TITLE = "Central Brilliance vs. Photon Energy"
PLOT_LABEL_X = "Photon Energy (KeV)"
PLOT_LABEL_Y = "Central Brilliance (Photons/s/mr^2/0.1%bw)"

class ExceptionBreak(Exception):
    pass

class ExceptionFound(Exception):
    pass

class ID_MONO_RADIO(Constant):
    CT     = 0
    KES    = 1
    ACTUAL = 2

class WBT_RADIO(Constant):
    OUT     = 0
    IN      = 1
    ACTUAL  = 2

class KEY(Constant):
    BEAMLINE    = 'beamline'
    PVS         = 'pvs'
    CHECKBOX    = 'checkbox'
    FILTER      = 'filter'
    NAME        = 'name'
    WBT         = 'wbt'

class SETTINGS(Constant):
    KEY                         = 'main_window_settings'
    SELECTED_MATERIAL           = 'selected_material'
    RING_CURRENT_USE_ACTUAL     = 'ring_current_use_actual'
    RING_CURRENT_THEORETICAL    = 'ring_current_theoretical'
    OTHER_FILTERS               = 'other_filters'
    MASS_ATTEN_THICKNESS        = 'mass_atten_thickness'
    WIGGLER_FIELD_USE_ACTUAL    = 'wiggler_field_use_actual'
    WIGGLER_FIELD_THEORETICAL   = 'wiggler_field_theoretical'
    PLOT_CUMULATIVE_ID          = 'plot_cumulative_id'
    PLOT_CUMULATIVE_BM          = 'plot_cumulative_bm'
    WBT_RADIO                   = 'wbt_radio'
    ID_MONO_RADIO               = 'id_mono_radio'

class COMBO_BOX_MAP_INDEX(Constant):
    MATERIAL_PV     = 0
    THICKNESS_PV    = 1
    ACTUAL          = 2

class MainWindow(QtGui.QMainWindow, UiMixin):
    """
    This thing has grown 'organically' and there is a ton of stuff in here
    that is not GUI related.
    """
    SIGNAL_ERROR_DIALOG = QtCore.pyqtSignal(unicode)

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        # Update counters used for debugging logs
        self.update_counter_id = 0
        self.update_counter_bm = 0

        self.bm_spectrum_cache_params = {}
        self.id_spectrum_cache_params = {}
        self.init_filter_pv_list = []
        self.timer_expired = False
        self.skip_compute = False

        # Record the update times so that updates can be forced if a long time
        # elapses.  This fixes the case where the values are very low and
        # updates never occurred... which led to a inaccurate view of the
        # spectrum
        self.last_actual_current_update_time = 0
        self.last_actual_field_update_time = 0

        super(MainWindow, self).__init__(*args, **kwargs)

        # Set up the user interface from Designer.
        self.load_ui("windows/main_window.ui")

        # Hide the specified Tabs
        for title in settings.HIDE_TABS:
            self.hide_tab(self.tabWidget, title)

        self.SIGNAL_ERROR_DIALOG.connect(self.handle_error_dialog_signal)
        self.setWindowTitle(settings.APP_NAME)
        self.init_groupBox_style()
        self.init_filter_grids()
        self.load_settings()
        self.init_default_settings()
        self.init_tab_debug_id_mono()

        # Set up the Data Visualization component
        self.plot_id = PlotterLog()

        self.verticalLayout_plot_container_id.addWidget(self.plot_id)
        self.plot_id.set_title(PLOT_TITLE)
        self.plot_id.set_axis_label_x(PLOT_LABEL_X)
        self.plot_id.set_axis_label_y(PLOT_LABEL_Y)
        self.plot_id.set_mouse_position_callback(self.callback_mouse_pos_id)
        self.plot_id.set_legend()

        self.plot_bm = PlotterLog()
        self.verticalLayout_plot_container_bm.addWidget(self.plot_bm)
        self.plot_bm.set_title(PLOT_TITLE)
        self.plot_bm.set_axis_label_x(PLOT_LABEL_X)
        self.plot_bm.set_axis_label_y(PLOT_LABEL_Y)
        self.plot_bm.set_mouse_position_callback(self.callback_mouse_pos_bm)
        self.plot_bm.set_legend()

        self.plot_test = PlotterLog()
        self.verticalLayout_plot_container_test.addWidget(self.plot_test)
        self.plot_test.set_title("Test Plot")
        self.plot_test.set_axis_label_x("X")
        self.plot_test.set_axis_label_y("Y")
        self.plot_test.set_mouse_position_callback(self.callback_mouse_pos_test)

        self.plot_atten = PlotterLog()
        self.verticalLayout_plot_container_coef.addWidget(self.plot_atten)
        self.plot_atten.set_mouse_position_callback(self.callback_mouse_pos_atten)

        self.mat_mgr = MaterialsManager(error_callback=self.error)

        self.spectrum = Spectrum(self.mat_mgr)
        self.spectrum.set_error_callback(self.error)

        # Make a logarithmic sequence of Photon Energies (KeV) for plotting
        self.kevs = self.spectrum.make_log_sequence(1, 1000, 1500)

        # This has to happen *before* the comboBox initialization
        self.simulated_filter_map = self.init_simulated_filters()

        # Defines which PVs compose the options for each comboBox
        self.comboBox_map = self.init_comboBox_map()

        self.debug_label_map = {}

        self.init_comboBox_materials()

        if not 'ID PVs' in settings.HIDE_TABS:
            self.init_debug_tab(FID, self.gridLayout_debug_id, cols=3)

        if not 'BM PVs' in settings.HIDE_TABS:
            self.init_debug_tab(FBM, self.gridLayout_debug_bm, cols=3)

        self.get_position()

        self.init_comboBoxes_filter()

        self.plot_cumulative_widget_map = {
            VAR.PLOT_CUMULATIVE_ID : self.checkBox_id_plot_cumulative,
            VAR.PLOT_CUMULATIVE_BM : self.checkBox_bm_plot_cumulative
        }

        self.plot_cumulative_settings_map = {
            VAR.PLOT_CUMULATIVE_ID : SETTINGS.PLOT_CUMULATIVE_ID,
            VAR.PLOT_CUMULATIVE_BM : SETTINGS.PLOT_CUMULATIVE_BM
        }

        for name, widget in self.plot_cumulative_widget_map.iteritems():
            widget.stateChanged.connect(
                lambda arg, name=name : self.handle_checkBox_plot_cumulative(name))

        # Perhaps should use a table to facilitate initializing these vars/settings
        val = self.get_setting(SETTINGS.PLOT_CUMULATIVE_ID, default=QtCore.Qt.Checked)
        self.monitor.add(VAR.PLOT_CUMULATIVE_ID, val)
        self.monitor.connect(VAR.PLOT_CUMULATIVE_ID, self.handle_var_plot_cumulative)

        val = self.get_setting(SETTINGS.PLOT_CUMULATIVE_BM, default=QtCore.Qt.Checked)
        self.monitor.add(VAR.PLOT_CUMULATIVE_BM, val)
        self.monitor.connect(VAR.PLOT_CUMULATIVE_BM, self.handle_var_plot_cumulative)

        self.lock_scale_widget_map = {
            self.checkBox_id_lock : (self.plot_id, self.horizontalSlider_id),
            self.checkBox_bm_lock : (self.plot_bm, self.horizontalSlider_bm)
        }
        for widget in self.lock_scale_widget_map.iterkeys():
            widget.stateChanged.connect(
                lambda arg, widget=widget : self.handle_checkBox_lock(widget))

        val = self.get_setting(SETTINGS.WBT_RADIO, default=WBT_RADIO.ACTUAL)
        self.monitor.add(VAR.WBT_RADIO, val)
        self.monitor.connect(VAR.WBT_RADIO, self.handle_var_wbt_radio)

        val = self.get_setting(SETTINGS.ID_MONO_RADIO, default=ID_MONO_RADIO.ACTUAL)
        self.monitor.add(VAR.ID_MONO_RADIO, val)
        self.monitor.connect(VAR.ID_MONO_RADIO, self.handle_var_id_mono_radio)

        val = self.get_setting(SETTINGS.RING_CURRENT_USE_ACTUAL, default=True)
        self.monitor.add(VAR.RING_CURRENT_USE_ACTUAL, val)
        self.monitor.connect(VAR.RING_CURRENT_USE_ACTUAL,
            self.handle_ring_current_use_actual_updated)

        val = self.get_setting(SETTINGS.WIGGLER_FIELD_USE_ACTUAL, default=True)
        self.monitor.add(VAR.WIGGLER_FIELD_USE_ACTUAL, val)
        self.monitor.connect(VAR.WIGGLER_FIELD_USE_ACTUAL,
            self.handle_wiggler_field_use_actual_updated)

        # Thickness for Mass Attenuation Tab
        val = self.get_setting(SETTINGS.MASS_ATTEN_THICKNESS, default=1.0)
        self.monitor.add(VAR.MASS_ATTEN_THICKNESS, val)
        self.monitor.connect(VAR.MASS_ATTEN_THICKNESS,
            self.handle_mass_atten_thickness)

        self.lineEdit_mass_atten_thickness.editingFinished.connect(
            self.handle_mass_atten_thickness_edit)

        # This is the actual PV that reports that actual WBT status
        self.monitor.add(FID.WBT_ACTUAL)
        self.monitor.connect(FID.WBT_ACTUAL, self.handle_pv_wbt_actual)

        self.monitor.add(VAR.WBT_STATUS, WBT_STATUS.UNKNOWN)
        self.monitor.connect(VAR.WBT_STATUS, self.handle_var_wbt_status)

        # Call the actual WBT_STATUS handler with status unknown.  This should
        # hide the appropriate filter group boxes so that there is not
        # a 'flicker' on launch
        self.handle_var_wbt_status(VAR.WBT_STATUS)
        self.monitor.add(VAR.ID_MONO_ACTUAL, ID_MONO_STATUS.UNKNOWN)

        # Init wiggler field
        val = self.get_setting(SETTINGS.WIGGLER_FIELD_THEORETICAL, default = 4.3)
        self.monitor.add(VAR.WIGGLER_FIELD_THEORETICAL, val)
        self.monitor.connect(VAR.WIGGLER_FIELD_THEORETICAL,
            self.handle_wiggler_field_theoretical_changed)

        self.monitor.add(VAR.WIGGLER_FIELD_ACTUAL, 0.0)
        self.monitor.add(VAR.WIGGLER_FIELD_ACTIVE, 0.0)

        self.monitor.connect(VAR.WIGGLER_FIELD_ACTUAL,
            self.handle_wiggler_field_actual_changed)

        self.monitor.connect(VAR.WIGGLER_FIELD_ACTIVE,
            self.handle_wiggler_field_active_changed)

        # Init ring current
        val = self.get_setting(SETTINGS.RING_CURRENT_THEORETICAL, default=250.0)
        self.monitor.add(VAR.RING_CURRENT_THEORETICAL, val)
        self.monitor.connect(VAR.RING_CURRENT_THEORETICAL,
            self.handle_ring_current_theoretical_changed)

        self.monitor.add(VAR.RING_CURRENT_ACTUAL, 0.0)
        self.monitor.add(VAR.RING_CURRENT_ACTIVE, 0.0)

        self.monitor.connect(VAR.RING_CURRENT_ACTUAL,
            self.handle_ring_current_actual_changed)

        self.monitor.connect(VAR.RING_CURRENT_ACTIVE,
            self.handle_ring_current_active_changed)

        self.monitor.add(VAR.OTHER_FILTERS, {})
        self.monitor.connect(VAR.OTHER_FILTERS,
            self.handle_var_other_filters_updated)

        self.monitor.add(VAR.BM_PLOT_MOUSE_POS, (0, 0))
        self.monitor.connect(VAR.BM_PLOT_MOUSE_POS,
            self.handle_mouse_pos_bm)

        self.monitor.add(VAR.ID_PLOT_MOUSE_POS, (0, 0))
        self.monitor.connect(VAR.ID_PLOT_MOUSE_POS,
            self.handle_mouse_pos_id)

        self.monitor.add(VAR.TEST_PLOT_MOUSE_POS, (0, 0))
        self.monitor.connect(VAR.TEST_PLOT_MOUSE_POS,
            self.handle_mouse_pos_test)

        self.monitor.add(VAR.ATTEN_PLOT_MOUSE_POS, (0, 0))
        self.monitor.connect(VAR.ATTEN_PLOT_MOUSE_POS,
            self.handle_mouse_pos_atten)

        # Connect all filter combo boxes to a handler
        for comboBox, value in self.comboBox_map.iteritems():
            name = value.get(KEY.NAME)
            comboBox.currentIndexChanged.connect(
                lambda arg, name=name : self.handle_comboBox_filter(name))

        # PV handlers should really be in a worker module, not the window.
        self.monitor.add(RING_PV.CURRENT)
        self.monitor.add(RING_PV.ENERGY)
        self.monitor.add(RING_PV.WIGGLER_FIELD)
        self.monitor.add(RING_PV.SYSTEM_TIME)

        self.monitor.connect(RING_PV.CURRENT, self.handle_pv_ring_current)
        self.monitor.connect(RING_PV.ENERGY, self.handle_pv_ring_energy)
        self.monitor.connect(RING_PV.WIGGLER_FIELD, self.handle_pv_wiggler_field)
        self.monitor.connect(RING_PV.SYSTEM_TIME, self.handle_pv_system_time)

        self.pushButton_id_current.clicked.connect(self.handle_pushButton_id_current)
        self.pushButton_bm_current.clicked.connect(self.handle_pushButton_bm_current)

        self.pushButton_monitor_list.clicked.connect(
            self.handle_pushButton_monitor_list_clicked)

        self.pushButton_bessel.clicked.connect(
            self.handle_pushButton_bessel_clicked)

        self.pushButton_spectrum_bm.clicked.connect(
            self.handle_pushButton_spectrum_bm_clicked)

        self.pushButton_bessel_2.clicked.connect(
            self.handle_pushButton_bessel_2_clicked)

        self.pushButton_spectrum_id.clicked.connect(
            self.handle_pushButton_spectrum_id_clicked)

        self.pushButton_kapton.clicked.connect(
            self.handle_pushButton_kapton)

        self.pushButton_water.clicked.connect(
            self.handle_pushButton_water)

        self.pushButton_pvc.clicked.connect(
            self.handle_pushButton_pvc)

        self.pushButton_test.clicked.connect(
            self.handle_pushButton_test)

        self.radioButton_atten.setChecked(True)

        self.radioButton_atten.clicked.connect(
           self.handle_radioButton_element)

        self.radioButton_raw.clicked.connect(
           self.handle_radioButton_element)

        self.wbt_radioButton_map = {
            WBT_RADIO.IN     : self.radioButton_wbt_in,
            WBT_RADIO.OUT    : self.radioButton_wbt_out,
            WBT_RADIO.ACTUAL : self.radioButton_wbt_actual
        }

        for state, widget in self.wbt_radioButton_map.iteritems():
            widget.clicked.connect(
                lambda arg, state=state : self.handle_radioButton_wbt(state=state))

        self.id_mono_radioButton_map = {
            ID_MONO_RADIO.CT     : self.radioButton_id_mono_ct,
            ID_MONO_RADIO.KES    : self.radioButton_id_mono_kes,
            ID_MONO_RADIO.ACTUAL : self.radioButton_id_mono_actual
        }

        for state, widget in self.id_mono_radioButton_map.iteritems():
            widget.clicked.connect(
                lambda arg, state=state : self.handle_radioButton_id_mono(state=state))

        self.wiggler_field_radioButton_map = {
            "it" : self.radioButton_id_wiggler_field_theoretical,
            "ia" : self.radioButton_id_wiggler_field_actual,
            "tt" : self.radioButton_test_wiggler_field_theoretical,
            "ta" : self.radioButton_test_wiggler_field_actual,
        }

        self.wiggler_field_radioButtons_theoretical_names = ['it', 'tt']
        self.wiggler_field_radioButtons_actual_names = ['ia', 'ta']

        for name, widget in self.wiggler_field_radioButton_map.iteritems():
            widget.clicked.connect(
                lambda arg, name=name : self.handle_radioButton_wiggler_field(name=name))

        self.ring_current_radioButton_map = {
            "tt" : self.radioButton_test_ring_current_theoretical,
            "ta" : self.radioButton_test_ring_current_actual,
            "bt" : self.radioButton_bm_ring_current_theoretical,
            "ba" : self.radioButton_bm_ring_current_actual,
            "it" : self.radioButton_id_ring_current_theoretical,
            "ia" : self.radioButton_id_ring_current_actual,
        }

        self.ring_current_radioButtons_theoretical_names = ['tt', 'bt', 'it']
        self.ring_current_radioButtons_actual_names = ['ta', 'ba', 'ia']

        for name, widget in self.ring_current_radioButton_map.iteritems():
            widget.clicked.connect(
                lambda arg, name=name : self.handle_radioButton_ring_current(name=name))

        self.line_edit_map = {
            'ring_current_test' :
                (self.lineEdit_test_ring_current_theoretical,
                 self.handle_ring_current_edited),
            'ring_current_bm'   :
                (self.lineEdit_bm_ring_current_theoretical,
                 self.handle_ring_current_edited),
            'ring_current_id'   :
                (self.lineEdit_id_ring_current_theoretical,
                 self.handle_ring_current_edited),
            'wiggler_field_id'     :
                (self.lineEdit_wiggler_field_theoretical,
                 self.handle_wiggler_field_edited),
            'wiggler_field_test'     :
                (self.lineEdit_test_wiggler_field_theoretical,
                 self.handle_wiggler_field_edited)
        }

        for name, item in self.line_edit_map.iteritems():
            widget = item[0]
            widget.editingFinished.connect(
                lambda name=name : self.handle_line_editing_finished(name))

        self.init_other_filters()

        self.filter_manager = FilterManager(monitor=self.monitor, mat_mgr=self.mat_mgr)
        self.filter_manager.set_error_callback(self.error)
        self.filter_manager.set_settings(self.settings)

        self.monitor.add(VAR.ID_MONO_ENERGY_KES, None)
        self.monitor.add(VAR.ID_MONO_ENERGY_CT, None)
        self.monitor.add(VAR.ID_MONO_ENERGY, None)

        self.monitor.connect(VAR.ID_MONO_RADIO,  self.handle_var_mono)
        self.monitor.connect(VAR.ID_MONO_ACTUAL, self.handle_var_id_mono_actual)
        self.monitor.connect(VAR.ID_MONO_ACTUAL, self.handle_var_mono)
        self.monitor.connect(VAR.ID_MONO_USE,    self.handle_var_mono_use)
        self.monitor.connect(VAR.ID_MONO_ENERGY, self.handle_var_mono_energy)

        self.handle_var_mono_use(VAR.ID_MONO_USE)

        # This dictionary maps the ID Mono thickness vars to IDs
        self.id_mono_thinkness_map = {
            VAR.ID_MONO_CT_THICKNESS_C1 : 'ID-W9-T',
            VAR.ID_MONO_CT_THICKNESS_C2 : 'ID-W10-T',
            VAR.ID_MONO_KES_THICKNESS   : 'ID-W11-T'
        }

        self.monitor.connect(VAR.ID_MONO_CT_THICKNESS_C1, self.handle_var_id_mono_thickness)
        self.monitor.connect(VAR.ID_MONO_CT_THICKNESS_C2, self.handle_var_id_mono_thickness)
        self.monitor.connect(VAR.ID_MONO_KES_THICKNESS,   self.handle_var_id_mono_thickness)

        # self.pushButton_apply_1.clicked.connect(
        #     lambda : self.handle_pushButton_apply(self.comboBoxes_bm))

        self.tabWidget.currentChanged.connect(self.handle_tab_index_changed)
        self.timer = QtCore.QTimer()
        self.timer.singleShot(2000, self.handle_timer_timeout)
        # self._timer.start(1000)

        self.mono_energy_timer = QtCore.QTimer()
        self.mono_energy_timer.setInterval(2000)
        self.mono_energy_timer.timeout.connect(self.handle_timer_mono_energy)
        self.mono_energy_timer.start(2000)

        self.min_factor_id = self.horizontalSlider_id.maximum()
        self.horizontalSlider_id.setValue(self.min_factor_id)
        self.prev_spectrum_id = None

        self.horizontalSlider_id.valueChanged.connect(
            self.handle_horizontalSlider)

        self.min_factor_bm = self.horizontalSlider_bm.maximum()
        self.horizontalSlider_bm.setValue(self.min_factor_bm)
        self.prev_spectrum_bm = None

        self.horizontalSlider_bm.valueChanged.connect(
            self.handle_horizontalSlider)

        self.init_tooltip_comboBox()

        self.filter_order = self.init_filter_order()

        self.actionAbout.triggered.connect(self.handle_actionAbout)
        self.actionMonitor_List.triggered.connect(self.handle_actionMonitor_List)

        self.pushButton_id_apply.setEnabled(False)
        self.pushButton_bm_apply.setEnabled(False)

        self.id_mono_energy_label_map = {
            VAR.ID_MONO_ENERGY_KES : (self.radioButton_id_mono_kes, 'KES'),
            VAR.ID_MONO_ENERGY_CT  : (self.radioButton_id_mono_ct, 'CT' )
        }

        self.monitor.connect(VAR.ID_MONO_ENERGY_KES, self.handle_var_id_mono_energy)
        self.monitor.connect(VAR.ID_MONO_ENERGY_CT, self.handle_var_id_mono_energy)

        self.monitor.start()

        self.get_position()
        self.position_set = False

    def init_tab_debug_id_mono(self):

        if 'ID Mono Debugging' in settings.HIDE_TABS:
            print "Skipping ID Mono Debugging Tab"
            return

        label_dict = {
            self.label_dbg_bragg_pv_name_c1         : PV.ID_MONO_CT1_BRAGG,
            self.label_dbg_bragg_pv_name_c2         : PV.ID_MONO_CT2_BRAGG,
            self.label_dbg_lattice_pv_name_c1       : PV.ID_MONO_CT1_LATTICE,
            self.label_dbg_lattice_pv_name_c2       : PV.ID_MONO_CT2_LATTICE,
            self.label_dbg_energy_pv_name_ct        : PV.ID_MONO_ENERGY_CT,
            self.label_dbg_energy_pv_name_kes       : PV.ID_MONO_ENERGY_KES,
            self.label_dbg_mono_in_pv_name_ct       : PV.ID_MONO_IN_CT,
            self.label_dbg_mono_in_pv_name_kes      : PV.ID_MONO_IN_KES,
            self.label_dbg_kes_pv_name_total_offset : PV.ID_MONO_KES_TOTAL_OFFSET,
            self.label_dbg_kes_pv_name_lattice_angle: PV.ID_MONO_KES_LATTICE_ANGLE,
            self.label_dbg_kes_pv_name_stage_angle  : PV.ID_MONO_KES_STAGE_ANGLE,
            self.label_dbg_kes_pv_name_bragg_angle  : PV.ID_MONO_KES_BRAGG_ANGLE
        }

        for widget, pv in label_dict.iteritems():
            widget.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
            widget.setText(QtCore.QString(pv))

        self.debug_id_mono_label_map = {
            PV.ID_MONO_CT1_BRAGG        : self.label_dbg_bragg_val_c1,
            PV.ID_MONO_CT2_BRAGG        : self.label_dbg_bragg_val_c2,
            PV.ID_MONO_CT1_LATTICE      : self.label_dbg_lattice_val_c1,
            PV.ID_MONO_CT2_LATTICE      : self.label_dbg_lattice_val_c2,
            VAR.ID_MONO_CT_THICKNESS_C1 : self.label_dbg_thickness_c1,
            VAR.ID_MONO_CT_THICKNESS_C2 : self.label_dbg_thickness_c2,
            VAR.ID_MONO_KES_THICKNESS   : self.label_dbg_kes_thickness,
            PV.ID_MONO_ENERGY_CT        : self.label_dbg_energy_ct,
            PV.ID_MONO_ENERGY_KES       : self.label_dbg_energy_kes,
            PV.ID_MONO_IN_CT            : self.label_dbg_mono_in_val_ct,
            PV.ID_MONO_IN_KES           : self.label_dbg_mono_in_val_kes,
            PV.ID_MONO_KES_TOTAL_OFFSET : self.label_dbg_kes_val_total_offset,
            PV.ID_MONO_KES_LATTICE_ANGLE: self.label_dbg_kes_val_lattice_angle,
            PV.ID_MONO_KES_STAGE_ANGLE  : self.label_dbg_kes_val_stage_angle,
            PV.ID_MONO_KES_BRAGG_ANGLE  : self.label_dbg_kes_val_bragg_angle,
        }

        # Connect up the PVs to the display labels
        for pv, widget in self.debug_id_mono_label_map.iteritems():
            self.monitor.connect(pv, self.handle_dbg_mono_label)
            widget.setToolTip(QtCore.QString(pv))

    def handle_checkBox_lock(self, widget):
        state = widget.checkState()

        # Get the plotter & slider corresponding to this lock widget
        widgets = self.lock_scale_widget_map.get(widget)

        plotter = widgets[0]
        slider = widgets[1]

        if state == QtCore.Qt.Checked:
            plotter.lock(True)
            slider.setEnabled(False)
        else:
            plotter.lock(False)
            self.compute_spectrum(force=True)
            slider.setEnabled(True)

    def handle_var_id_mono_thickness(self, pv_name):
        """
        Handle ID mono thickness has change.  Get value from internal PV
        """
        value = float(self.monitor.get_value(pv_name, 0.0))
        value = '%f' % value
        line_edit_id = self.id_mono_thinkness_map.get(pv_name)

        current = self.monitor.get_value(VAR.OTHER_FILTERS)
        current = current.get(line_edit_id, '')

        try:
            success = False
            self.filter_manager.update_other_filters(line_edit_id, value)
            success = True
        finally:
            if not success:
                # restore old value
                widget = self.other_filter_map.get(line_edit_id)
                widget.setText(QtCore.QString(current))

    def handle_dbg_mono_label(self, pv_name):
        value = self.monitor.get_value(pv_name)
        display = "%.5f" % float(value)
        display = clean_float(display)
        widget = self.debug_id_mono_label_map.get(pv_name)
        widget.setText(QtCore.QString(display))

    def handle_var_mono_use(self, pv_name):
        value = self.monitor.get_value(pv_name)

        groupBoxes = [
            self.groupBox_id_mono_ct,   # 0
            self.groupBox_id_mono_kes,  # 1
        ]

        if value == ID_MONO_STATUS.CT_IN:
            in_list = [0]
        elif value == ID_MONO_STATUS.KES_IN:
            in_list = [1]
        elif value == ID_MONO_STATUS.BOTH:
            in_list = [0, 1]
        else:
            in_list = []

        # Hiding all mono groupBoxes then subsequently unhiding
        # a subset prevents a "screen flash" from happening
        for i in [0, 1]:
            groupBox = groupBoxes[i]
            groupBox.setHidden(True)

        # All now hidden... un-hide desired ones
        for i in [0, 1]:
            if i in in_list:
                groupBox = groupBoxes[i]
                groupBox.setHidden(False)

        self.update_mono_energy()

    def handle_var_mono_energy(self, pv_name):
        self.compute_spectrum()

    def handle_var_mono(self, pv_name):
        radio_value = self.monitor.get_value(VAR.ID_MONO_RADIO)

        use_value = ID_MONO_STATUS.UNKNOWN
        if radio_value == ID_MONO_RADIO.CT:
            use_value = ID_MONO_STATUS.CT_IN
        elif radio_value == ID_MONO_RADIO.KES:
            use_value = ID_MONO_STATUS.KES_IN
        else:
            use_value = self.monitor.get_value(VAR.ID_MONO_ACTUAL)

        self.monitor.update(VAR.ID_MONO_USE, use_value)

    def handle_pushButton_bm_current(self):

        self.skip_compute = True

        self.reset_combo_boxes(BEAMLINE.BM)
        self.reset_window_filters(BEAMLINE.BM)

        self.skip_compute = False
        self.compute_spectrum()

    def handle_pushButton_id_current(self):

        self.skip_compute = True

        # First, set WBT to actual state
        self.monitor.update(VAR.WBT_RADIO, WBT_RADIO.ACTUAL)
        self.monitor.update(VAR.ID_MONO_RADIO, ID_MONO_RADIO.ACTUAL)

        self.reset_combo_boxes(BEAMLINE.ID)
        self.reset_window_filters(BEAMLINE.ID)

        self.skip_compute = False
        self.compute_spectrum()

    def reset_window_filters(self, beamline):

        for key, checkBox in self.other_filter_check_box_map.iteritems():
            parts = key.split('-')
            if parts[0] != beamline:
                continue

            if parts[1].startswith('W'):
                checkBox.setChecked(True)

            elif parts[1].startswith('0'):

                if self.reset_other_filter_special_case(key):
                    checkBox.setChecked(True)
                else:
                    checkBox.setChecked(False)

    def reset_other_filter_special_case(self, key):
        """
        This 'special case' returns True if the first 'other filter' is 'Air'
        """
        special = ['ID-01-C', 'BM-01-C']

        if key in special:
            key = key.replace('C', 'M')
            comboBox = self.other_filter_map.get(key)
            if unicode(comboBox.currentText()) == 'Air':
                return True

    def reset_combo_boxes(self, beamline):
        """
        Must reset all the combo boxes to the "actual" beam conditions.
        """
        for comboBox, value in self.comboBox_map.iteritems():
            if not value.get(KEY.BEAMLINE) == beamline:
                continue

            check_box = value.get(KEY.CHECKBOX)
            check_box.setCheckState(QtCore.Qt.Checked)

            self.reset_combo_box_selection(comboBox, value)

    def reset_combo_box_selection(self, comboBox, value):
        """
        This method sets the comboBox selection back to the item
        that is actually in the beam
        """
        pvs = value.get(KEY.PVS)
        # print "these are the combo box PVs", pvs

        in_beam_pv = None
        for pv in pvs:
            if pv[COMBO_BOX_MAP_INDEX.ACTUAL] == True:
                in_beam_pv = pv[COMBO_BOX_MAP_INDEX.MATERIAL_PV]
                break

        if not in_beam_pv:
            raise ValueError("Unable to locate in_beam_pv")

        # The material PV is used to identify comboBox items
        material_pv = pv[COMBO_BOX_MAP_INDEX.MATERIAL_PV]
        user_data = QtCore.QVariant(QtCore.QString(material_pv))
        index = comboBox.findData(user_data)
        comboBox.setCurrentIndex(index)

    def handle_pv_wbt_actual(self, name):

        value = self.monitor.get_value(name)
        if value == 1:
            display = "In"
        else:
            display = "Out"

        self.label_id_wbt_actual.setText(QtCore.QString(display))
        self.wbt_update()

    def handle_var_id_mono_actual(self, name):
        value = self.monitor.get_value(name)

        display = 'Unknown'
        if value == ID_MONO_STATUS.CT_IN:
            display = 'CT'
        elif value == ID_MONO_STATUS.KES_IN:
            display = 'KES'
        elif value == ID_MONO_STATUS.BOTH:
            display = 'CT & KES'
        elif value == ID_MONO_STATUS.NO_MONO:
            display = 'No Mono'

        self.label_id_mono_actual.setText(QtCore.QString(display))

    def handle_var_wbt_status(self, name):

        value = self.monitor.get_value(name)

        groupBoxes = [
            self.groupBox_id_window_4,  # 0
            self.groupBox_id_window_5,  # 1
            self.groupBox_id_window_6,  # 2
            self.groupBox_id_window_7,  # 3
            self.groupBox_poe_3         # 4
        ]

        if value == WBT_STATUS.IN:
            in_list = [2, 3, 4]
        elif value == WBT_STATUS.OUT:
            in_list = [0, 1]
        else:
            in_list = []

        # Hide all the widgets first
        for i in [0, 1, 2, 3, 4]:
            groupBox = groupBoxes[i]
            groupBox.setHidden(True)

        for i in [0, 1, 2, 3, 4]:
            if i in in_list:
                groupBox = groupBoxes[i]
                groupBox.setHidden(False)

        self.compute_spectrum()

    def handle_var_id_mono_radio(self, name):

        value = self.monitor.get_value(name)
        self.save_setting(SETTINGS.ID_MONO_RADIO, value)

        # Need to set the buttons so that saved setting gets applied
        if value == ID_MONO_RADIO.CT:
            self.radioButton_id_mono_ct.setChecked(True)
        elif value == ID_MONO_RADIO.KES:
            self.radioButton_id_mono_kes.setChecked(True)
        else:
            self.radioButton_id_mono_actual.setChecked(True)

    def handle_var_wbt_radio(self, name):

        value = self.monitor.get_value(name)
        self.save_setting(SETTINGS.WBT_RADIO, value)

        # Need to set the buttons so that saved setting gets applied
        if value == WBT_RADIO.IN:
            self.radioButton_wbt_in.setChecked(True)
        elif value == WBT_RADIO.OUT:
            self.radioButton_wbt_out.setChecked(True)
        else:
            self.radioButton_wbt_actual.setChecked(True)

        self.wbt_update()

    def wbt_update(self):

        value = self.monitor.get_value(VAR.WBT_RADIO)
        if value == WBT_RADIO.IN:
            status = WBT_STATUS.IN
        elif value == WBT_RADIO.OUT:
            status = WBT_STATUS.OUT
        else:
            status = self.monitor.get_value(FID.WBT_ACTUAL)

        self.monitor.update(VAR.WBT_STATUS, status)

    def handle_radioButton_wbt(self, state):
        self.monitor.update(VAR.WBT_RADIO, state)

    def handle_radioButton_id_mono(self, state):
        self.monitor.update(VAR.ID_MONO_RADIO, state)

    def handle_var_plot_cumulative(self, name):

        widget = self.plot_cumulative_widget_map.get(name)
        state = self.monitor.get_value(name)
        settings_key = self.plot_cumulative_settings_map.get(name)
        self.save_setting(settings_key, state)
        current = widget.checkState()

        if state != current:
             widget.setCheckState(state)

        self.compute_spectrum()

    def handle_checkBox_plot_cumulative(self, name):

        widget = self.plot_cumulative_widget_map.get(name)
        state = widget.checkState()
        self.monitor.update(name, state)

    def handle_actionAbout(self):

        epics_version = self.monitor.epics_version()

        msg = "Qt Version: %s\n" % Qt.qVersion()
        msg = msg + "PyEpics Version: %s\n" % epics_version[0]
        msg = msg + "Epics DLL: %s\n" % epics_version[1]
        msg = msg + "MKS Checkpoint: %s\n" % settings.MKS_CHECKPOINT
        msg = msg + "%s" % settings.RELEASE_DATE
        dialog_info(self, msg=msg)

    def init_filter_order(self):
        """
        List of filters in the order in which they must be applied
        to the spectrum.  This is done so that cumulative plots may
        be generated.  Filter ordering was added as a late feature
        which is why this ordering is not more tightly integrated.
        """
        order = [
            'ID-W0-M', 'ID-W1-M', 'ID-W2-M',
            'ID-F1-B', 'ID-F2-B', 'ID-F3-B', 'ID-F4-B', 'ID-F5-B',
            'ID-W3-M', 'ID-W4-M', 'ID-W5-M',
            'ID-F6-B', 'ID-F7-B', 'ID-F8-B', 'ID-F9-B', 'ID-F10-B',
            'ID-W6-M',

            # CT and KES Mono
            'ID-W9-M', 'ID-W10-M', 'ID-W11-M',

            'ID-W7-M',

            # The 'other' filters
            'ID-01-M', 'ID-02-M', 'ID-03-M', 'ID-04-M', 'ID-05-M',

            'BM-W1-M',
            'BM-F1-B', 'BM-F2-B', 'BM-F3-B',
            'BM-W2-M', 'BM-W3-M',
            'BM-01-M', 'BM-02-M', 'BM-03-M', 'BM-04-M', 'BM-05-M',
        ]

        return order

    def init_other_filters(self):
        """
        Unfortunately, ZERO, not OH, is used for the 'other filter' keys.
        This legacy exists because initially, keys were not used
        for 'W' (windows) and 'F' (Filters).  Ideally, OH should have
        been used for 'Other' to maintain consistency.
        """
        self.other_filter_map = {
            'BM-01-M' : self.comboBox_bm_mat1,
            'BM-01-T' : self.lineEdit_bm_thk1,
            'BM-02-M' : self.comboBox_bm_mat2,
            'BM-02-T' : self.lineEdit_bm_thk2,
            'BM-03-M' : self.comboBox_bm_mat3,
            'BM-03-T' : self.lineEdit_bm_thk3,
            'BM-04-M' : self.comboBox_bm_mat4,
            'BM-04-T' : self.lineEdit_bm_thk4,
            'BM-05-M' : self.comboBox_bm_mat5,
            'BM-05-T' : self.lineEdit_bm_thk5,

            'BM-W1-M' : self.lineEdit_bm_mat_w1,    # Window 1
            'BM-W1-T' : self.lineEdit_bm_thk_w1,
            'BM-W2-M' : self.lineEdit_bm_mat_w2,    # Window 2
            'BM-W2-T' : self.lineEdit_bm_thk_w2,
            'BM-W3-M' : self.lineEdit_bm_mat_w3,    # Window 3
            'BM-W3-T' : self.lineEdit_bm_thk_w3,

            'ID-01-M' : self.comboBox_id_mat1,
            'ID-01-T' : self.lineEdit_id_thk1,
            'ID-02-M' : self.comboBox_id_mat2,
            'ID-02-T' : self.lineEdit_id_thk2,
            'ID-03-M' : self.comboBox_id_mat3,
            'ID-03-T' : self.lineEdit_id_thk3,
            'ID-04-M' : self.comboBox_id_mat4,
            'ID-04-T' : self.lineEdit_id_thk4,
            'ID-05-M' : self.comboBox_id_mat5,
            'ID-05-T' : self.lineEdit_id_thk5,

            'ID-W0-M' : self.lineEdit_id_mat_w0,
            'ID-W0-T' : self.lineEdit_id_thk_w0,
            'ID-W1-M' : self.lineEdit_id_mat_w1,
            'ID-W1-T' : self.lineEdit_id_thk_w1,
            'ID-W2-M' : self.lineEdit_id_mat_w2,
            'ID-W2-T' : self.lineEdit_id_thk_w2,
            # Removed WND1605.1-I20-06
            # 'ID-W3-M' : self.lineEdit_id_mat_w3,
            # 'ID-W3-T' : self.lineEdit_id_thk_w3,
            'ID-W4-M' : self.lineEdit_id_mat_w4,
            'ID-W4-T' : self.lineEdit_id_thk_w4,
            'ID-W5-M' : self.lineEdit_id_mat_w5,
            'ID-W5-T' : self.lineEdit_id_thk_w5,
            'ID-W6-M' : self.lineEdit_id_mat_w6,
            'ID-W6-T' : self.lineEdit_id_thk_w6,
            'ID-W7-M' : self.lineEdit_id_mat_w7,
            'ID-W7-T' : self.lineEdit_id_thk_w7,

            # CT Mono
            'ID-W9-M' : self.lineEdit_id_mat_w9,
            'ID-W9-T' : self.lineEdit_id_thk_w9,
            'ID-W10-M': self.lineEdit_id_mat_w10,
            'ID-W10-T': self.lineEdit_id_thk_w10,

            # KES Mono
            'ID-W11-M' : self.lineEdit_id_mat_w11,
            'ID-W11-T' : self.lineEdit_id_thk_w11,
        }

        # Disable the widgets that display the filters in the windows so that
        # their values cannot be changed.  The checkboxes that enable/disable
        # these filters are still active.
        disabled_list = [
            'BM-W1-M', 'BM-W2-M', 'BM-W3-M',
            'BM-W1-T', 'BM-W2-T', 'BM-W3-T',

            'ID-W0-M', 'ID-W1-M', 'ID-W2-M', 'ID-W4-M', 'ID-W5-M', 'ID-W6-M', 'ID-W7-M',
            'ID-W0-T', 'ID-W1-T', 'ID-W2-T', 'ID-W4-T', 'ID-W5-T', 'ID-W6-T', 'ID-W7-T',

            'ID-W9-M', 'ID-W10-M', 'ID-W11-M',
            'ID-W9-T', 'ID-W10-T', 'ID-W11-T'
        ]

        for key in disabled_list:
            widget = self.other_filter_map.get(key)
            widget.setDisabled(True)

        # This loop connects the lineEdit widgets to a handler.  Note that
        # the map originally contained only lineEdit widgets
        for name, widget in self.other_filter_map.iteritems():
            self.init_tooltip_lineEdit_filter(name, widget)

            if not self.is_lineEdit(widget):
                continue

            widget.editingFinished.connect(
                lambda name=name : self.handle_filter_edit_finished(name))

        self.other_filter_check_box_map = {
            'BM-01-C'  : self.checkBox_bm_1,
            'BM-02-C'  : self.checkBox_bm_2,
            'BM-03-C'  : self.checkBox_bm_3,
            'BM-04-C'  : self.checkBox_bm_4,
            'BM-05-C'  : self.checkBox_bm_5,

            'BM-W1-C'  : self.checkBox_bm_w1,
            'BM-W2-C'  : self.checkBox_bm_w2,
            'BM-W3-C'  : self.checkBox_bm_w3,
            'BM-F1-C'  : self.checkBox_bm_f1,
            'BM-F2-C'  : self.checkBox_bm_f2,
            'BM-F3-C'  : self.checkBox_bm_f3,

            'ID-01-C'  : self.checkBox_id_1,
            'ID-02-C'  : self.checkBox_id_2,
            'ID-03-C'  : self.checkBox_id_3,
            'ID-04-C'  : self.checkBox_id_4,
            'ID-05-C'  : self.checkBox_id_5,

            'ID-F1-C'  : self.checkBox_id_f1,
            'ID-F2-C'  : self.checkBox_id_f2,
            'ID-F3-C'  : self.checkBox_id_f3,
            'ID-F4-C'  : self.checkBox_id_f4,
            'ID-F5-C'  : self.checkBox_id_f5,
            'ID-F6-C'  : self.checkBox_id_f6,
            'ID-F7-C'  : self.checkBox_id_f7,
            'ID-F8-C'  : self.checkBox_id_f8,
            'ID-F9-C'  : self.checkBox_id_f9,
            'ID-F10-C' : self.checkBox_id_f10,

            'ID-W0-C'  : self.checkBox_id_w0,
            'ID-W1-C'  : self.checkBox_id_w1,
            'ID-W2-C'  : self.checkBox_id_w2,

            # Removed WND1605.1-I20-06
            # 'ID-W3-C'  : self.checkBox_id_w3,
            'ID-W4-C'  : self.checkBox_id_w4,
            'ID-W5-C'  : self.checkBox_id_w5,
            'ID-W6-C'  : self.checkBox_id_w6,
            'ID-W7-C'  : self.checkBox_id_w7,
            'ID-W9-C'  : self.checkBox_id_w9,
            'ID-W10-C' : self.checkBox_id_w10,
            'ID-W11-C' : self.checkBox_id_w11,
        }

        for name, widget in self.other_filter_check_box_map.iteritems():
            self.init_tooltip_checkBox(name, widget)
            widget.stateChanged.connect(
                lambda arg, name=name : self.handle_filter_check_box(name=name))

        materials = self.mat_mgr.get_list(formatted=True, atomic_number=False)

        # Connect up the editable comboBoxes
        for name, widget in self.other_filter_map.iteritems():
            if self.is_lineEdit(widget):
                continue

            for index, material in enumerate(materials):
                widget.addItem(QtCore.QString(material))

            widget.setInsertPolicy(QtGui.QComboBox.NoInsert)
            widget.setCurrentIndex(-1)
            widget.currentIndexChanged.connect(
                lambda arg, name=name : self.handle_comboBox_other_filter_index_changed(name=name))

            lineEdit = widget.lineEdit()
            lineEdit.editingFinished.connect(
                lambda name=name : self.handle_comboBox_other_filter_text_changed(name=name))

    def init_filter_grids(self):
        grid_list_id = [
            self.gridLayout_id_1,
            self.gridLayout_id_2,
            self.gridLayout_id_3,
            self.gridLayout_id_4,
            # Removed WND1605.1-I20-06
            # self.gridLayout_id_5,
            self.gridLayout_id_6,
            self.gridLayout_id_7,
            self.gridLayout_id_8,
            self.gridLayout_id_9,
            self.gridLayout_id_10,
            self.gridLayout_id_11,
            self.gridLayout_id_12
        ]

        grid_list = grid_list_id

        for grid in grid_list:
            grid.setVerticalSpacing(2)

    def init_groupBox_style(self):

        groupBoxList = [
            self.groupBox_poe_1,
            self.groupBox_poe_3,
            self.groupBox_id_other_filters,
            self.groupBox_id_mouse_position,
            self.groupBox_id_ring_current,
            self.groupBox_id_wiggler_field,

            self.groupBox_id_window_0,
            self.groupBox_id_window_1,
            self.groupBox_id_window_2,
            # Removed WND1605.1-I20-06
            # self.groupBox_id_window_3,
            self.groupBox_id_window_4,
            self.groupBox_id_window_5,
            self.groupBox_id_window_6,
            self.groupBox_id_window_7,

            self.groupBox_id_wbt,

            self.groupBox_id_mono,
            self.groupBox_id_mono_kes,
            self.groupBox_id_mono_ct,

            self.groupBox_bm_filters,
            self.groupBox_bm_other_filters,
            self.groupBox_bm_ring_current,
            self.groupBox_bm_mouse_position,

            self.groupBox_bm_window_1,
            self.groupBox_bm_window_2,
            self.groupBox_bm_window_3,

            self.groupBox_test_ring_current,
            self.groupBox_test_mouse_position,
            self.groupBox_test_wiggler_field,

            self.groupBox_mouse_position_atten,

            self.groupBox_debug_id_mono_ct,
            self.groupBox_debug_id_mono_kes,
        ]

        for groupBox in groupBoxList:
            groupBox.setStyleSheet(GROUP_BOX_STYLE)

    def handle_horizontalSlider(self, value):
        self.compute_spectrum()

    def handle_wiggler_field_active_changed(self, name):
        self.compute_spectrum()
        if not 'Test' in settings.HIDE_TABS:
            self.handle_pushButton_spectrum_bm_clicked()
            self.handle_pushButton_spectrum_id_clicked()

    def handle_pv_wiggler_field(self, name):

        value = self.monitor.get_value(name)
        wiggler_field = "%f" % value

        self.label_wiggler_field_actual.setText(QtCore.QString(wiggler_field))
        self.label_wiggler_field_actual.setToolTip(QtCore.QString(name))

        current_time = time.time()
        update = False
        if current_time - self.last_actual_field_update_time > 5:
            if value > 0:
                update = True
        else:
            try:
                # Multiply by 10 to reduce frequency of auto-updates
                cur_int = int(10.0 * value)
                last_int = int(10.0 * self.monitor.get_value(VAR.WIGGLER_FIELD_ACTUAL))
            except:
                self.error(self, "Unable to determine wiggler field")
                return

            if cur_int != last_int:
                update = True

        if update:
            self.monitor.update(VAR.WIGGLER_FIELD_ACTUAL, value)
            self.last_actual_field_update_time = current_time

    def handle_wiggler_field_actual_changed(self, name):
        self.update_wiggler_field_active()

    def handle_wiggler_field_theoretical_changed(self, name):
        value = self.monitor.get_value(name)
        self.save_setting(SETTINGS.WIGGLER_FIELD_THEORETICAL, value)

        display = clean_float("%f" % value)

        # These should come from a list or map
        self.lineEdit_wiggler_field_theoretical.setText(QtCore.QString(display))
        self.lineEdit_test_wiggler_field_theoretical.setText(QtCore.QString(display))
        self.update_wiggler_field_active()

    def update_wiggler_field_radio_buttons(self):
        use_actual = self.monitor.get_value(VAR.WIGGLER_FIELD_USE_ACTUAL)

        for name, widget in self.wiggler_field_radioButton_map.iteritems():
            value = False
            if name in self.wiggler_field_radioButtons_actual_names and use_actual:
                value = True

            if name in self.wiggler_field_radioButtons_theoretical_names and not use_actual:
                value = True

            widget.setChecked(value)

    def update_wiggler_field_active(self):
        use_actual = self.monitor.get_value(VAR.WIGGLER_FIELD_USE_ACTUAL)
        field = self.monitor.get_value(VAR.WIGGLER_FIELD_ACTIVE)

        if use_actual:
            new_field = self.monitor.get_value(VAR.WIGGLER_FIELD_ACTUAL)
        else:
            new_field = self.monitor.get_value(VAR.WIGGLER_FIELD_THEORETICAL)

        if new_field != field:
            self.monitor.update(VAR.WIGGLER_FIELD_ACTIVE, new_field)

    def handle_wiggler_field_edited(self, widget):

        try:
            value = unicode(widget.text())
            new_value = float(value)
            self.monitor.update(VAR.WIGGLER_FIELD_THEORETICAL, new_value)

        except:
            # Calling error dialog in handler does not seem to work!!
            msg = "Invalid Wiggler Field: '%s'" % value
            self.monitor.emit(self.SIGNAL_ERROR_DIALOG, msg)

            # This should re-populate field
            self.monitor.call_callbacks(VAR.WIGGLER_FIELD_THEORETICAL)

    def handle_wiggler_field_use_actual_updated(self, name):
        self.update_wiggler_field_active()
        self.update_wiggler_field_radio_buttons()

    def handle_tab_index_changed(self, index):
        # This is a total hack!!! Sometimes we seem to be stuck waiting
        # for a PV.  This bypasses the wait
        if len(self.init_filter_pv_list) != 0:
            msg = "Error: init_filter_pv_list not empty. " \
                "System may not be properly initialized."
            self.error(msg)
            self.init_filter_pv_list = []

        self.compute_spectrum()

    def handle_timer_timeout(self):
        self.timer_expired = True
        self.compute_spectrum()

    def handle_timer_mono_energy(self):

        value = self.monitor.get_value(PV.ID_MONO_ENERGY_KES)
        self.monitor.update(VAR.ID_MONO_ENERGY_KES, value)

        value = self.monitor.get_value(PV.ID_MONO_ENERGY_CT)
        self.monitor.update(VAR.ID_MONO_ENERGY_CT, value)

    def init_tooltip_checkBox(self, name, widget):

        if not name.endswith('C'):
            raise ValueError("Don't know how to set tool tip for '%s'" % name)
        text = "Include/Exclude filter in Spectrum Attenuation"
        widget.setToolTip(QtCore.QString(text))

    def init_tooltip_lineEdit_filter(self, name, widget):

        if name.endswith('T'):
            text = 'Effective Filter Thickness (mm)'
        elif name.endswith('M'):
            text = 'Filter Material'
        else:
            raise ValueError("Don't know how to set tool tip for '%s'" % name)

        widget.setToolTip(QtCore.QString(text))

    def init_simulated_filters(self):
        """
        These simulated filters make the 'carbon' filters with the closed PV
        appear like the other beamline filters.
        """

        # NOTE:  The PV order is important!
        simulated_filter_map = {
            'P1_1' : { KEY.PVS : [
                FID.P1_1_MAT,
                FID.P1_1_THK,
                FID.P1_1_CLOSED,
                FSM.P1_1_MAT_1,
                FSM.P1_1_MAT_2,
                FSM.P1_1_THK_1,
                FSM.P1_1_THK_2,
            ] },
            'P1_2' : { KEY.PVS : [
                FID.P1_2_MAT,
                FID.P1_2_THK,
                FID.P1_2_CLOSED,
                FSM.P1_2_MAT_1,
                FSM.P1_2_MAT_2,
                FSM.P1_2_THK_1,
                FSM.P1_2_THK_2,
            ] },
            'P3_1' : { KEY.PVS : [
                FID.P3_1_MAT,
                FID.P3_1_THK,
                FID.P3_1_CLOSED,
                FSM.P3_1_MAT_1,
                FSM.P3_1_MAT_2,
                FSM.P3_1_THK_1,
                FSM.P3_1_THK_2,
            ] },
            'P3_2' : { KEY.PVS : [
                FID.P3_2_MAT,
                FID.P3_2_THK,
                FID.P3_2_CLOSED,
                FSM.P3_2_MAT_1,
                FSM.P3_2_MAT_2,
                FSM.P3_2_THK_1,
                FSM.P3_2_THK_2,
            ] },
        }

        for key, value in simulated_filter_map.iteritems():
            f = SimulatedFilter(monitor=self.monitor)
            f.set_pvs(value.get(KEY.PVS))
            value['filter'] = f

        return simulated_filter_map

    def init_comboBox_map(self):

        comboBox_map = {

            self.comboBox_id_1 : {
                KEY.NAME : 'ID-F1-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.CHECKBOX : self.checkBox_id_f1,
                KEY.PVS : [
                    (FSM.P1_1_MAT_1, FSM.P1_1_THK_1,  True),
                    (FSM.P1_1_MAT_2, FSM.P1_1_THK_2,  False)
                ]
            },
            self.comboBox_id_2 : {
                KEY.NAME : 'ID-F2-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.CHECKBOX : self.checkBox_id_f2,
                KEY.PVS : [
                    (FSM.P1_2_MAT_1, FSM.P1_2_THK_1,  True),
                    (FSM.P1_2_MAT_2, FSM.P1_2_THK_2,  False)
                ],
            },
            self.comboBox_id_3 : {
                KEY.NAME : 'ID-F3-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.CHECKBOX : self.checkBox_id_f3,
                KEY.PVS : [
                    (FID.P1_3_MAT,   FID.P1_3_THK,    True),
                    (FID.P1_3_MAT_1, FID.P1_3_THK_1,  False),
                    (FID.P1_3_MAT_2, FID.P1_3_THK_2,  False),
                    (FID.P1_3_MAT_3, FID.P1_3_THK_3,  False),
                    (FID.P1_3_MAT_4, FID.P1_3_THK_4,  False),
                    (FID.P1_3_MAT_5, FID.P1_3_THK_5,  False)
                ],
            },
            self.comboBox_id_4 : {
                KEY.NAME : 'ID-F4-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.CHECKBOX : self.checkBox_id_f4,
                KEY.PVS : [
                    (FID.P1_4_MAT,   FID.P1_4_THK,    True),
                    (FID.P1_4_MAT_1, FID.P1_4_THK_1,  False),
                    (FID.P1_4_MAT_2, FID.P1_4_THK_2,  False),
                    (FID.P1_4_MAT_3, FID.P1_4_THK_3,  False),
                    (FID.P1_4_MAT_4, FID.P1_4_THK_4,  False),
                    (FID.P1_4_MAT_5, FID.P1_4_THK_5,  False)
                ],
            },
            self.comboBox_id_5 : {
                KEY.NAME : 'ID-F5-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.CHECKBOX : self.checkBox_id_f5,
                KEY.PVS : [
                    (FID.P1_5_MAT,   FID.P1_5_THK,    True),
                    (FID.P1_5_MAT_1, FID.P1_5_THK_1,  False),
                    (FID.P1_5_MAT_2, FID.P1_5_THK_2,  False),
                    (FID.P1_5_MAT_3, FID.P1_5_THK_3,  False),
                    (FID.P1_5_MAT_4, FID.P1_5_THK_4,  False),
                    (FID.P1_5_MAT_5, FID.P1_5_THK_5,  False)
                ],
            },
            self.comboBox_id_6 : {
                KEY.NAME : 'ID-F6-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.CHECKBOX : self.checkBox_id_f6,
                KEY.WBT : WBT_STATUS.IN,
                KEY.PVS : [
                    (FSM.P3_1_MAT_1, FSM.P3_1_THK_1,  True),
                    (FSM.P3_1_MAT_2, FSM.P3_1_THK_2,  False)
                ],
            },
            self.comboBox_id_7 : {
                KEY.NAME : 'ID-F7-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.WBT : WBT_STATUS.IN,
                KEY.CHECKBOX : self.checkBox_id_f7,
                KEY.PVS : [
                    (FSM.P3_2_MAT_1, FSM.P3_2_THK_1,  True),
                    (FSM.P3_2_MAT_2, FSM.P3_2_THK_2,  False)
                ],
            },
            self.comboBox_id_8 : {
                KEY.NAME : 'ID-F8-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.WBT : WBT_STATUS.IN,
                KEY.CHECKBOX : self.checkBox_id_f8,
                KEY.PVS : [
                    (FID.P3_3_MAT,   FID.P3_3_THK,    True),
                    (FID.P3_3_MAT_1, FID.P3_3_THK_1,  False),
                    (FID.P3_3_MAT_2, FID.P3_3_THK_2,  False),
                    (FID.P3_3_MAT_3, FID.P3_3_THK_3,  False),
                    (FID.P3_3_MAT_4, FID.P3_3_THK_4,  False),
                    (FID.P3_3_MAT_5, FID.P3_3_THK_5,  False)
                ],
            },
            self.comboBox_id_9 : {
                KEY.NAME : 'ID-F9-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.WBT : WBT_STATUS.IN,
                KEY.CHECKBOX : self.checkBox_id_f9,
                KEY.PVS : [
                    (FID.P3_4_MAT,   FID.P3_4_THK,    True),
                    (FID.P3_4_MAT_1, FID.P3_4_THK_1,  False),
                    (FID.P3_4_MAT_2, FID.P3_4_THK_2,  False),
                    (FID.P3_4_MAT_3, FID.P3_4_THK_3,  False),
                    (FID.P3_4_MAT_4, FID.P3_4_THK_4,  False),
                    (FID.P3_4_MAT_5, FID.P3_4_THK_5,  False)
                ],
            },
            self.comboBox_id_10 : {
                KEY.NAME : 'ID-F10-B',
                KEY.BEAMLINE : BEAMLINE.ID,
                KEY.WBT : WBT_STATUS.IN,
                KEY.CHECKBOX : self.checkBox_id_f10,
                KEY.PVS : [
                    (FID.P3_5_MAT,   FID.P3_5_THK,    True),
                    (FID.P3_5_MAT_1, FID.P3_5_THK_1,  False),
                    (FID.P3_5_MAT_2, FID.P3_5_THK_2,  False),
                    (FID.P3_5_MAT_3, FID.P3_5_THK_3,  False),
                    (FID.P3_5_MAT_4, FID.P3_5_THK_4,  False),
                    (FID.P3_5_MAT_5, FID.P3_5_THK_5,  False)
                ],
            },
            self.comboBox_bm_1 : {
                KEY.NAME : 'BM-F1-B',
                KEY.BEAMLINE : BEAMLINE.BM,
                KEY.CHECKBOX : self.checkBox_bm_f1,
                KEY.PVS : [
                    (FBM.P1_1_MAT,   FBM.P1_1_THK,    True),
                    (FBM.P1_1_MAT_1, FBM.P1_1_THK_1,  False),
                    (FBM.P1_1_MAT_2, FBM.P1_1_THK_2,  False),
                    (FBM.P1_1_MAT_3, FBM.P1_1_THK_3,  False),
                    (FBM.P1_1_MAT_4, FBM.P1_1_THK_4,  False),
                    (FBM.P1_1_MAT_5, FBM.P1_1_THK_5,  False)
                ],
            },
            self.comboBox_bm_2 : {
                KEY.NAME : 'BM-F2-B',
                KEY.BEAMLINE : BEAMLINE.BM,
                KEY.CHECKBOX : self.checkBox_bm_f2,
                KEY.PVS : [
                    (FBM.P1_2_MAT,   FBM.P1_2_THK,    True),
                    (FBM.P1_2_MAT_1, FBM.P1_2_THK_1,  False),
                    (FBM.P1_2_MAT_2, FBM.P1_2_THK_2,  False),
                    (FBM.P1_2_MAT_3, FBM.P1_2_THK_3,  False),
                    (FBM.P1_2_MAT_4, FBM.P1_2_THK_4,  False),
                    (FBM.P1_2_MAT_5, FBM.P1_2_THK_5,  False)
                ],
            },
            self.comboBox_bm_3 : {
                KEY.NAME : 'BM-F3-B',
                KEY.BEAMLINE : BEAMLINE.BM,
                KEY.CHECKBOX : self.checkBox_bm_f3,
                KEY.PVS : [
                    (FBM.P1_3_MAT,   FBM.P1_3_THK,    True),
                    (FBM.P1_3_MAT_1, FBM.P1_3_THK_1,  False),
                    (FBM.P1_3_MAT_2, FBM.P1_3_THK_2,  False),
                    (FBM.P1_3_MAT_3, FBM.P1_3_THK_3,  False),
                    (FBM.P1_3_MAT_4, FBM.P1_3_THK_4,  False),
                    (FBM.P1_3_MAT_5, FBM.P1_3_THK_5,  False)
                ],
            }
        }
        return comboBox_map

    def init_tooltip_simulated_filter(self, widget, pv):

        for name, value in self.simulated_filter_map.iteritems():
            pvs = value.get(KEY.PVS, [])
            if pv in pvs:
                tip = ''
                for item in pvs:
                    s = "%s\n" % item
                    tip = tip + s
                return tip

    def init_tooltip_comboBox(self):

        for widget, value in self.comboBox_map.iteritems():
            pvs = value.get(KEY.PVS)
            tip = ""
            for item in pvs:

                sim = self.init_tooltip_simulated_filter(widget, item[0])
                if sim:
                    tip = sim
                    break

                s = "%s\n%s\n" % (item[0], item[1])
                tip = tip + s

            widget.setToolTip(QtCore.QString(tip.strip()))

    def init_default_settings(self):
        """

        """
        settings = self.settings.get(FILTER_MANAGER_SETTINGS_KEY, {})

        windows = [
            ('BM-W1-M', 'Beryllium'),
            ('BM-W2-M', 'Beryllium'),
            ('BM-W3-M', 'Kapton'),

            ('BM-W1-T', '0.25'),
            ('BM-W2-T', '0.25'),
            ('BM-W3-T', '0.1'),

            ('ID-W0-M', 'Beryllium'),
            ('ID-W1-M', 'Beryllium'),
            ('ID-W2-M', 'Beryllium'),
            ('ID-W3-M', 'Beryllium'),
            ('ID-W4-M', 'Beryllium'),
            ('ID-W5-M', 'AlN'),
            ('ID-W6-M', 'Beryllium'),
            ('ID-W7-M', 'Kapton'),

            ('ID-W9-M',  'Silicon'),
            ('ID-W10-M', 'Silicon'),
            ('ID-W11-M', 'Silicon'),

            ('ID-W0-T', '0.25'),
            ('ID-W1-T', '0.25'),
            ('ID-W2-T', '0.25'),
            ('ID-W3-T', '0.25'),
            ('ID-W4-T', '0.25'),
            ('ID-W5-T', '0.80'),
            ('ID-W6-T', '0.25'),
            ('ID-W7-T', '1.5'),
        ]

        for item in windows:
            if not settings.has_key(item[0]):
                settings[item[0]] = item[1]

        # This just ensures that new values are not somehow screwed up
        # These lines can safely be removed (and should be removed)
        # after these new settings have been deployed for a while.
        settings['ID-W0-M'] = 'Beryllium'
        settings['ID-W0-T'] = '0.25'

        checkboxes = [
            'BM-W1-C',
            'BM-W2-C',
            'BM-W3-C',

            'BM-F1-C',
            'BM-F2-C',
            'BM-F3-C',

            'ID-F1-C',
            'ID-F2-C',
            'ID-F3-C',
            'ID-F4-C',
            'ID-F5-C',

            'ID-F6-C',
            'ID-F7-C',
            'ID-F8-C',
            'ID-F9-C',
            'ID-F10-C',

            'ID-W0-C',
            'ID-W1-C',
            'ID-W2-C',
            'ID-W3-C',
            'ID-W4-C',
            'ID-W5-C',
            'ID-W6-C',
            'ID-W7-C',

            'ID-W9-C',
            'ID-W10-C',
            'ID-W11-C',
        ]

        for key in checkboxes:
            settings[key] = QtCore.Qt.Checked

        self.settings[FILTER_MANAGER_SETTINGS_KEY] = settings

    def handle_pushButton_apply(self, combo_boxes):
        """
        This handler looks at the selected filters in the comboBoxes and
        sets them active in the beamline
        """
        for combo_box in combo_boxes:
            pv_list = self.comboBox_map.get(combo_box)

            actual_item = None
            for item in pv_list:

                print "LOOKING AT ITEM", item

                if item[COMBO_BOX_MAP_INDEX.ACTUAL] == True:
                    actual_item = item
                    break

            # Next, determine which set of PVs is selected
            index = combo_box.currentIndex()
            selected_item = pv_list[index]

            print "ACTUAL ITEM   :", actual_item
            print "SELECTED ITEM :", selected_item

            if selected_item == actual_item:
                print "No need to update"
                continue

            actual_material = self.monitor.get_value(actual_item[0])
            selected_material = self.monitor.get_value(selected_item[0])

            print "ACTUAL MATERIAL   :", actual_material
            print "SELECTED MATERIAL :", selected_material

    def handle_mouse_pos_bm(self, name):
        self.handle_mouse_pos(name, self.label_bm_plot_x, self.label_bm_plot_y)

    def handle_mouse_pos_id(self, name):
        self.handle_mouse_pos(name, self.label_id_plot_x, self.label_id_plot_y)

    def handle_mouse_pos_test(self, name):
        self.handle_mouse_pos(name, self.label_test_plot_x, self.label_test_plot_y)

    def handle_mouse_pos_atten(self, name):
        self.handle_mouse_pos(name, self.label_atten_plot_x, self.label_atten_plot_y)

    def handle_mouse_pos(self, name, label_x, label_y):
        value = self.monitor.get_value(name)
        x = "%3.5f" % value[0]
        y = "%3.2e" % value[1]
        label_x.setText(QtCore.QString(x))
        label_y.setText(QtCore.QString(y))

    def callback_mouse_pos_bm(self, x, y):
        self.monitor.update(VAR.BM_PLOT_MOUSE_POS, (x, y))

    def callback_mouse_pos_id(self, x, y):
        self.monitor.update(VAR.ID_PLOT_MOUSE_POS, (x, y))

    def callback_mouse_pos_test(self, x, y):
        self.monitor.update(VAR.TEST_PLOT_MOUSE_POS, (x, y))

    def callback_mouse_pos_atten(self, x, y):
        self.monitor.update(VAR.ATTEN_PLOT_MOUSE_POS, (x, y))

    def handle_pushButton_pvc(self):
        self.plot_atten.set_title('PVC: NIST vs Computed')
        self.plot_atten.set_axis_label_y("Mass Atten, Mass E Absorp (cm^2/g)")
        pvc2 = self.mat_mgr.get_mass_attenuation_compound('Poly', self.kevs)
        pvc1 = self.mat_mgr.get_mass_attenuation('Poly', self.kevs)
        pvc2 = [(item[0], item[1] * 1.05) for item in pvc2]
        self.plot_atten.new_plot(pvc1, data2=pvc2,  data3=[(1, 1)])

    def handle_pushButton_water(self):

        self.monitor.reset('breem-1-I20-02:material')
        self.plot_atten.set_title('Water: NIST vs Computed')
        self.plot_atten.set_axis_label_y("Mass Atten, Mass E Absorp (cm^2/g)")
        water2 = self.mat_mgr.get_mass_attenuation_compound('Water', self.kevs)
        water1 = self.mat_mgr.get_mass_attenuation('Water', self.kevs)
        water2 = [(item[0], item[1] * 1.05) for item in water2]
        self.plot_atten.new_plot(water1, data2=water2,  data3=[(1, 1)])

    def handle_pushButton_kapton(self):

        self.plot_atten.set_title('Kapton: NIST vs Computed')
        self.plot_atten.set_axis_label_y("Mass Atten, Mass E Absorp (cm^2/g)")
        kapton2 = self.mat_mgr.get_mass_attenuation_compound('kapton', self.kevs)
        kapton1 = self.mat_mgr.get_mass_attenuation(' kap', self.kevs)
        kapton2 = [(item[0], item[1] * 1.05) for item in kapton2]
        self.plot_atten.new_plot(kapton1, data2=kapton2, data3=[(1 ,1)])

    def handle_pushButton_test(self):
        print "TEST button pushed"
        self.error("this is an error message")
        self.error("this is an error message")
        self.error("this is an error message")
        self.error("this is an error message")

    def error(self, msg):
        self.monitor.emit(self.SIGNAL_ERROR_DIALOG, msg)

    def handle_mass_atten_thickness(self, name):
        value = self.monitor.get_value(VAR.MASS_ATTEN_THICKNESS)
        display = "%f" % value
        display = clean_float(display)
        self.lineEdit_mass_atten_thickness.setText(QtCore.QString(display))
        self.plot_selected_material()

    def handle_mass_atten_thickness_edit(self):
        value = unicode(self.lineEdit_mass_atten_thickness.text())
        valid = True
        try:
            new_value = float(value)
        except:
            new_value = self.monitor.get_value(VAR.MASS_ATTEN_THICKNESS)
            valid = False

        self.monitor.update(VAR.MASS_ATTEN_THICKNESS, new_value)
        self.save_setting(SETTINGS.MASS_ATTEN_THICKNESS, new_value)

        if not valid:
            self.error("Invalid thickness '%s'" % value)

    def handle_filter_check_box(self, name=None):
        widget = self.other_filter_check_box_map.get(name)
        self.filter_manager.update_other_filters(name, widget.checkState())

    def is_lineEdit(self, widget):

        if hasattr(widget, 'editingFinished'):
            return True
        elif hasattr(widget, 'currentIndexChanged'):
            return False

        raise ValueError("Unexpected widget %s" % repr(widget))

    def handle_var_other_filters_updated(self, name):
        data = self.monitor.get_value(VAR.OTHER_FILTERS)

        if not isinstance(data, dict):
            print "Other filter data is not a dictionary!"
            return

        for key, value in data.iteritems():
            # print "handle_var_other_filters_updated() -> key '%s' value '%s'" % \
            #       (key, value)

            widget = self.other_filter_map.get(key)
            parts = key.split('-')

            if widget:
                if value:
                    value = value.strip()
                else:
                    value = ''

                if parts[2] == 'T':
                    value = clean_float(value)

                if self.is_lineEdit(widget):
                    widget.setText(QtCore.QString(value))
                else:
                    self.set_comboBox_other_filter(key, widget, value)

                continue

            widget = self.other_filter_check_box_map.get(key)
            if widget:
                widget.setCheckState(value)

        self.compute_spectrum()

    def set_comboBox_other_filter(self, name, widget, material_in):

        material = self.mat_mgr.resolve_material(material_in)

        # Can just set index to -1 if material not found
        index = widget.findText(QtCore.QString(material))
        widget.setCurrentIndex(index)

    @decorator_dialog_error
    def handle_filter_edit_finished(self, name):

        current = self.monitor.get_value(VAR.OTHER_FILTERS)
        current = current.get(name, '')

        try:
            success = False
            widget = self.other_filter_map.get(name)
            value = unicode(widget.text())
            self.filter_manager.update_other_filters(name, value)
            success = True
        finally:
            if not success:
                print "restore old value here!!"
                # self.handle_var_other_filters_updated(name)
                widget.setText(QtCore.QString(current))

    def handle_radioButton_wiggler_field(self, name=None):
        """
        This handler is called when a ring current radio button is clicked.
        """
        use_actual = True
        if name in self.wiggler_field_radioButtons_theoretical_names:
            use_actual = False

        self.monitor.update(VAR.WIGGLER_FIELD_USE_ACTUAL, use_actual)
        self.save_setting(SETTINGS.WIGGLER_FIELD_USE_ACTUAL, use_actual)

    def handle_radioButton_ring_current(self, name=None):
        """
        This handler is called when a ring current radio button is clicked.
        """
        use_actual = True
        if name in self.ring_current_radioButtons_theoretical_names:
            use_actual = False

        self.monitor.update(VAR.RING_CURRENT_USE_ACTUAL, use_actual)
        self.save_setting(SETTINGS.RING_CURRENT_USE_ACTUAL, use_actual)

    def update_ring_current_active(self):

        use_actual = self.monitor.get_value(VAR.RING_CURRENT_USE_ACTUAL)
        current = self.monitor.get_value(VAR.RING_CURRENT_ACTIVE)

        if use_actual:
            new_current = self.monitor.get_value(VAR.RING_CURRENT_ACTUAL)
        else:
            new_current = self.monitor.get_value(VAR.RING_CURRENT_THEORETICAL)

        if new_current != current:
            self.monitor.update(VAR.RING_CURRENT_ACTIVE, new_current)

    def handle_ring_current_use_actual_updated(self, name):
        self.update_ring_current_active()
        self.update_ring_current_radio_buttons()

    def handle_ring_current_actual_changed(self, name):
        self.update_ring_current_active()

    def update_ring_current_radio_buttons(self):
        use_actual = self.monitor.get_value(VAR.RING_CURRENT_USE_ACTUAL)

        for name, widget in self.ring_current_radioButton_map.iteritems():
            value = False
            if name in self.ring_current_radioButtons_actual_names and use_actual:
                value = True

            if name in self.ring_current_radioButtons_theoretical_names and not use_actual:
                value = True

            widget.setChecked(value)

    def handle_ring_current_active_changed(self, name):

        self.compute_spectrum()

        if not 'Test' in settings.HIDE_TABS:
            self.handle_pushButton_spectrum_bm_clicked()
            self.handle_pushButton_spectrum_id_clicked()

    def handle_ring_current_theoretical_changed(self, name):
        value = self.monitor.get_value(name)
        self.save_setting(SETTINGS.RING_CURRENT_THEORETICAL, value)

        display = clean_float("%f" % value)

        # These should come from a list or map
        self.lineEdit_id_ring_current_theoretical.setText(QtCore.QString(display))
        self.lineEdit_bm_ring_current_theoretical.setText(QtCore.QString(display))
        self.lineEdit_test_ring_current_theoretical.setText(QtCore.QString(display))

        self.update_ring_current_active()

    def handle_error_dialog_signal(self, msg):
        dialog_error(self, msg=msg)

    def handle_line_editing_finished(self, name):
        item = self.line_edit_map.get(name)
        widget = item[0]
        handler = item[1]
        handler(widget)

    def handle_ring_current_edited(self, widget):

        try:
            value = unicode(widget.text())
            new_value = float(value)
            self.monitor.update(VAR.RING_CURRENT_THEORETICAL, new_value)

        except:
            # Calling error dialog in handler does not seem to work!!
            msg = "Invalid ring current: '%s'" % value
            self.monitor.emit(self.SIGNAL_ERROR_DIALOG, msg)
            self.monitor.call_callbacks(VAR.RING_CURRENT_THEORETICAL)

    def handle_radioButton_element(self):
        self.plot_selected_material()

    def handle_var_id_mono_energy(self, pv_name):

        value = self.monitor.get_value(pv_name)
        try:
            energy = float(value)
            display = clean_float('%.2f' % energy)
        except Exception, e:
            print "exception: %s" % str(e)
            display = '-'

        data = self.id_mono_energy_label_map.get(pv_name)
        widget = data[0]
        display = data[1] + ' (%s)' % display

        widget.setText(QtCore.QString(display))
        self.update_mono_energy()

    def update_mono_energy(self):
        """
        Updates the mono energy depending on the mono in use.
        There is just a single "mono energy" which is used when
        plotting the spectrum.
        """
        which_mono = self.monitor.get_value(VAR.ID_MONO_USE)
        if which_mono == ID_MONO_STATUS.CT_IN:
            energy = self.monitor.get_value(PV.ID_MONO_ENERGY_CT)
        elif which_mono == ID_MONO_STATUS.KES_IN:
            energy = self.monitor.get_value(PV.ID_MONO_ENERGY_KES)
        else:
            energy = None

        try:
            energy = float(energy)
            if energy < 1.0 or energy > 1000.0:
                energy = None
        except:
            energy = None

        self.monitor.update(VAR.ID_MONO_ENERGY, energy)
        self.compute_spectrum()

    def handle_pv_system_time(self, name):

        # Put the system time into the plot title to save vertical space.
        # Also, it's quite noticable there.

        system_time  = self.monitor.get_value(name)
        value = QtCore.QString("%s  (%s)" % (PLOT_TITLE, system_time))

        self.plot_bm.set_title(value)
        self.plot_id.set_title(value)

    def handle_pv_ring_current(self, name):
        value = self.monitor.get_value(name)
        current = "%f" % value

        # First, update the displays of the actual ring current
        self.label_test_ring_current_actual.setText(QtCore.QString(current))
        self.label_test_ring_current_actual.setToolTip(QtCore.QString(name))

        self.label_bm_ring_current_actual.setText(QtCore.QString(current))
        self.label_bm_ring_current_actual.setToolTip(QtCore.QString(name))

        self.label_id_ring_current_actual.setText(QtCore.QString(current))
        self.label_id_ring_current_actual.setToolTip(QtCore.QString(name))

        # Record in an internal variable every time the int portion
        # of the value changes.  This allows re-computation only when
        # int value changes

        current_time = time.time()

        update = False
        if current_time - self.last_actual_current_update_time > 5:
            if value > 0:
                update = True
        else:
            try:
                cur_int = int(value)
                last_int = int(self.monitor.get_value(VAR.RING_CURRENT_ACTUAL))
            except:
                self.error(self, "Unable to determine ring current")
                return

            if cur_int != last_int:
                update = True

        if update:
            self.monitor.update(VAR.RING_CURRENT_ACTUAL, value)
            self.last_actual_current_update_time = current_time

    def handle_pv_ring_energy(self, name):
        value = self.monitor.get_value(name)
        print "Ring Energy:", value

    def get_wiggler_field(self):
        wiggler_field = self.monitor.get_value(VAR.WIGGLER_FIELD_ACTIVE)
        return wiggler_field

    def get_ring_current(self):
        ring_current = self.monitor.get_value(VAR.RING_CURRENT_ACTIVE)
        return ring_current

    def handle_pushButton_spectrum_id_clicked(self):

        ring_current = self.get_ring_current()
        ring_energy = self.monitor.get_value(RING_PV.ENERGY)

        parts = ring_energy.split()
        ring_energy_gev = float(parts[0])

        # Must convert ring current to Amps for computations
        ring_current_amps = float(ring_current) / 1000.0
        wiggler_field = self.get_wiggler_field()

        if ring_current is None or wiggler_field is None:
            return

        result = self.spectrum.spectrum_id(ring_energy_gev, ring_current_amps,
            wiggler_field, self.kevs)

        self.plot_test.set_title("ID Spectrum")
        self.plot_test.set_axis_label_x("Photon Energy (keV)")
        self.plot_test.set_axis_label_y("Central Brilliance")
        self.plot_test.new_plot(result)

    def handle_pushButton_spectrum_bm_clicked(self):

        ring_current = self.get_ring_current()
        ring_energy = self.monitor.get_value(RING_PV.ENERGY)

        parts = ring_energy.split()
        ring_energy_gev = float(parts[0])

        # Must convert ring current to Amps for computations
        ring_current_amps = float(ring_current) / 1000.0
        bend_magnet_field = settings.BEND_MAGNET_FIELD

        if not ring_current:
            return

        result = self.spectrum.spectrum(ring_energy_gev, ring_current_amps,
            bend_magnet_field, self.kevs)

        self.plot_test.set_title("BM Spectrum")
        self.plot_test.set_axis_label_x("Photon Energy (keV)")
        self.plot_test.set_axis_label_y("Central Brilliance")
        self.plot_test.new_plot(result)

    def handle_pushButton_bessel_2_clicked(self):
        range = self.spectrum.make_log_sequence(0.00001, 10, 500)
        result = self.spectrum.hxy(range, 0.19)
        data = zip(range, result)

        self.plot_test.set_title("H(X, y)")
        self.plot_test.set_axis_label_x("X")
        self.plot_test.set_axis_label_y("Y")
        self.plot_test.new_plot(data, None)

        range = [2.64]
        result = self.spectrum.hxy(range, 0.19)
        # print "X: 0.19, y: %s result: %s" % (range, result)

    def handle_pushButton_bessel_clicked(self):
        range = self.spectrum.make_log_sequence(0.00001, 10, 500)
        result = self.spectrum.h2(range)
        data = zip(range, result)

        self.plot_test.set_title("H(y)")
        self.plot_test.set_axis_label_x("X")
        self.plot_test.set_axis_label_y("Y")
        self.plot_test.new_plot(data, None)

    def handle_comboBox_other_filter_index_changed(self, name):

        widget = self.other_filter_map.get(name)

        # print "NAME %s current index: %d" % (name, widget.currentIndex())

        value = unicode(widget.currentText())
        self.filter_manager.update_other_filters(name, value)

    @decorator_dialog_error
    def handle_comboBox_other_filter_text_changed(self, name):

        try:
            comboBox = self.other_filter_map.get(name)
            current_index = comboBox.currentIndex()
            lineEdit = comboBox.lineEdit()
            value = unicode(lineEdit.text())

            # print "The text changed to '%s'" % value
            success = False
            self.filter_manager.update_other_filters(name, value)
            success = True
        finally:
            if not success:
                comboBox.setCurrentIndex(current_index)

    def handle_comboBox_filter(self, name):
        # Brute force recompute rather than figure out which combo box changed
        # print "handle_comboBox_filter(): combo box changed", name
        self.compute_spectrum()

    def init_comboBoxes_filter(self):
        """
        This initializer method populates the comboBoxes listed in
        self.comboBox_map.  The entries are assigned userData = material_pv.
        This allows an event handler to search the list of comboBoxes to
        find the one associated with a particular PV
        """
        for comboBox, value in self.comboBox_map.iteritems():

            pvs = value.get(KEY.PVS)

            for value in pvs:
                material_pv = value[COMBO_BOX_MAP_INDEX.MATERIAL_PV]
                thickness_pv = value[COMBO_BOX_MAP_INDEX.THICKNESS_PV]

                # Store the material PV name (not value) in the comboBox
                # user data. This allows the value to change dynamically
                user_data = QtCore.QVariant(QtCore.QString(material_pv))
                comboBox.addItem(QtCore.QString(material_pv), userData=user_data)

                # Append these PVs to a list.  Only when a handler has been
                # called for ALL pvs in list is the app considered 'initialized'
                self.init_filter_pv_list.append(material_pv)
                self.init_filter_pv_list.append(thickness_pv)

                if material_pv.startswith(SIM_PV_PREFIX):
                    self.monitor.add(material_pv, None)
                else:
                    self.monitor.add(material_pv)
                self.monitor.connect(material_pv, self.handle_comboBox_init)

                if thickness_pv.startswith(SIM_PV_PREFIX):
                    self.monitor.add(thickness_pv, None)
                else:
                    self.monitor.add(thickness_pv)
                self.monitor.connect(thickness_pv, self.handle_comboBox_init)

            # Adds a "none" option, which is not required as there apparently
            # is always a "none" in the actual filter assembly
            add_none = False
            if add_none:
                userData = QtCore.QVariant(QtCore.QString("none"))
                comboBox.addItem(QtCore.QString("- none"), userData=userData)

    def handle_comboBox_init(self, name):
        """
        This handler responds to changes to the material/thickness
        PVs and updates the filter comboBoxes accordingly
        """

        # Remove handled PV from list.  When list becomes empty, the
        # filter comboBox initialization is complete
        self.init_filter_pv_list = \
            [x for x in self.init_filter_pv_list if x != name]

        resolved_combo_box = None
        try:
            for comboBox, value in self.comboBox_map.iteritems():

                pvs = value.get(KEY.PVS)

                for item in pvs:
                    if name in item:
                        resolved_combo_box = comboBox
                        material_pv  = item[COMBO_BOX_MAP_INDEX.MATERIAL_PV]
                        thickness_pv = item[COMBO_BOX_MAP_INDEX.THICKNESS_PV]
                        raise ExceptionFound

        except ExceptionFound:
            pass

        if not resolved_combo_box:
            print "DID NOT FIND COMBO BOX....  IS THIS AN ERROR??"
            return

        material = self.monitor.get_value(material_pv)
        thickness = self.monitor.get_value(thickness_pv)

        if not thickness:
            thickness = "0.0"

        if not material:
            print "Material PV not yet initialized"
            return

        material_resolved = self.mat_mgr.resolve_material(material)
        if not material_resolved:
            self.error("Unknown/unsupported material '%s'" % material)
        else:
            material = material_resolved

        actual = '-'
        if item[COMBO_BOX_MAP_INDEX.ACTUAL]:
           actual = '*'

        th = '%.4f' % float(thickness)
        text = "%s %s (%s)" % (actual, material, clean_float(th))

        # The material_pv is used to identify the comboBox item
        user_data = QtCore.QVariant(QtCore.QString(material_pv))
        index = resolved_combo_box.findData(user_data)

        if index < 0:
            raise ValueError("Could not find '%s'" % material_pv)

        resolved_combo_box.setItemText(index, QtCore.QString(text))

        # Recompute the spectrum on material/thickness changes
        # *iff* there are no items left to initialize
        if len(self.init_filter_pv_list) == 0:
            self.compute_spectrum()

    def init_debug_tab(self, filter_class, grid, cols=4):
        """
        This method programatically adds PVs to labels on a debug grid layout
        """

        pv_list = []
        for k, v in filter_class.__dict__.iteritems():
            if k.startswith('__'):
                continue

            pv_list.append((k, v))

        pv_list.sort()
        item_count = len(pv_list)

        rows = int(math.ceil(float(len(pv_list))/float(cols)))

        font = QtGui.QFont('Courier', 9)
        font.setWeight(QtGui.QFont.Light)

        index = 0
        for x in xrange(cols):
            for y in xrange(rows):

                if index >= item_count:
                    break

                item = pv_list[index]
                index += 1

                print "ADDING DEBUG ITEM", item
                label1 = QtGui.QLabel()
                label1.setText(QtCore.QString(item[0]))
                label1.setToolTip(QtCore.QString(item[1]))
                label1.setFont(font)

                label2 = QtGui.QLabel()
                label2.setText(QtCore.QString(item[1]))
                label2.setToolTip(QtCore.QString(item[1]))
                label2.setFont(font)

                self.debug_label_map[item[1]] = (label1, label2)

                grid.addWidget(label1, y, x * 2)
                grid.addWidget(label2, y, x * 2 + 1)

                self.monitor.add(item[1])
                self.monitor.connect(item[1], self.handle_debug_label)

    def handle_debug_label(self, name):
        value = self.monitor.get_value(name)
        labels = self.debug_label_map.get(name)

        label_title = labels[0]
        label_value = labels[1]

        if value is None:
            value = name
            label_value.setStyleSheet("QLabel { background-color : black; color : white; }")
        else:
            label_value.setStyleSheet("QLabel { color : blue; }")

        label_value.setText(QtCore.QString(unicode(value)))
        label_value.setToolTip(QtCore.QString(name))
        label_title.setToolTip(QtCore.QString(name))

        label_value.setText(QtCore.QString(unicode(value)))
        label_value.setToolTip(QtCore.QString(name))
        label_title.setToolTip(QtCore.QString(name))

    def init_comboBox_materials(self):

        selected_material = self.get_setting(SETTINGS.SELECTED_MATERIAL)
        selected_index = None

        materials = self.mat_mgr.get_list(formatted=True)

        for index, material in enumerate(materials):
            self.comboBox_materials.addItem(QtCore.QString(material))

            if selected_material and selected_material == material:
                selected_index = index

        if selected_index:
            self.comboBox_materials.setCurrentIndex(selected_index)

        self.comboBox_materials.currentIndexChanged.connect(
            self.handle_comboBox_materials)

    def handle_actionMonitor_List(self):
        self.monitor.print_list()

    def handle_pushButton_monitor_list_clicked(self):
        self.monitor.print_list()

    def plot_selected_material(self):

        text = unicode(self.comboBox_materials.currentText())

        # Get rid of the trailing (x) in the comboBox text
        pos = text.find('(')
        if pos > 0:
            parts = text.split('(')
            text = ''.join(parts[:-1])

        text = text.strip()

        material = self.mat_mgr.resolve_material(unicode(text))

        print "Plot selected material '%s'" % material
        self.plot_atten.set_title(text)
        self.plot_atten.set_axis_label_x("Photon Energy (KeV)")

        data1 = self.mat_mgr.get_mass_attenuation(material, kevs=self.kevs)
        data2 = None
        data3 = None

        if self.mat_mgr.has_nist_data(material):
            data2 = self.mat_mgr.get_mass_energy_absorption(material)
            data3 = self.mat_mgr.get_mass_attenuation(material)

        if self.radioButton_raw.isChecked():
            self.plot_atten.set_axis_label_y("Mass Atten, Mass E Absorp (cm^2/g)")
            self.plot_atten.new_plot(data1, data2=data2, data3=data3)

        else:
            self.plot_atten.set_axis_label_y("Attenuation")

            density = self.mat_mgr.get_density(material)
            thickness = self.monitor.get_value(VAR.MASS_ATTEN_THICKNESS)

            data2 = self.spectrum.compute_attenuation(data1, density, thickness)
            data2 = self.clean_for_plot([data2], 1e-6)[0]

            if data3:
                data3 = self.spectrum.compute_attenuation(data3, density, thickness)
                data3 = self.clean_for_plot([data3], 1e-6)[0]

            self.plot_atten.new_plot(data1, data2=data2, data3=data3)

    def handle_comboBox_materials(self, index):
        material = self.comboBox_materials.currentText()
        self.save_setting(SETTINGS.SELECTED_MATERIAL, unicode(material))
        self.plot_selected_material()

    @decorator_dialog_error
    def compute_spectrum(self, force=False):

        if self.skip_compute or not self.timer_expired:
             # print "waiting for timer"
             return

        # First, check if all controls initialized.... this is a hack
        # to prevent spectrum from being computed with invalid settings
        if len(self.init_filter_pv_list):
            if len(self.init_filter_pv_list) < 5:
                print "compute_spectrum(): waiting for: ", self.init_filter_pv_list
                for pv in self.init_filter_pv_list:
                    self.monitor.reset(pv)
            return

        ring_current = self.get_ring_current()
        ring_current_amps = float(ring_current) / 1000.0

        ring_energy = self.monitor.get_value(RING_PV.ENERGY)
        parts = ring_energy.split()
        ring_energy_gev = float(parts[0])

        current_tab_index = self.tabWidget.currentIndex()

        if current_tab_index == 0:
            self.compute_spectrum_id(ring_current_amps, ring_energy_gev, self.plot_id, force=force)

        elif current_tab_index == 1:
            self.compute_spectrum_bm(ring_current_amps, ring_energy_gev, self.plot_bm, force=force)

        if not self.position_set:
            # Having difficulty getting the window dimensions reset to the
            # save position, so attempt to set the position after the spectrum
            # has been computed and the appropriate side panels determined.
            # Seems to help
            self.position_set = True
            self.get_position()

    def get_filters(self, beamline):

        wdt_status = self.monitor.get_value(VAR.WBT_STATUS)

        filters = []
        for comboBox, value in self.comboBox_map.iteritems():

            # print "consider combo box: %s" % value.get(KEY.NAME)
            if not value.get(KEY.BEAMLINE) == beamline:
                # print "combo box not in beamline checked", value.get(KEY.NAME)
                continue

            check_box = value.get(KEY.CHECKBOX)
            if not check_box.checkState() == QtCore.Qt.Checked:
                # print "combo box not checked", value.get(KEY.NAME)
                continue

            status = value.get(KEY.WBT)
            if status is not None and status != wdt_status:
                # print "get_filters(): omit filter due to WBT", value
                continue

            name = value.get(KEY.NAME)
            pv_list = value.get(KEY.PVS)

            # Next, determine which set of PVs is selected
            index = comboBox.currentIndex()

            pv_tuple = pv_list[index]
            material = self.monitor.get_value(pv_tuple[0])
            thickness = self.monitor.get_value(pv_tuple[1])

            items = self.mat_mgr.get_filter_layers(name, material, thickness)
            filters.extend(items)

        return filters

    def sort_filters(self, filters):

        result = []
        for key in self.filter_order:
            for i, filter in enumerate(filters):
                if filter[0] == key:
                    result.append(filter)
                    # Note: Once the filter is located, we cannot break
                    # from the search loop.  This is because a "filter" may
                    # appear multiple times in the filter list.  This happens
                    # due to filters that are comprised of 'layers'
                    # (e.g. Al 3mm + Sn0.5)
                    # break

        # Debugging
        for filter in filters:
            if filter not in result:
                msg = "filter %s not sorted" % repr(filter)
                raise ValueError(msg)

        return result

    def get_min_plot_value(self, cumulative, min_factor):

        spectrum = cumulative[0]
        attenuated = cumulative[-1]

        max_spectrum = max([item[1] for item in spectrum])
        max_atten = max([item[1] for item in attenuated])

        s = 0
        while max_spectrum > 10.0:
            max_spectrum = max_spectrum / 10.0
            s += 1

        m = 0
        while max_atten > 10.0:
            max_atten = max_atten / 10.0
            m += 1

        if max_atten < 5.0:
            m -= 1

        # Show at least two order of magnitude based on max value of
        # unattenuated spectrum
        m = min(s - 2, m)
        m = m - min_factor

        # Bump up the min value a bit so it does not draw directly on the
        # plot gridline
        min_val = math.pow(10.0, m) * 1.05

        return min_val

    def compute_spectrum_id(self, ring_current_amps, ring_energy_gev, plotter, force=False):

        # Get all the filters
        filters = self.get_filters(BEAMLINE.ID)
        other_filters = self.filter_manager.get_beamline_filters(BEAMLINE.ID)

        filters.extend(other_filters)
        filters = self.sort_filters(filters)

        wiggler_field = self.get_wiggler_field()

        min_factor = self.horizontalSlider_id.maximum() - \
                     self.horizontalSlider_id.value()

        mono_energy = self.monitor.get_value(VAR.ID_MONO_ENERGY)

        # print "compute_spectrum_id: min_factor: %f force: %s" % (min_factor, force)

        if not force and not self.spectrum_update_required_id(ring_current_amps,
                ring_energy_gev, wiggler_field, filters, mono_energy):

            if min_factor == self.min_factor_id:
                return

            else:
                cumulative = self.prev_spectrum_id

        else:
            spectrum = self.spectrum.spectrum_id(ring_energy_gev, ring_current_amps,
                wiggler_field, self.kevs)

            msg = []

            # Apply the filters to the spectrum
            cumulative = self.spectrum.apply_filters(spectrum,
                filters, kevs=self.kevs, msg=msg)
            self.prev_spectrum_id = cumulative

            msg = '\n'.join(msg)
            plotter.setToolTip(QtCore.QString(msg))

        self.min_factor_id = min_factor

        locked = False
        if self.checkBox_id_lock.checkState() == QtCore.Qt.Checked:
            locked = True

        if not locked:
            min_val = self.get_min_plot_value(cumulative, min_factor)
        else:
            min_val = 0.01

        cumulative = self.clean_for_plot(cumulative, min_val)

        spectrum = cumulative[0]
        attenuated = cumulative[-1]

        if max(attenuated) == 0.0:
            attenuated = None

        show_cumulative = self.monitor.get_value(VAR.PLOT_CUMULATIVE_ID)
        if show_cumulative == QtCore.Qt.Checked and len(cumulative) > 2:
            cumulative = cumulative[1:-1]
        else:
            cumulative = []

        # Make a white line
        kevs = [item[0] for item in spectrum]
        white = []
        for x in kevs:
            white.append((x, min_val))

        plotter.new_plot(spectrum, data2=attenuated, white=white,
                gray=cumulative, mono_energy=mono_energy)

    def compute_spectrum_bm(self, ring_current_amps, ring_energy_gev, plotter, force=False):

        filters = self.get_filters(BEAMLINE.BM)
        other_filters = self.filter_manager.get_beamline_filters(BEAMLINE.BM)
        filters.extend(other_filters)
        filters = self.sort_filters(filters)

        min_factor = self.horizontalSlider_bm.maximum() - \
                     self.horizontalSlider_bm.value()

        if not force and not self.spectrum_update_required_bm(ring_current_amps,
                ring_energy_gev, filters):

            if min_factor == self.min_factor_bm:
                return
            else:
                cumulative = self.prev_spectrum_bm
        else:
            spectrum = self.spectrum.spectrum(ring_energy_gev, ring_current_amps,
                settings.BEND_MAGNET_FIELD, self.kevs)

            msg = []
            # Apply the filters to the spectrum
            cumulative = self.spectrum.apply_filters(spectrum,
                filters, self.kevs, msg=msg)

            msg = '\n'.join(msg)
            plotter.setToolTip(QtCore.QString(msg))

            self.prev_spectrum_bm = cumulative

        self.min_factor_bm = min_factor
        min_val = self.get_min_plot_value(cumulative, min_factor)

        cumulative = self.clean_for_plot(cumulative, min_val)

        spectrum = cumulative[0]
        attenuated = cumulative[-1]

        if max(attenuated) == 0.0:
            attenuated = None

        show_cumulative = self.monitor.get_value(VAR.PLOT_CUMULATIVE_BM)
        if show_cumulative == QtCore.Qt.Checked and len(cumulative) > 2:
            cumulative = cumulative[1:-1]
        else:
            cumulative = []

        # Make a white line
        kevs = [item[0] for item in spectrum]
        white = []
        for x in kevs:
            white.append((x, min_val))

        plotter.new_plot(spectrum, data2=attenuated, white=white,
                gray=cumulative)

    def spectrum_update_required_bm(self, current, energy, filters):

        cumulative = self.monitor.get_value(VAR.PLOT_CUMULATIVE_BM)

        if self.bm_spectrum_cache_params.get('cumulative') == cumulative:
            if self.bm_spectrum_cache_params.get('current') == current:
                if self.bm_spectrum_cache_params.get('energy') == energy:
                    if self.bm_spectrum_cache_params.get('filters') == filters:
                        # print "BM Spectrum: No update required"
                        return False

        self.update_counter_bm += 1
        print "BM Spectrum: Update required", self.update_counter_bm
        self.bm_spectrum_cache_params['cumulative'] = cumulative
        self.bm_spectrum_cache_params['current'] = current
        self.bm_spectrum_cache_params['energy'] = energy
        self.bm_spectrum_cache_params['filters'] = filters

        return True

    def spectrum_update_required_id(self, current, energy, field, filters, mono_energy):

        cumulative = self.monitor.get_value(VAR.PLOT_CUMULATIVE_ID)

        check_list = [
            ('cumulative', cumulative),
            ('current', current),
            ('energy', energy),
            ('field', field),
            ('filters', filters),
            ('mono_energy', mono_energy)
        ]

        try:
            for item in check_list:
                have = self.id_spectrum_cache_params.get(item[0])
                if have != item[1]:
                    print "Item '%s' stale %s != %s" % (item[0], item[1], have)
                    raise ExceptionBreak

        except ExceptionBreak:
            for item in check_list:
                self.id_spectrum_cache_params[item[0]] = item[1]

            self.update_counter_id += 1
            print "ID Spectrum: Update required", self.update_counter_id
            return True

        return False

    def clean_for_plot(self, data, threshold):

        result = []

        for item in data:
            result.append(self.clean_for_plot_one(item, threshold))

        return result

    def clean_for_plot_one(self, data, threshold, truncate=False):

        result = []
        count = len(data)
        for i in xrange(count):
            item = data[i]
            if item[1] < threshold:
                old_val = item[1]
                item = (item[0], threshold)
                result.append(item)

                # This ugly hack interpolates an extra datapoint
                # where the plot crossed the threshold
                if i < (count - 1):
                    next_item = data[i+1]
                    if next_item[1] > threshold:
                        y_diff = next_item[1] - old_val
                        p = (threshold - old_val) / y_diff
                        new_x = item[0] + (next_item[0] - item[0]) * p
                        result.append((new_x, threshold))
            else:
                result.append(item)

        if truncate:
            # This strips values at the right of the plot that have
            # been capped at the minimum threshold value.  But it does not
            # look good to switch scales dynamically.
            for i in xrange(len(result)):
                p = i + 1
                item = result[-p]

                if item[1] > threshold:
                    break

            if i > 0:
                result = result[:-p]

        return result

    def load_settings(self):

        f = None

        try:
            home = os.path.expanduser("~")
            filename = os.path.join(home, SETTINGS_FILE_NAME)
            f = open(filename, 'r')

            print "Loading settings from '%s'" % filename

            self.settings = simplejson.load(f)

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
            filename = os.path.join(home, SETTINGS_FILE_NAME)
            directory = os.path.dirname(os.path.realpath(filename))

            print "saving settings to settings file '%s'" % filename
            print "these are the settings to save", self.settings

            if not os.path.exists(directory):
                os.makedirs(directory)

            self.settings = self.filter_manager.get_settings(self.settings)

            f = open(filename, 'w+')
            simplejson.dump(self.settings, f, indent=4, sort_keys=True)

        except Exception, e:
            print "Error saving user settings file %s: %s" % (filename, str(e))

        finally:
            if f:
                f.close()

    def get_setting(self, setting, default=None):
        """
        Return a single setting
        """
        my_settings = self.settings.get(SETTINGS.KEY, {})
        return my_settings.get(setting, default)

    def save_setting(self, setting, value):
        """
        Save a single setting
        """
        my_settings = self.settings.get(SETTINGS.KEY, {})
        my_settings[setting] = value
        self.settings[SETTINGS.KEY] = my_settings

    def closeEvent(self, event):

        if settings.PROMPT_ON_QUIT:

            msg = "Are you sure you want to quit?"

            if not dialog_yes_no(sender=self, msg=msg):
                event.ignore()
                return

        for value in self.simulated_filter_map.itervalues():
            filter = value.get('filter')
            filter.terminate()

        self.filter_manager.terminate()
        self.save_position()
        self.monitor.disconnect(self)
        self.monitor.stop()
        self.save_settings()

        # Get a list of all callbacks.... should be empty
        callback_list = self.monitor.get_callback_list()
        if len(callback_list):
            msg = "Error: there are still registered callbacks: %s" % callback_list
            dialog_error(self, msg=msg)

    def hide_tab(self, tab_widget, tab_title):

        hide_index = None
        for i in xrange(tab_widget.count()):
            if unicode(tab_widget.tabText(i)) == tab_title:
                hide_index = i
                break

        if hide_index:
            tab_widget.removeTab(i)
