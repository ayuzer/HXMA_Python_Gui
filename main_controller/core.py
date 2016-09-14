# System imports
import random
import math
import threading
import time

from functools import partial

# App imports
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant

import SpecClient.SpecMotor as SpecMotor_module
from SpecClient.SpecMotor import SpecMotorA as SpecMotor
from SpecClient.Spec import Spec
from SpecClient.SpecCounter_toki import SpecCounter as SpecCounter
from SpecClient.SpecClientError import SpecClientError
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

    COUNTER_1_COUNT = 'var:counter_1_count'
    COUNTER_2_COUNT = 'var:counter_2_count'

    SERVER_ADDRESS  = 'var:server_address'
    SERVER_HOST     = 'var:server_host'
    SERVER_PORT     = 'var:server_port'

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

        self._counter_timer = threading.Timer(.25, self.handle_counter)
        self._counter_timer.start()
        self.count = False

        self.Spec_sess = Spec()
        self.SpecMotor_sess = SpecMotor()

        self.SpecMotor_sess.state = SpecMotor_module.NOTINITIALIZED

    def init_Spec(self):
        # starting up the Spec server, completed in main_window as monitor needs to load
        Spec.connectToSpec(self.Spec_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))

    def motorStateChanged(self, state):
        self.state = state
        if self.state in [SpecMotor_module.MOVING, SpecMotor_module.MOVESTARTED]:
            print "MOVING"
        elif self.state in [SpecMotor_module.UNUSABLE, SpecMotor_module.NOTINITIALIZED]:
            print "NOT WORKING"
        elif self.state in [SpecMotor_module.READY, SpecMotor_module.ONLIMIT]:
            print "READY"

    def move_motor(self, motor):
        motor_name = motor.Mne
        self.monitor.update(VAR.STATUS_MSG, "Moving Motor " + motor.Name)
        if motor.Enabled:
            pos = self.checkpos_motor(motor) # This sets the motor to the correct Mne as well
            moveto = motor.Moveto_SB.value()
            movetype = motor.MoveType_CB.currentText()
            if movetype == 'Relative':
                SpecMotor.moveRelative(self.SpecMotor_sess, moveto)
                print "Moving motor " + motor.Name + " to " + repr(moveto + pos)
            elif movetype == 'Absolute':
                SpecMotor.move(self.SpecMotor_sess, moveto)
                print "Moving motor " + motor_name + " to " + repr(moveto)
            else:
                print "Move command FAILED:  INVESTIGATE"
                print movetype
                print moveto
            self.move_thread = threading.Timer(0.1, partial(self.handle_motor_moving_thread, motor))
            self.move_thread.start()
        else:
            print "Cannot Move non-enabled motor"

    def handle_motor_moving_thread(self, motor):
        self.SpecMotor_sess.moving = True
        while self.SpecMotor_sess.moving:
            if self.SpecMotor_sess.specName == motor.Mne:
                self.SpecMotor_sess.moving = self.SpecMotor_sess.motorState in [SpecMotor_module.MOVING, SpecMotor_module.MOVESTARTED]
                time.sleep(0.1)
                self.checkpos_motor(motor)
            else:# making sure we're looking at the right motor
                SpecMotor.connectToSpec(self.SpecMotor_sess, motor.Mne, self.monitor.get_value(VAR.SERVER_ADDRESS))
                time.sleep(1)
            if self._terminate_flag: break
        time.sleep(2)
        self.checkpos_motor(motor)

    def checkpos_motor(self, motor):
        if self.SpecMotor_sess.specName == motor.Mne:
            pass
        else:
            SpecMotor.connectToSpec(self.SpecMotor_sess, motor.Mne, self.monitor.get_value(VAR.SERVER_ADDRESS))
        try:
            pos = SpecMotor.getPosition(self.SpecMotor_sess)
        except SpecClientError as e:
            print repr(e) + ' unconfig = Motor Name: ' + motor.Name
            pos = 'None'
        if isinstance(pos, basestring) ==  True:
            pass
        else:
            self.monitor.update(motor.Pos_VAR, pos)
            print repr(self.monitor.get_value(motor.Pos_VAR))
        return pos

    def move_motor_all(self):
        for i in range(1,len(motor_list)):  # simply sending all of the "motor_num"s to the check pos command
            self.move_motor(i)

    def handle_counter(self):
        address = self.monitor.get_value(VAR.SERVER_ADDRESS) #Just initalizing the counter classes which we'll read
        self.SpecCounter_ic2 = SpecCounter()
        self.SpecCounter_pinf = SpecCounter()
        self.SpecCounter_sec = SpecCounter()
        SpecCounter.connectToSpec(self.SpecCounter_ic2, 'ic2', address)
        SpecCounter.connectToSpec(self.SpecCounter_pinf, 'pinf', address)
        SpecCounter.connectToSpec(self.SpecCounter_sec, 'sec', address)
        i=0
        while True:
            i = i+1
            print i
            if self._terminate_flag: break
            count_time = SpecCounter.count(self.SpecCounter_sec, 5)
            if self.count:
                self.monitor.update(VAR.COUNTER_1_COUNT, SpecCounter.getValue(self.SpecCounter_ic2))
                self.monitor.update(VAR.COUNTER_2_COUNT, SpecCounter.getValue(self.SpecCounter_pinf))
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

    def start_count(self):
        self.count = True
        print "COUNT STARTED"

    def stop_count(self):
        self.count = False
        print "COUNT STOPPED"

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



