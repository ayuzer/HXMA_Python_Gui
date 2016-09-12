# System imports
import random
import math
import threading
import time

# App imports
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant

from SpecClient.SpecMotor import SpecMotor
from SpecClient.Spec import Spec

import settings

motor_dict = {'one':'phi','two':''}

class PV(Constant):

    SYSTEM_TIME             = 'WIG1405-01:systemTime'
    CYCLES                  = 'TRG2400:cycles'

class VAR(Constant):

    # X_PIXEL             = 'var:x_pixel'
    # Y_PIXEL             = 'var:y_pixel'
    STATUS_MSG          = 'var:status_message'
    # QUEUE_SIZE          = 'var:queue_size'

    MOTOR_ONE_POS       = 'var:motor_one_pos'
    MOTOR_TWO_POS       = 'var:motor_two_pos'

    MOTOR_ONE_MOVETO    = 'var:motor_one_moveto'
    MOTOR_TWO_MOVETO    = 'var:motor_two_moveto'

    SERVER_ADDRESS      = 'var:server_address'
    SERVER_HOST         = 'var:server_host'
    SERVER_PORT         = 'var:server_port'


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

        # self.monitor.update(VAR.QUEUE_SIZE, 0)

        self._terminate_flag = False
        self._lock = threading.Lock()
        # self._queue = []
        # self._queue_timer = threading.Timer(1, self.handle_queue_timer)
        # self._queue_timer.start()

        self.Spec_sess = Spec()
        self.SpecMotor_sess = SpecMotor()
        self.SpecMotor_init = False

    def init(self):
        if self.SpecMotor_init == False:
            # starting up the Spec server
            Spec.connectToSpec(self.Spec_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))
            self.SpecMotor_init = True
        else:
            pass

    def move_motor(self,motor_num):
        motor_name = motor_dict[motor_num]
        self.monitor.update(VAR.STATUS_MSG, "Moving Motor " + motor_name)
        self.check_motor_pos(motor_num)
        if motor_num == 'one':
            moveto = self.monitor.get_value(VAR.MOTOR_ONE_MOVETO)
        elif motor_num == 'two':
            moveto = self.monitor.update(VAR.MOTOR_TWO_MOVETO)
            print repr(self.monitor.get_value(VAR.MOTOR_TWO_POS))
        else:
            pass
        print "moving motor " + motor_name + " up " + repr(moveto)
        SpecMotor.moveRelative(self.SpecMotor_sess,moveto)

    def set_motor_moveto(self,value,motor_num):
        if motor_num == 'one':
            self.monitor.update(VAR.MOTOR_ONE_MOVETO, int(value))
        elif motor_num == 'two':
            self.monitor.update(VAR.MOTOR_TWO_MOVETO, int(value))

    def check_motor_pos(self,motor_num):
        motor_name = motor_dict[motor_num]
        self.init()
        SpecMotor.connectToSpec(self.SpecMotor_sess, motor_name, self.monitor.get_value(VAR.SERVER_ADDRESS))
        pos = SpecMotor.getPosition(self.SpecMotor_sess)
        if motor_num == 'one':
            self.monitor.update(VAR.MOTOR_ONE_POS, pos)
            print repr(self.monitor.get_value(VAR.MOTOR_ONE_POS))
        elif motor_num == 'two':
            self.monitor.update(VAR.MOTOR_TWO_POS, pos)
            print repr(self.monitor.get_value(VAR.MOTOR_TWO_POS))
        else:
            pass

    # def handle_queue_timer(self):
    #
    #     while True:
    #
    #         if self._terminate_flag: break
    #
    #         try:
    #             self._lock.acquire()
    #             item = self._queue.pop(0)
    #         except:
    #             item = None
    #         finally:
    #             queue_size = len(self._queue)
    #             self._lock.release()
    #
    #         self.monitor.update(VAR.QUEUE_SIZE, queue_size)
    #         if queue_size ==  0:
    #             self.monitor.update(VAR.STATUS_MSG, "Queue empty")
    #
    #         if not item:
    #             time.sleep(1)
    #             continue
    #
    #         msg = "Processing queue item: %s" % repr(item)
    #         self.monitor.update(VAR.STATUS_MSG, msg)
    #
    #         for _ in xrange(2):
    #             time.sleep(1)
    #             if self._terminate_flag:
    #                 break
    #
    # def queue_item(self, item):
    #
    #     try:
    #         self._lock.acquire()
    #         self._queue.append(item)
    #
    #     finally:
    #         queue_size = len(self._queue)
    #         self._lock.release()
    #
    #     self.monitor.update(VAR.QUEUE_SIZE, queue_size)
    #
    # def queue_clear(self):
    #
    #     try:
    #         self._lock.acquire()
    #         self._queue = []
    #
    #     finally:
    #         queue_size = len(self._queue)
    #         self._lock.release()
    #
    #     self.monitor.update(VAR.QUEUE_SIZE, queue_size)
    #
    def set_status(self, status_msg):
        self.monitor.update(VAR.STATUS_MSG, status_msg)

    def set_server(self):
        """Right now this is simply a placeholder function for an interactive set server
        This is awful -----------------------------RECODE THIS!!!!-------------------
        """
        self.monitor.update(VAR.SERVER_HOST, '10.52.36.1')
        self.monitor.update(VAR.SERVER_PORT, '8585')
        self.monitor.update(VAR.SERVER_ADDRESS, ''.join((self.monitor.get_value(VAR.SERVER_HOST), ':', self.monitor.get_value(VAR.SERVER_PORT))))

    def terminate(self):
        print "core.terminate called"
        self._terminate_flag = True



