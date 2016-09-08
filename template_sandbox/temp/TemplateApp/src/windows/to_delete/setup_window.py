# System imports

# Library imports
from PyQt4 import QtGui
from PyQt4 import QtCore

# App imports
from windows.css import GROUP_BOX_STYLE

import settings
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant
from utils import to_float
from utils.gui import UiMixin
from utils.gui import dialog_info
from utils.gui import dialog_yes_no

from camera_positioner import VAR as CP_VAR
from optics_table import VAR as OT_VAR

from windows.drag_text_mixin import DragTextMixin

class VAR(Constant):
    CMD_CAMERA_POS      = 'var:cmd_camera'
    CMD_MRT_LIFT        = 'var:cmd_mrt_list'
    CMD_SHIELDING       = 'var:cmd_shielding'
    CMD_OPTICS_TABLE    = 'var:cmd_optics_table'
    CMD_KE_MONO         = 'var:cmd_ke_mono'
    CMD_CT_MONO         = 'var:cmd_ct_mono'
    CMD_ION_CP          = 'var:cmd_ion_cp'

class SetupWindow(QtGui.QMainWindow, UiMixin, DragTextMixin):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        center_point = kwargs['center']
        del kwargs['center']

        super(SetupWindow, self).__init__(*args, **kwargs)

        self._close_flag = False
        self._close_callback = None

        # Set up the user interface from Designer.
        self.load_ui("windows/setup_window.ui")
        self.setWindowTitle(settings.APP_NAME)

        self.ok_clicked = False

        self.editMap = {
            VAR.CMD_CAMERA_POS : (
                self.lineEdit_camera_positioner,    None),
            VAR.CMD_MRT_LIFT : (
                self.lineEdit_mrt_lift,             None),
            VAR.CMD_ION_CP : (
                self.lineEdit_ion_cp,               None),
            VAR.CMD_SHIELDING : (
                self.lineEdit_shielding,            None),
            VAR.CMD_OPTICS_TABLE : (
                self.lineEdit_optics_table,         None),
            VAR.CMD_KE_MONO : (
                self.lineEdit_ke_mono,              None),
            VAR.CMD_CT_MONO : (
                self.lineEdit_ct_mono,              None),
            CP_VAR.CFG_DETECTOR_ANGLE : (
                self.lineEdit_cp_detector_angle,    '{:,.3f}'),
            CP_VAR.CFG_DETECTOR_OFFSET : (
                self.lineEdit_cp_detector_offset,   '{:,.3f}'),
            CP_VAR.CFG_LASER_ANGLE : (
                self.lineEdit_cp_laser_angle,       '{:,.3f}'),
            CP_VAR.CFG_LASER_OFFSET : (
                self.lineEdit_cp_laser_offset,      '{:,.3f}'),
            CP_VAR.CFG_EXTENSION : (
                self.lineEdit_cp_extension,         '{:,.3f}'),
            OT_VAR.CFG_HEIGHT_OFFSET : (
                self.lineEdit_ot_height_offset,     '{:,.3f}'),
        }

        self.orig_value = {}

        for var_name, data in self.editMap.iteritems():
            widget = data[0]
            value = self.monitor.get_value(var_name)
            print "SETUP: var '%s' value '%s'" % (var_name, value)

            #widget.setText(QtCore.QString(value))
            widget.editingFinished.connect(
                lambda var_name=var_name : self.handle_lineEdit_finished(var_name))

            self.lineEdit_render(var_name, value, setOrig=True)

        self.pushButton_ok.clicked.connect(self.handle_pushButton_ok)
        self.pushButton_cancel.clicked.connect(self.handle_pushButton_cancel)

        self.init_cp_tab()

        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def set_close_callback(self, callback):
        self._close_callback = callback

    def init_cp_tab(self):

        label_map = {
            self.label_cp_laser_offset_desc:
                "<b>OFFSET:</b> The height (mm) of the laser above the center " + \
                "of the Camera Positioner stage when the extension is 0.0 mm. " + \
                "Care must be taken to ensure this value is correct when the " + \
                "laser also has an angle with respect to the stage.",

            self.label_cp_laser_angle_desc:
                "<b>ANGLE:</b> The angle (deg) of the laser with respect to the " + \
                "Camera Positioner stage.  A positive angle points the laser " + \
                "down with respect to the stage.",

            self.label_cp_detector_offset_desc:
                "<b>OFFSET:</b> The height (mm) of the detector line-of-sight " + \
                "above the center " + \
                "of the Camera Positioner stage when the extension is 0.0 mm. " + \
                "Care must be taken to ensure this value is correct when the " + \
                "detector also has an angle with respect to the stage.",

            self.label_cp_detector_angle_desc:
                "<b>ANGLE:</b> The angle (deg) of the detector line-of-sight " + \
                "with respect to the " + \
                "Camera Positioner stage.  A positive angle points the detector " + \
                "line-of-sight down with respect to the stage.",

            self.label_cp_extension_desc:
                "<b>EXTENSION:</b> This program sets the stage extension to " + \
                "the value specified here whenever the <b>Laser to Beam</b> or " + \
                "<b>Detector to Beam</b> buttons are clicked.",

            self.label_ot_height_offset_desc:
                "<b>Fast Imaging Shutter (F.I.S.):</b> The Z offset " + \
                "(i.e., height above the table) of the Fast Imaging Shutter.",

            self.label_ot_not_used: " "
        }

        for widget, text in label_map.iteritems():
            widget.setWordWrap(True)
            widget.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            widget.setText(QtCore.QString(text))

        groupBoxes = [
            self.groupBox_cp_laser_config,
            self.groupBox_cp_detector_config,
            self.groupBox_cp_extension,
            self.groupBox_ot_setup
        ]

        for groupBox in groupBoxes:
            groupBox.setStyleSheet(GROUP_BOX_STYLE)

    def handle_lineEdit_finished(self, var_name):

        if self._close_flag:
            print "handle_lineEdit_finished() called with close flag"
            return

        # Get the value and validate it
        data = self.editMap.get(var_name)
        widget = data[0]

        value = unicode(widget.text())
        self.lineEdit_render(var_name, value)

        # display = self.format_value(var_name, value)

    def format_value(self, var_name, value):

        print "FORMAT VALUE CALLED FOR VAR %s VAL %s" % (var_name, value)
        data = self.editMap.get(var_name)
        fmt = data[1]

        if fmt is None:
            # Must be a string
            try:
                display = unicode(value).strip()
            except:
                display = unicode("")

        else:
            print "THIS IS THE FMT", fmt, value
            # display = fmt.format(value)
            try:
                value = to_float(value)
                display = fmt.format(value)
            except Exception, e:
                print "Error formatting float", str(e), var_name, value
                display = unicode("")

        return display

    def lineEdit_render(self, var_name, value, setOrig=False):
        print "lineEdit render called for var '%s'" % var_name

        if self._close_flag:
            print "lineEdit_render() called with close flag"
            return

        display = self.format_value(var_name, value)

        data = self.editMap.get(var_name)
        widget = data[0]
        #fmt = data[1]
        #
        #if fmt is None:
        #    # Must be a string
        #    try:
        #        display = unicode(value).strip()
        #    except:
        #        display = unicode("")
        #
        #else:
        #    try:
        #        display = fmt.format(value)
        #    except Exception, e:
        #        print "Error formtting float", str(e), var_name, value
        #        display = unicode("")

        widget.setText(QtCore.QString(display))

        if setOrig:
            self.orig_value[var_name] = display

    def handle_pushButton_ok(self):
        print "OK clicked"

        self._close_flag = True

        for var, data in self.editMap.iteritems():
            widget = data[0]
            print "%s %s %s" % (var, self.orig_value.get(var), unicode(widget.text()))
            orig = unicode(self.orig_value.get(var, ''))

            try:
                new =  unicode(widget.text())
            except Exception, e:
                print "Exception: %s for var %s" % (str(e), var)
                new = ''

            new = new.strip()
            print "%s %s %s" % (var, orig, new)

            if new != orig:
                print "value changed for var", var
                self.monitor.put(var, new)

        self.ok_clicked = True
        self.close()

    def handle_pushButton_cancel(self):
        print "cancel clicked"
        self.close()

    def edits_made(self):

        print "CHECKING FOR EDITS ======================================== "
        if self.ok_clicked:
            return False

        changed = False
        for var, data in self.editMap.iteritems():
            widget = data[0]
            orig = unicode(self.orig_value.get(var, ''))

            try:
                new =  unicode(widget.text())
            except Exception, e:
                print "Exception: %s for var %s" % (str(e), var)
                new = ''

            new = new.strip()
            print "LOOK FOR CHANGES: VAR %s ORIG %s NEW: '%s'" % (var, orig, new)
            if new != orig:
                print "value changed for var", var
                changed = True
                break

        return changed

    def closeEvent(self, event):

        print "setup window close event"

        if self.edits_made():
            if not dialog_yes_no(sender=self, msg='Discard Changes?', title="Setup"):
                event.ignore()
                return

        self._close_flag = True
        if self._close_callback:
            self._close_callback(self)

        self.monitor.disconnect(self)
