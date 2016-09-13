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


class PV(Constant):

    SYSTEM_TIME             = 'WIG1405-01:systemTime'
    CYCLES                  = 'TRG2400:cycles'

class VAR(Constant):

    # X_PIXEL             = 'var:x_pixel'
    # Y_PIXEL             = 'var:y_pixel'
    STATUS_MSG      = 'var:status_message'
    # QUEUE_SIZE          = 'var:queue_size'

    MOTOR_1_POS     = 'var:motor_1_pos'
    MOTOR_2_POS     = 'var:motor_2_pos'
    MOTOR_3_POS     = 'var:motor_3_pos'
    MOTOR_4_POS     = 'var:motor_4_pos'
    MOTOR_5_POS     = 'var:motor_5_pos'
    MOTOR_6_POS     = 'var:motor_6_pos'

    MOTOR_1_MOVETO  = 'var:motor_1_moveto'
    MOTOR_2_MOVETO  = 'var:motor_2_moveto'
    MOTOR_3_MOVETO = 'var:motor_3_moveto'
    MOTOR_4_MOVETO = 'var:motor_4_moveto'
    MOTOR_5_MOVETO = 'var:motor_5_moveto'
    MOTOR_6_MOVETO = 'var:motor_6_moveto'

    SERVER_ADDRESS  = 'var:server_address'
    SERVER_HOST     = 'var:server_host'
    SERVER_PORT     = 'var:server_port'

motor_0 = ('name',  """Motor pos VAR""","""Motor moveto VAR""")
motor_1 = ('phi',   VAR.MOTOR_1_POS, VAR.MOTOR_1_MOVETO)
motor_2 = ('eta',   VAR.MOTOR_2_POS, VAR.MOTOR_2_MOVETO)
motor_3 = ('name',  VAR.MOTOR_3_POS, VAR.MOTOR_3_MOVETO)
motor_4 = ('name',  VAR.MOTOR_4_POS, VAR.MOTOR_4_MOVETO)
motor_5 = ('name',  VAR.MOTOR_5_POS, VAR.MOTOR_5_MOVETO)
motor_6 = ('name',  VAR.MOTOR_6_POS, VAR.MOTOR_6_MOVETO)

motor_list = [motor_0, motor_1, motor_2, motor_3, motor_4, motor_5, motor_6]
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

    def move_motor(self,motor_num,movetype):
        motor_var = motor_list[motor_num]
        motor_name = motor_var[0]
        self.monitor.update(VAR.STATUS_MSG, "Moving Motor " + motor_name)
        pos = self.check_motor_pos(motor_num)
        moveto = self.monitor.get_value(motor_var[2])
        if movetype == 'Relative':
            SpecMotor.moveRelative(self.SpecMotor_sess, moveto)
            print "Moving motor " + motor_name + " to " + repr(moveto + pos)
        elif movetype == 'Absolute':
            SpecMotor.move(self.SpecMotor_sess, moveto)
            print "Moving motor " + motor_name + " to " + repr(moveto)
        else:
            print "Move command FAILED"

    def set_motor_moveto(self,value,motor_num):
        motor_var = motor_list[motor_num]
        self.monitor.update(motor_var[2], int(value))

    def check_motor_pos(self,motor_num):
        motor_var = motor_list[motor_num]
        motor_name = motor_var[0]
        self.init()
        SpecMotor.connectToSpec(self.SpecMotor_sess, motor_name, self.monitor.get_value(VAR.SERVER_ADDRESS))
        pos = SpecMotor.getPosition(self.SpecMotor_sess)
        self.monitor.update(motor_var[1], pos)
        print repr(self.monitor.get_value(motor_var[1]))
        return pos

    def checkpos_motor_all(self):
        try:
            for i in range(1,len(motor_list)): #simply sending all of the "motor_num"s to the check pos command
                self.check_motor_pos(i)
            return True
        except:
            return False
    def move_motor_all(self):
        for i in range(1,len(motor_list)):  # simply sending all of the "motor_num"s to the check pos command
            self.move_motor(i)

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



