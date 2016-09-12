# System imports
import random
import math
import threading
import time

# App imports
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant

import settings

class PV(Constant):

    SYSTEM_TIME             = 'WIG1405-01:systemTime'
    CYCLES                  = 'TRG2400:cycles'

class VAR(Constant):

    X_PIXEL             = 'var:x_pixel'
    Y_PIXEL             = 'var:y_pixel'
    STATUS_MSG          = 'var:status_message'
    QUEUE_SIZE          = 'var:queue_size'

class Core(object):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        pvs = PV.items()
        for  pv_name in pvs.itervalues():
            self.monitor.add(pv_name)

        # Add all VARs to the monitor
        vars = VAR.items()
        for var_name in vars.itervalues():
            self.monitor.add(var_name)

        self.monitor.update(VAR.QUEUE_SIZE, 0)

        self._terminate_flag = False
        self._lock = threading.Lock()
        self._queue = []
        self._queue_timer = threading.Timer(1, self.handle_queue_timer)
        self._queue_timer.start()


    def handle_queue_timer(self):

        while True:

            if self._terminate_flag: break

            try:
                self._lock.acquire()
                item = self._queue.pop(0)
            except:
                item = None
            finally:
                queue_size = len(self._queue)
                self._lock.release()

            self.monitor.update(VAR.QUEUE_SIZE, queue_size)
            if queue_size ==  0:
                self.monitor.update(VAR.STATUS_MSG, "Queue empty")

            if not item:
                time.sleep(1)
                continue

            msg = "Processing queue item: %s" % repr(item)
            self.monitor.update(VAR.STATUS_MSG, msg)

            for _ in xrange(2):
                time.sleep(1)
                if self._terminate_flag:
                    break

    def queue_item(self, item):

        try:
            self._lock.acquire()
            self._queue.append(item)

        finally:
            queue_size = len(self._queue)
            self._lock.release()

        self.monitor.update(VAR.QUEUE_SIZE, queue_size)

    def queue_clear(self):

        try:
            self._lock.acquire()
            self._queue = []

        finally:
            queue_size = len(self._queue)
            self._lock.release()

        self.monitor.update(VAR.QUEUE_SIZE, queue_size)

    def set_status(self, status_msg):
        self.monitor.update(VAR.STATUS_MSG, status_msg)

    def set_pixel_x(self, value):
        self.monitor.update(VAR.X_PIXEL, int(value))

    def set_pixel_y(self, value):
        self.monitor.update(VAR.Y_PIXEL, int(value))

    def terminate(self):
        print "core.terminate called"
        self._terminate_flag = True



