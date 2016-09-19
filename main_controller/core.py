# System imports
import random
import math
import threading
import time

from numpy import array_equal

from functools import partial

# App imports
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant

import SpecClient.SpecMotor as SpecMotor_module
from SpecClient.SpecMotor import SpecMotorA as SpecMotor
from SpecClient.Spec import Spec
from SpecClient.SpecCounter_toki import SpecCounter as SpecCounter
from SpecClient.SpecClientError import SpecClientError

from SpecClient.SpecScan_toki import SpecScanA as SpecScan

from SpecDataConnection import SpecDataConnection

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

    COUNT_TIME      = 'var:count_time'

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
        # self._lock = threading.Lock()
        # self._queue = []
        # self._queue_timer = threading.Timer(1, self.handle_queue_timer)
        # self._queue_timer.start()

        self._counter_timer = threading.Timer(1, self.handle_counter)
        self._counter_timer.start()
        self.count = False
        self.count_event = threading.Event()
        self.count_event.clear()

        self.move_event = threading.Event()
        self.move_event.set()

        self._scan_timer = threading.Timer(1, self.handle_scan)
        self._scan_timer.start()
        self.scan_event = threading.Event()
        self.scan_event.clear()

        self.Spec_sess = Spec()
        self.SpecMotor_sess = SpecMotor()
        self.SpecScan_sess = SpecScan()

        self.SpecMotor_sess.state = SpecMotor_module.NOTINITIALIZED


    def init_motor_thread(self, motors):
        for i in range(len(motors)):
            motor_inst = motors[i]
            if motor_inst.Enabled:
                self.move_thread = threading.Thread(group=None, target=self.handle_motor_moving_thread, name=None,
                                                    args=(motor_inst, i))
                self.move_thread.start()
    def handle_motor_moving_thread(self, motor, id):
        moved = False  # initializing variable which gets checked before assigned on first loop
        _SpecMotor_sess = SpecMotor()
        while True:
            self.move_event.wait()
            if self._terminate_flag: break
            if _SpecMotor_sess.specName == motor.Mne:
                '''
                moving = inst_self['state'] in [SpecMotor_module.MOVING, SpecMotor_module.MOVESTARTED]
                if moving:  # this doesnt seem to work because it doesnt properly register when the motor is moving
                # I believe this issue is with SpecClient and not with my code...
                '''
                motor_check = self.checkpos_motor(motor, False)
                if moved:
                    time.sleep(0.33)
                    print motor.Name + " is moving"
                else:
                    time.sleep(1)
                moved = motor_check['moved']
                pos = motor_check['pos']
                if moved:
                    print motor.Name + " has moved to " + repr(pos)
            else:  # making sure we're looking at the right motor
                time.sleep(1)
                SpecMotor.connectToSpec(_SpecMotor_sess, motor.Mne, self.monitor.get_value(VAR.SERVER_ADDRESS))

    def init_Spec(self):
        # starting up the Spec server, completed in main_window as monitor needs to load
        Spec.connectToSpec(self.Spec_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))

    def motor_track_state(self,state):
        if state:  # If the checkbox is clicked
            self.move_event.set()
        else:  # Disable movecheck
            self.move_event.clear()


    def move_motor(self, motor):
        motor_name = motor.Mne
        self.monitor.update(VAR.STATUS_MSG, "Moving Motor " + motor.Name)
        if motor.Enabled:
            motor_check = self.checkpos_motor(motor)  # This sets the motor to the correct Mne as well
            pos = motor_check['pos']
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
        else:
            print "Cannot Move non-enabled motor"

    def checkpos_motor(self, motor, print_val = True):
        if self.SpecMotor_sess.specName == motor.Mne:
            pass
        else:
            SpecMotor.connectToSpec(self.SpecMotor_sess, motor.Mne, self.monitor.get_value(VAR.SERVER_ADDRESS))
        try:
            init_pos = self.monitor.get_value(motor.Pos_VAR)
            pos = SpecMotor.getPosition(self.SpecMotor_sess)
            moved = not (init_pos == pos)
            if moved:  # this is where you can hook if motors are moving or not
                self.monitor.update(motor.Pos_VAR, pos)
                if print_val:
                    print repr(self.monitor.get_value(motor.Pos_VAR))
        except SpecClientError as e:
            print repr(e) + ' unconfig = Motor Name: ' + motor.Name
            pos = 'None'
        return {'pos': pos, 'moved': moved}

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
            self.count_event.wait()
            if self._terminate_flag: break
            i = i + 1
            print i
            count_time = SpecCounter.count(self.SpecCounter_sec, self.count_time_set_SB.value())
            self.monitor.update(VAR.COUNT_TIME, count_time)
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

    def counting_state(self, state, spinBox_counter):
        self.count_time_set_SB = spinBox_counter
        if state:  #Enable Counting
            self.count_state = True
            self.count_event.set()
        else:  # Disable Counting
            self.count_event.clear()

    def is_scanning(self, button=None):
        if button == None:
            try:
                button = self.saved_button
            except UnboundLocalError:
                pass
        else:
            self.saved_button = button
        if self.SpecScan_sess.scanning:  # This property is checked, so functions here will work
            button.setText('Stop')
        else:
            button.setText('Start')
        return self.SpecScan_sess.scanning

    def scan_start(self, scantype, motor_name, startpos, endpos, intervals, count_time, Motors):
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Name == motor_name:
                if Motor_inst.Enabled:
                    SpecScan.connectToSpec(self.SpecScan_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))
                    SpecScan.newScan(self.SpecScan_sess, True)
                    if scantype:
                        checkpos = self.checkpos_motor(Motor_inst, False)
                        pos = checkpos['pos']
                        relstartpos = startpos - pos
                        relendpos = endpos - pos
                        SpecScan.dscan(self.SpecScan_sess, Motor_inst.Mne, relstartpos, relendpos, intervals, count_time)
                    else:
                        SpecScan.ascan(self.SpecScan_sess, Motor_inst.Mne, startpos, endpos, intervals, count_time)
                    self.scan_event.set()
                else:
                    raise Exception('Scan cannot be started as the motor was not Enabled')
            else:
                pass
        print "Scan Started"

        return True  # Saying the scan is started
    def handle_scan(self):
        #Thread which handles scan data
        self.scan_event.wait()
        self.scan_data = []  # Initalizing empty array
        while True:
            self.scan_event.wait()
            if self._terminate_flag: break
            while self.is_scanning():
                if self._terminate_flag: break
                old_scan = self.scan_data
                self.scan_data = SpecScan.get_SCAN_D(self.SpecScan_sess)
                if array_equal(old_scan, self.scan_data):
                    time.sleep(1)
                else:  # here is where you would graph it/save it to the csv
                    print self.scan_data
            time.sleep(5)

    def scan_stop(self):
        SpecScan.abort(self.SpecScan_sess)
        self.scan_event.clear()
        print "Scan Stopped"
        return False  # Saying the scan is stopped

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
        self.count_event.set()  # allow any blocked threads to terminate
        self.move_event.set()
        self.scan_event.set()
        self.scan_stop()