# System Imports
from PyQt4 import QtCore
import math
import threading
import time

# App imports
import settings
from utils import Constant
from utils import to_rad
from utils import to_float

from utils.monitor import KEY as MONITOR_KEY
from core import VAR as CORE_VAR
from line import LineGeneric


if settings.USE_SIMULATED_PVS:
    BASE = 'breem:'
    REL_WB = 'relWB'
else:
    BASE = ''
    REL_WB = 'relativeToWB'

class PV(Constant):
    ACT_HEIGHT          = BASE + 'OPTICS1605-3-I20:height'
    ACT_ANGLE           = BASE + 'OPTICS1605-3-I20:angle'
    ACT_HEIGHT_REL_WB   = BASE + 'OPTICS1605-3-I20:height:' + REL_WB

    SET_HEIGHT          = BASE + 'OPTICS1605-3-I20:height:sp'
    SET_ANGLE           = BASE + 'OPTICS1605-3-I20:angle:sp'

    ACTIVE_ANGLE        = BASE + 'OPTICS1605-3-I20:height:active'
    ACTIVE_HEIGHT       = BASE + 'OPTICS1605-3-I20:angle:active'

    STOP_VERT           = BASE + 'SMTR1605-3-I20-27:stop'
    STOP_TILT           = BASE + 'SMTR1605-3-I20-28:stop'

    MOVE                = BASE + 'OPTICS1605-3-I20:moveToPosition'
    ERR_STR             = BASE + 'OPTICS1605-3-I20:opticsTableErr'

class VAR(Constant):
    CFG_HEIGHT_OFFSET   = 'var:ot:cfg:height_offset'

    PROPOSED_ANGLE      = 'var:ot:proposed:angle'
    PROPOSED_HEIGHT     = 'var:ot:proposed:height'

    TABLE_ACTUAL        = 'var:ot:table:actual'
    TABLE_PROPOSED      = 'var:ot:table:proposed'
    FIS_ACTUAL          = 'var:ot:fis:actual'
    FIS_PROPOSED        = 'var:of:fis:proposed'

    ALIGNED_TO_ACTUAL   = 'var:ot:aligned:to:actual'

class ACTION(Constant):
    ALIGN_FIS   = 'align_fis'
    ACTUAL      = 'actual'
    GO          = 'go'
    STOP        = 'stop'

class OpticsTable(QtCore.QObject):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        # Initialize the parent object
        super(OpticsTable, self).__init__(*args, **kwargs)

        pvs = PV.items()
        for pv_name in pvs.itervalues():
            self.monitor.add(pv_name)

        vars = VAR.items()
        for var_name in vars.itervalues():
            self.monitor.add(var_name)

        self.monitor.put(VAR.PROPOSED_HEIGHT, 1000)
        self.monitor.put(VAR.PROPOSED_ANGLE, 0)

        # If any of these PVs change, recompute the positions
        update_position_list = [
            VAR.CFG_HEIGHT_OFFSET,
            VAR.PROPOSED_ANGLE,
            VAR.PROPOSED_HEIGHT,
            PV.ACT_ANGLE,
            PV.ACT_HEIGHT,
        ]

        for pv_name in update_position_list:
            self.monitor.connect(pv_name, self.compute_positions)

        self.ping_list = [
            VAR.FIS_PROPOSED,
            VAR.FIS_ACTUAL,
            VAR.TABLE_PROPOSED,
            VAR.TABLE_ACTUAL,
        ]

        proposed_equal_actual_list = [
            VAR.PROPOSED_ANGLE,
            VAR.PROPOSED_HEIGHT,
            PV.ACT_ANGLE,
            PV.ACT_HEIGHT,
        ]

        for pv_name in update_position_list:
            self.monitor.connect(pv_name, self.check_aligned)

        self._timer = threading.Timer(1, self._timer_worker)
        self._timer.start()
        self._terminate_flag = False
        self._timer_queue = []

        self._dialog_callback = None

    def set_dialog_callback(self, func):
        self._dialog_callback = func

    def dialog(self, msg):
        print msg
        if self._dialog_callback:
            self._dialog_callback(msg)

    def _timer_worker(self):
        """
        TODO: This timer is essentially a duplicate of the one in the camera
        positioner. Should consider refactoring this
        """
        while not self._terminate_flag:
            time.sleep(0.2)
            try:
                item = self._timer_queue.pop(0)
            except:
                continue

            pv_name = item[0]
            value = item[1]

            if not pv_name: continue

            print "Timer queue putting %s --> %s" % (repr(value), pv_name)
            self.monitor.put(pv_name, value)

    def check_aligned(self, pv_name):

        aligned = True

        try:

            val1 = self.monitor.get_value(VAR.PROPOSED_ANGLE)
            val2 = self.monitor.get_value(PV.ACT_ANGLE)

            if abs(to_float(val1) - to_float(val2)) > 0.01:
                raise ValueError("angle not aligned")

            val1 = self.monitor.get_value(VAR.PROPOSED_HEIGHT)
            val2 = self.monitor.get_value(PV.ACT_HEIGHT)

            if abs(to_float(val1) - to_float(val2)) > 0.01:
                raise ValueError("height not aligned")

        except Exception, e:
            # print str(e)
            aligned = False

        self.monitor.put(VAR.ALIGNED_TO_ACTUAL, aligned)

    def action_actual_position(self):

        # Get the actual positions
        height = self.monitor.get_value(PV.ACT_HEIGHT)
        angle = self.monitor.get_value(PV.ACT_ANGLE)

        self.monitor.put(VAR.PROPOSED_ANGLE, angle)
        self.monitor.put(VAR.PROPOSED_HEIGHT, height)

    def action_align_fis(self):

        pivot = settings.X_MM_OPTICS_TABLE_UPSTREAM_EDGE
        fis_height = self.monitor.get_value(VAR.CFG_HEIGHT_OFFSET)

        angle = self.monitor.get_value(CORE_VAR.BEAM_ANGLE_PROPOSED)
        beam_disp = self.monitor.get_value(CORE_VAR.BEAM_VDISP_PROPOSED)
        a_rad = to_rad(angle)

        sx = settings.BEAM_ORIGIN_X
        sz = settings.BEAM_ORIGIN_Z + beam_disp
        fx = sx + math.cos(a_rad)
        fz = sz + math.sin(a_rad)

        beam_line = LineGeneric(sx, sz, fx, fz)
        beam_height_at_pivot = beam_line.get_height(pivot)

        # Compute table to FIS height
        try:
            fis_height = float(fis_height)

            height_diff = fis_height / math.cos(a_rad)
            target_height = beam_height_at_pivot - height_diff

            self.monitor.put(VAR.PROPOSED_ANGLE, angle)
            self.monitor.put(VAR.PROPOSED_HEIGHT, target_height)

        except Exception, e:
            print "Error"

    def action_go(self):

        height = self.monitor.get_value(VAR.PROPOSED_HEIGHT)
        angle = self.monitor.get_value(VAR.PROPOSED_ANGLE)

        if settings.ENABLE_MOVE_OT is False:
            target_height = "Height (PV: %s): <b>%.3f</b><br><br>" % (PV.SET_HEIGHT, to_float(height))
            target_angle = "Angle  (PV: %s): <b>%.3f</b>" % (PV.SET_ANGLE, to_float(angle))

            msg = "<b>Optics Table move disabled in settings.py</b><br><br>" + \
                  "The calculated target positions are:<br><br>" + \
                  target_height + target_angle

            self.dialog(msg)
            return

        self.monitor.put(PV.ACTIVE_ANGLE, 1)
        self.monitor.put(PV.ACTIVE_HEIGHT, 1)

        self.monitor.put(PV.SET_HEIGHT, to_float(height))
        self.monitor.put(PV.SET_ANGLE, to_float(angle))

        self.monitor.put(PV.MOVE, 1)
        self._timer_queue.append((None, 0))
        self._timer_queue.append((PV.MOVE, 0))

    def action_stop(self):

        # Not sure what the actual behaviour is... rely on the h/w (and
        # simulator) to reset these PVs bask to 0
        self.monitor.put(PV.STOP_TILT, 1)
        self.monitor.put(PV.STOP_VERT, 1)

    def handle_action(self, action):

        if action == ACTION.ACTUAL:
            self.action_actual_position()

        elif action == ACTION.ALIGN_FIS:
            self.action_align_fis()

        elif action == ACTION.GO:
            self.action_go()

        elif action == ACTION.STOP:
            self.action_stop()

        else:
            raise ValueError("Action: %s: Not supported" % action)

    def ping(self):
        """
        Do whatever needs to be done when positions change
        """
        for pv_name in self.ping_list:
            self.monitor.call_callbacks(pv_name)

    def terminate(self):
        self.monitor.disconnect(self)

    def compute_positions(self, pv_name):

        # print "Compute positions called from", pv_name

        # Get the actual position
        height = self.monitor.get_value(PV.ACT_HEIGHT)
        angle = self.monitor.get_value(PV.ACT_ANGLE)
        a_rad = to_rad(angle)
        fis_height = self.monitor.get_value(VAR.CFG_HEIGHT_OFFSET)

        # print "The height is:", repr(height)
        # print "The angle is", repr(angle)
        # print "The fis height is:", repr(fis_height)

        # First, compute the actual tabletop render line
        pivot = settings.X_MM_OPTICS_TABLE_UPSTREAM_EDGE
        start = settings.OPTICS_TABLE_RENDER_START
        stop = settings.OPTICS_TABLE_RENDER_STOP

        try:
            diff = pivot - start
            start_x = pivot - diff * math.cos(a_rad)
            start_z = height - diff * math.sin(a_rad)

            diff = stop - pivot
            stop_x = pivot + diff * math.cos(a_rad)
            stop_z = height + diff * math.sin(a_rad)

            position = (start_x, start_z, stop_x, stop_z)
        except Exception, e:
            print "Exception computing OT position", str(e)
            position = (None, None, None, None)
        self.monitor.put(VAR.TABLE_ACTUAL, position)

        try:
            fis_height = float(fis_height)

            # Next compute the F.I.S render line.
            fis_start_x = start_x - fis_height * math.sin(a_rad)
            fis_start_z = start_z + fis_height * math.cos(a_rad)

            fis_stop_x = stop_x - fis_height * math.sin(a_rad)
            fis_stop_z = stop_z + fis_height * math.cos(a_rad)

            position = (fis_start_x, fis_start_z, fis_stop_x, fis_stop_z)
        except Exception, e:
            print "Exception computing OT position", str(e)
            position = (start_x, start_z, stop_x, stop_z)

        self.monitor.put(VAR.FIS_ACTUAL, position)

        # Repeat but for proposed position

        try:
            height = float(self.monitor.get_value(VAR.PROPOSED_HEIGHT))
            angle = float(self.monitor.get_value(VAR.PROPOSED_ANGLE))
            a_rad = to_rad(angle)

            diff = pivot - start
            start_x = pivot - diff * math.cos(a_rad)
            start_z = height - diff * math.sin(a_rad)

            diff = stop - pivot
            stop_x = pivot + diff * math.cos(a_rad)
            stop_z = height + diff * math.sin(a_rad)

            position = (start_x, start_z, stop_x, stop_z)
        except Exception, e:
            print "Exception computing OT position", str(e)
            position = (None, None, None, None)
        self.monitor.put(VAR.TABLE_PROPOSED, position)

        try:
            fis_height = float(fis_height)

            # Next compute the F.I.S render line.  It is assumed the F.I.S
            fis_start_x = start_x - fis_height * math.sin(a_rad)
            fis_start_z = start_z + fis_height * math.cos(a_rad)

            fis_stop_x = stop_x - fis_height * math.sin(a_rad)
            fis_stop_z = stop_z + fis_height * math.cos(a_rad)

            position = (fis_start_x, fis_start_z, fis_stop_x, fis_stop_z)
        except Exception, e:
            print "Exception computing OT position", str(e)
            position = (start_x, start_z, stop_x, stop_z)

        self.monitor.put(VAR.FIS_PROPOSED, position)
