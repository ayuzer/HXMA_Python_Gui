# System imports
import time
import sys
import random
import threading

from utils.monitor import EpicsMonitor
from utils import to_float

from camera_positioner import PV as PV
from optics_table import PV as PV_OT

# Library imports
from PyQt4.QtGui import QApplication

TIMER_INTERVAL_SEC = 0.5

class Simulator(object):
    """
    A simple simulator for the BMIT Camera Positioner
    """
    def __init__(self):

        self.monitor = EpicsMonitor()

        pv_dict = PV.items()
        pv_names = [value for value in pv_dict.itervalues()]

        pv_dict = PV_OT.items()
        pv_names_ot = [value for value in pv_dict.itervalues()]

        pv_names.extend(pv_names_ot)

        for pv_name in pv_names:

            if not pv_name.startswith('breem'):
                self.log("skipping PV '%s'" % pv_name)
                continue

            self.log("Adding PV: %s" % pv_name)
            self.monitor.add(pv_name)
            self.monitor.connect(pv_name, self.pv_logger)

        # self.monitor.connect(PV.SET_HEIGHT,      self.handle_PV_SET_HEIGHT)
        # self.monitor.connect(PV.SET_ANGLE,       self.handle_PV_SET_ANGLE)
        # self.monitor.connect(PV.SET_EXTENSION,   self.handle_PV_SET_EXTENSION)
        self.monitor.connect(PV.STOP,           self.handle_PV_STOP)
        self.monitor.connect(PV.KILL,           self.handle_PV_STOP)
        self.monitor.connect(PV.MOVE,           self.handle_PV_MOVE)

        self.monitor.connect(PV_OT.MOVE,        self.handle_PV_OT_MOVE)
        self.monitor.connect(PV_OT.STOP_VERT,   self.handle_PV_STOP)
        self.monitor.connect(PV_OT.STOP_TILT,   self.handle_PV_STOP)

        self.timer_action_list = []
        self.timer_lock = threading.Lock()
        self.timer_object = threading.Timer(1, lambda : self.handle_timer())
        self.timer_object.start()

        self.monitor.start()

    def handle_timer(self):

        while True:
            # self.log("timer running")
            time.sleep(TIMER_INTERVAL_SEC)

            self.timer_lock.acquire()

            done_list = []

            for item in self.timer_action_list:
                # print "process item:", item

                target_pv = item[0]
                target_value = item[1]
                step_size = item[2]

                current_value = to_float(self.monitor.get_value(target_pv, 0))
                new_value = current_value + step_size

                if step_size < 0:
                    if new_value <= target_value:
                        done_list.append(item)
                        new_value = target_value
                else:
                    if new_value >= target_value:
                        done_list.append(item)
                        new_value = target_value

                self.monitor.put(target_pv, new_value)

            self.timer_action_list = [item for item in self.timer_action_list \
                                      if item not in done_list]
            self.timer_lock.release()

    def log(self, msg):
        print "ID Simulator: %s" % msg

    def put_float(self, pv_name, value, source='unknown'):
        try:
            validated = to_float(value)
            self.monitor.put(pv_name, validated)
            return True

        except Exception, e:
            self.log("Non float value '%s' from %s to %s" % (repr(value), source, pv_name))

        return False

    def handle_PV_MOVE(self, pv_name):
        print "CP SIMULATOR >>>>>>>>>> "
        value = self.monitor.get_value(pv_name)

        if value == 0: return
        self.monitor.put(pv_name, 0)

        target = self.monitor.get_value(PV.SET_HEIGHT, 0)
        try:
            self.timer_add_action(PV.CUR_HEIGHT, target, 10)
        except Exception, e:
            print "Exception handling PV %s: %s" %(pv_name, str(e))

        target = self.monitor.get_value(PV.SET_EXTENSION, 0)
        try:
            self.timer_add_action(PV.CUR_EXTENSION, target, 10)
        except Exception, e:
            print "Exception handling PV %s: %s" %(pv_name, str(e))

        target = self.monitor.get_value(PV.SET_ANGLE, 0)
        try:
            self.timer_add_action(PV.CUR_ANGLE, target, 10)
        except Exception, e:
            print "Exception handling PV %s: %s" %(pv_name, str(e))

    def handle_PV_OT_MOVE(self, pv_name):
        print "OT SIMULATOR >>>>>>>>>> "
        value = self.monitor.get_value(pv_name)

        if value == 0: return
        self.monitor.put(pv_name, 0)

        target = self.monitor.get_value(PV_OT.SET_HEIGHT, 0)
        try:
            self.timer_add_action(PV_OT.ACT_HEIGHT, target, 10)
        except Exception, e:
            print "Exception handling PV %s: %s" %(pv_name, str(e))

        target = self.monitor.get_value(PV_OT.SET_ANGLE, 0)
        try:
            self.timer_add_action(PV_OT.ACT_ANGLE, target, 10)
        except Exception, e:
            print "Exception handling PV %s: %s" %(pv_name, str(e))

    def handle_PV_STOP(self, pv_name):

        value = self.monitor.get_value(pv_name, 0)
        if value == 0: return
        self.monitor.put(pv_name, 0)

        self.timer_action_list_clear()
        self.put_status("STOP/KILL BUTTON CLICKED")

    def put_status(self, msg):
        print msg

    def timer_add_action(self, target_pv, target_value, duration_sec):

        print "TIMER ACTION ADD CALLED FOR PV -------->", target_pv, target_value
        current_value = self.monitor.get_value(target_pv)

        diff = to_float(target_value) - (current_value)
        steps = to_float(duration_sec)/ to_float(TIMER_INTERVAL_SEC)
        step_size = diff/steps

        self.timer_lock.acquire()

        # Get rid of any existing entries for this PV
        self.timer_action_list = [item for item in self.timer_action_list \
                                  if item[0] != target_pv]

        self.timer_action_list.append((target_pv, target_value, step_size))
        self.timer_lock.release()

    def pv_logger(self, pv_name):
        value = self.monitor.get_value(pv_name)
        self.log("PV: %s VALUE: %s" % (pv_name, repr(value)))

    def timer_action_list_clear(self):
        self.timer_lock.acquire()
        self.timer_action_list = []
        self.timer_lock.release()

if __name__ == "__main__":

    # The EpicsMonitor replies on Qt signals to operate
    app = QApplication(sys.argv)
    simulator = Simulator()
    sys.exit(app.exec_())

