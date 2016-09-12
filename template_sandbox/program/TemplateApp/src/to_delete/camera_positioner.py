# System Imports
from PyQt4 import QtCore
import random
import math
import time
import threading

# App imports
from utils import Constant
from utils import to_rad
from utils import to_float

from line import LineGeneric

from core import VAR as CORE_VAR
from utils.monitor import KEY as MONITOR_KEY
import settings

CAM_POS_RENDER_LENGTH = 7500


if settings.USE_SIMULATED_PVS:
    BASE = 'breem:'
    CP_ERR = BASE + 'STAGE1605-4-I20:errorStr'
    REL_WB = 'relWB'
else:
    BASE = ''
    CP_ERR = 'STAGE1605-4-I20:cameraPositionerError' # Too long to prepend BASE
    REL_WB = 'relativeToWB'

class PV(Constant):

    HEIGHT_REL_WB        = BASE + 'STAGE1605-4-I20:height:' + REL_WB
    CUR_HEIGHT           = BASE + 'STAGE1605-4-I20:height'
    CUR_ANGLE            = BASE + 'STAGE1605-4-I20:angle'
    CUR_EXTENSION        = BASE + 'STAGE1605-4-I20:extension'
    SET_HEIGHT           = BASE + 'STAGE1605-4-I20:height:sp'
    SET_ANGLE            = BASE + 'STAGE1605-4-I20:angle:sp'
    SET_EXTENSION        = BASE + 'STAGE1605-4-I20:extension:sp'
    ACTIVE_HEIGHT        = BASE + 'STAGE1605-4-I20:height:active'
    ACTIVE_ANGLE         = BASE + 'STAGE1605-4-I20:angle:active'
    ACTIVE_EXTENSION     = BASE + 'STAGE1605-4-I20:extension:active'
    STOP                 = BASE + 'STAGE1605-4-I20:stop:seq'
    KILL                 = BASE + 'STAGE1605-4-I20:kill:seq'
    MOVE                 = BASE + 'STAGE1605-4-I20:moveToPosition'
    ERR_STR              = CP_ERR

class VAR(Constant):

    # Camera positioner laser and detector config settings
    CFG_LASER_ANGLE     = 'var:cp:cfg:laser_angle'
    CFG_LASER_OFFSET    = 'var:cp:cfg:laser_offset'
    CFG_DETECTOR_ANGLE  = 'var:cp:cfg:detector_angle'
    CFG_DETECTOR_OFFSET = 'var:cp:cfg:detector_offset'
    CFG_EXTENSION       = 'var:cp:cfg:extension'

    # The "current" camera positioner position
    CUR_ANGLE           = 'var:cp:cur_angle'
    CUR_HEIGHT          = 'var:cp:cur_height'
    CUR_EXTENSION       = 'var:cp:cur_extension'

    # These variables are tuples that contain the position of the
    # actual and proposed laser and detector positions
    LASER_PROPOSED      = 'var:cp:laser_proposed'
    LASER_ACTUAL        = 'var:cp:laser_actual'
    DETECTOR_PROPOSED   = 'var:cp:detector_proposed'
    DETECTOR_ACTUAL     = 'var:cp:detector_actual'

    ALIGNED_TO_ACTUAL   = 'var:cp:aligned_to_actual'

class ACTION(Constant):

    ALIGN_LASER     = 'laser'
    ALIGN_DETECTOR  = 'detector'
    ACTUAL          = 'actual'
    GO              = 'go'
    STOP            = 'stop'

class CameraPositioner(QtCore.QObject):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        # Initialize the parent object
        super(CameraPositioner, self).__init__(*args, **kwargs)

        self._enabled = False

        pvs = PV.items()
        for pv_name in pvs.itervalues():
            self.monitor.add(pv_name)

        vars = VAR.items()
        for var_name in vars.itervalues():
            self.monitor.add(var_name)

        self.ping_list = [
            VAR.LASER_PROPOSED,
            VAR.LASER_ACTUAL,
            VAR.DETECTOR_PROPOSED,
            VAR.DETECTOR_ACTUAL,
        ]

        # If any of these PVs change, recompute the positions of the
        # laser and detector
        update_position_list = [
            VAR.CFG_DETECTOR_ANGLE,
            VAR.CFG_DETECTOR_OFFSET,
            VAR.CFG_LASER_ANGLE,
            VAR.CFG_LASER_OFFSET,
            VAR.CFG_EXTENSION,
            VAR.CUR_ANGLE,
            VAR.CUR_EXTENSION,
            VAR.CUR_HEIGHT,
            PV.CUR_ANGLE,
            PV.CUR_HEIGHT,
            PV.CUR_EXTENSION
        ]

        for pv_name in update_position_list:
            self.monitor.connect(pv_name, self.compute_positions)

        aligned_check_list = [
            VAR.CUR_ANGLE,
            VAR.CUR_EXTENSION,
            VAR.CUR_HEIGHT,
            PV.CUR_ANGLE,
            PV.CUR_HEIGHT,
            PV.CUR_EXTENSION
        ]

        for pv_name in aligned_check_list:
            self.monitor.connect(pv_name, self.check_aligned)

        self.monitor.put(VAR.CUR_ANGLE, 0)
        self.monitor.put(VAR.CUR_HEIGHT, 1400)
        self.monitor.put(VAR.CUR_EXTENSION, 0)

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

    def enable(self, value):
        self._enabled = value

    def check_aligned(self, pv_name):

        # print "CP check_aligned() called"
        aligned = True

        try:

            val1 = self.monitor.get_value(VAR.CUR_EXTENSION)
            val2 = self.monitor.get_value(PV.CUR_EXTENSION)

            if abs(to_float(val1) - to_float(val2)) > 0.01:
                raise ValueError("extension not aligned")

            val1 = self.monitor.get_value(VAR.CUR_HEIGHT)
            val2 = self.monitor.get_value(PV.CUR_HEIGHT)

            if abs(to_float(val1) - to_float(val2)) > 0.01:
                raise ValueError("height not aligned")

            val1 = self.monitor.get_value(VAR.CUR_ANGLE)
            val2 = self.monitor.get_value(PV.CUR_ANGLE)

            if abs(to_float(val1) - to_float(val2)) > 0.01:
                raise ValueError("angle not aligned")

        except Exception, e:
            # print str(e)
            aligned = False

        self.monitor.put(VAR.ALIGNED_TO_ACTUAL, aligned)

    def action_align_laser_to_beam(self):
        return self.action_align_target_to_beam(
            VAR.CFG_LASER_ANGLE, VAR.CFG_LASER_OFFSET)

    def action_align_detector_to_beam(self):
        return self.action_align_target_to_beam(
            VAR.CFG_DETECTOR_ANGLE, VAR.CFG_DETECTOR_OFFSET)

    def action_align_target_to_beam(self, target_angle_pv, target_height_pv):
        """
        Align the "target" (beam or detector line of sight) to the beam
        """
        # First get angle of the beam
        beam_angle = self.monitor.get_value(CORE_VAR.BEAM_ANGLE_PROPOSED)
        beam_disp = self.monitor.get_value(CORE_VAR.BEAM_VDISP_PROPOSED)

        if None in [beam_angle, beam_disp]:
            raise ValueError("Cannot align camera positioner.<br>Beam position unknown.")

        # What is the laser angle"
        target_angle = to_float(self.monitor.get_value(target_angle_pv))
        stage_angle = beam_angle - target_angle

        self.monitor.put(VAR.CUR_ANGLE, stage_angle)

        # Next we must set extension
        extension = to_float(self.monitor.get_value(VAR.CFG_EXTENSION))
        self.monitor.put(VAR.CUR_EXTENSION, extension)

        stage_height = self.monitor.get_value(VAR.CUR_HEIGHT)
        target_height = self.monitor.get_value(target_height_pv)

        # Now get the line start/stop coordinates
        sx, sz, fx, fz = self.compute_line_position(stage_height, stage_angle,
            extension, target_height, target_angle)

        target_line = LineGeneric(sx, sz, fx, fz)
        target_height_at_mrt = target_line.get_height(settings.X_MM_MRT)

        sx = settings.BEAM_ORIGIN_X
        sz = settings.BEAM_ORIGIN_Z + beam_disp
        fx = sx + math.cos(to_rad(beam_angle))
        fz = sz + math.sin(to_rad(beam_angle))

        beam_line = LineGeneric(sx, sz, fx, fz)
        beam_height_at_mrt = beam_line.get_height(settings.X_MM_MRT)

        height_diff = beam_height_at_mrt - target_height_at_mrt
        stage_height += height_diff
        self.monitor.put(VAR.CUR_HEIGHT, stage_height)

    def action_align_to_current(self):
        height = self.monitor.get_value(PV.CUR_HEIGHT)
        angle = self.monitor.get_value(PV.CUR_ANGLE)
        extension = self.monitor.get_value(PV.CUR_EXTENSION)

        self.monitor.put(VAR.CUR_HEIGHT, to_float(height))
        self.monitor.put(VAR.CUR_ANGLE, to_float(angle))
        self.monitor.put(VAR.CUR_EXTENSION, to_float(extension))

    def action_go(self):
        """
        Move the current cam pos to the proposed position
        """
        height = self.monitor.get_value(VAR.CUR_HEIGHT)
        angle = self.monitor.get_value(VAR.CUR_ANGLE)
        extension = self.monitor.get_value(VAR.CFG_EXTENSION)

        if settings.ENABLE_MOVE_CP is False:
            target_height = "Height (PV: %s): <b>%.3f</b><br><br>" % (PV.SET_HEIGHT, to_float(height))
            target_angle = "Angle  (PV: %s): <b>%.3f</b><br><br>" % (PV.SET_ANGLE, to_float(angle))
            target_ext = "Extension (PV: %s): <b>%.3f</b><br><br>" % (PV.SET_EXTENSION, to_float(extension))
            msg = "<b>Camera Positioner move disabled in settings.py</b><br><br>" + \
                  "The calculated target positions are:<br><br>" + \
                  target_height + target_angle + target_ext

            self.dialog(msg)
            return

        self.monitor.put(PV.ACTIVE_ANGLE, 1)
        self.monitor.put(PV.ACTIVE_HEIGHT, 1)
        self.monitor.put(PV.ACTIVE_EXTENSION, 1)

        self.monitor.put(VAR.CUR_EXTENSION, to_float(extension))
        self.monitor.put(PV.SET_HEIGHT, to_float(height))
        self.monitor.put(PV.SET_ANGLE, to_float(angle))
        self.monitor.put(PV.SET_EXTENSION, to_float(extension))

        self.monitor.put(PV.MOVE, 1)
        self._timer_queue.append((None, 0))
        self._timer_queue.append((PV.MOVE, 0))

    def action_stop(self):
        # print "action_stop called"
        self.monitor.put(PV.STOP, 1)
        self._timer_queue.append((None, 0))
        self._timer_queue.append((PV.STOP, 0))

    def handle_action(self, action):
        if action == ACTION.ALIGN_LASER:
            self.action_align_laser_to_beam()
        elif action == ACTION.ALIGN_DETECTOR:
            self.action_align_detector_to_beam()
        elif action == ACTION.ACTUAL:
            self.action_align_to_current()
        elif action == ACTION.GO:
            self.action_go()
        elif action == ACTION.STOP:
            self.action_stop()
        else:
            raise ValueError("Unknown action", repr(action))

    def ping(self):
        """
        Do whatever needs to be done when positions change
        """
        for pv_name in self.ping_list:
            self.monitor.call_callbacks(pv_name)

    def test(self):

        extension_orig = self.monitor.get_value(VAR.CFG_EXTENSION)
        for angle in [-15, -10, -5, 0, 5, 10, 15]:
            self._timer_queue.append((VAR.CUR_ANGLE, angle))

        height = 2000
        for _ in xrange(10):
            self._timer_queue.append((VAR.CUR_HEIGHT, height))
            height -= 200

        self._timer_queue.append((VAR.CUR_ANGLE, 0))

        extension = 0
        for _ in xrange(10):
            self._timer_queue.append((VAR.CFG_EXTENSION, extension))
            self._timer_queue.append((VAR.CUR_EXTENSION, extension))
            extension += 100
        self._timer_queue.append((VAR.CFG_EXTENSION, extension_orig))

    def compute_line_position(self, stage_height, stage_angle, stage_extension,
                              line_offset_height, line_offset_angle):

        #print "compute_line_position() called ---------------------"
        #print "stage_height", stage_height
        #print "sage_angle", stage_angle
        #print "stage_extension", stage_extension
        #print "line_offset_angle", line_offset_angle
        #print "line_offset_height", line_offset_height

        angle1 = to_rad(to_float(stage_angle))
        angle2 = to_rad(to_float(line_offset_angle))
        angle3 = angle1 + angle2

        # Point 0 co-ordinates
        p0_z = to_float(settings.Z_MM_WHITE_BEAM) + to_float(stage_height)
        p0_x = to_float(settings.X_MM_CP_CENTER)

        # Point 1 co-ordinates
        p1_z = p0_z + math.cos(angle1) * to_float(line_offset_height)
        p1_x = p0_x - math.sin(angle1) * to_float(line_offset_height)

        # Point 2 co-ordinates
        p2_z = p1_z - math.sin(angle1) * to_float(stage_extension)
        p2_x = p1_x - math.cos(angle1) * to_float(stage_extension)

        # Point 3 co-ordinates
        p3_z = p2_z - math.sin(angle3) * to_float(CAM_POS_RENDER_LENGTH)
        p3_x = p2_x - math.cos(angle3) * to_float(CAM_POS_RENDER_LENGTH)

        return p2_x, p2_z, p3_x, p3_z

    def compute_positions(self, pv_name):

        if not self._enabled : return

        # print "camera positioner compute positions called (%s)" % pv_name

        angle = self.monitor.get_value(PV.CUR_ANGLE)
        height = self.monitor.get_value(PV.CUR_HEIGHT)
        extension = self.monitor.get_value(PV.CUR_EXTENSION)

        laser_height = self.monitor.get_value(VAR.CFG_LASER_OFFSET)
        laser_angle = self.monitor.get_value(VAR.CFG_LASER_ANGLE)

        detector_height = self.monitor.get_value(VAR.CFG_DETECTOR_OFFSET)
        detector_angle = self.monitor.get_value(VAR.CFG_DETECTOR_ANGLE)

        # Actual laser position
        try:
            # print "Compute actual laser position ::::::::::"
            sx, sz, ex, ez = self.compute_line_position(height, angle, extension,
                laser_height, laser_angle)

            self.monitor.put(VAR.LASER_ACTUAL, (sx, sz, ex, ez))
        except Exception, e:
            print "Compute actual laser position: FAILED", str(e)

        # Actual detector position
        try:
            # print "Compute actual detector position ::::::::::"
            sx, sz, ex, ez = self.compute_line_position(height, angle, extension,
                detector_height, detector_angle)

            self.monitor.put(VAR.DETECTOR_ACTUAL, (sx, sz, ex, ez))
        except Exception, e:
            print "Compute actual detector position: FAILED", str(e)

        angle = self.monitor.get_value(VAR.CUR_ANGLE)
        height = self.monitor.get_value(VAR.CUR_HEIGHT)

        # Get the proposed extension from the configuration
        extension = self.monitor.get_value(VAR.CFG_EXTENSION)
        self.monitor.put(VAR.CUR_EXTENSION, extension)

        # Proposed laser position
        try:
            # print "Compute proposed laser position ::::::::::"
            sx, sz, ex, ez = self.compute_line_position(height, angle, extension,
                laser_height, laser_angle)

            self.monitor.put(VAR.LASER_PROPOSED, (sx, sz, ex, ez))
        except Exception, e:
            print "Compute proposed laser position: FAILED", str(e)

        # Proposed detector position
        try:
            # print "Compute proposed detector position ::::::::::"
            sx, sz, ex, ez = self.compute_line_position(height, angle, extension,
                detector_height, detector_angle)

            self.monitor.put(VAR.DETECTOR_PROPOSED, (sx, sz, ex, ez))

        except Exception, e:
            print "Compute proposed detector position: FAILED", str(e)

    def terminate(self):
        self._terminate_flag = True
        self.monitor.disconnect(self)

