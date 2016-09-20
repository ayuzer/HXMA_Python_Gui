# System imports
import random
import math
import threading
import time
import json

from numpy import array_equal

from functools import partial

# App imports
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant
from utils import graph

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

    SCAN_ARRAY      = 'var:scan_array'

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

        self._terminate_flag = False

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

        self.scan_array = []


    """ MOTOR """
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

    def motor_stop(self, motor):
        if motor.Enabled:
            self.checkpos_motor(motor)  # This sets the motor to the correct Mne as well
            SpecMotor.stop(self.SpecMotor_sess)
            print motor.Name + " has been stopped"
        else:
            print "Cannot stop a disabled motor"

    def checkpos_motor(self, motor, print_val=True):
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

    def motor_track_state(self, state):
        if state:  # If the checkbox is clicked
            self.move_event.set()
        else:  # Disable movecheck
            self.move_event.clear()

    def check_limits(self, motor):
        self.checkpos_motor(motor) # check where the motor is and assigning it.
        return SpecMotor.getLimits(self.SpecMotor_sess)

    """ COUNTER """
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

    def counting_state(self, state, spinBox_counter):
        self.count_time_set_SB = spinBox_counter
        if state:  #Enable Counting
            self.count_state = True
            self.count_event.set()
        else:  # Disable Counting
            self.count_event.clear()

    """ SCANNING """

    def is_scanning(self, button=None):
        if button == None:
            try:
                button = self.saved_button
            except UnboundLocalError:
                pass
        else:
            self.saved_button = button
            # This property is checked, so functions here will work
        self.SpecScan_sess.scanning = SpecScan.isScanning(self.SpecScan_sess)
        if self.SpecScan_sess.scanning:
            button.setText('Stop')
        else:
            button.setText('Start')
            #self.scan_event.clear() # stops the scanning thread when the scan isn't running
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
                    self.scan_array = []  # starting/wiping an array for the scan data to push into
                    self.scan_array_counter = 0
                    self.scan_event.set()
                else:
                    raise Exception('Scan cannot be started as the motor was not Enabled')
            else:
                pass
        print "Scan Started"
        return True  # Saying the scan is started

    def handle_scan(self):
        # Thread which handles scan data
        self.scan_event.wait()
        self.scan_data = []  # Initalizing empty arrays
        self.scan_point = []
        while True:
            self.scan_event.wait()
            if self._terminate_flag: break
            # while self.is_scanning():
            while True:
                if self._terminate_flag: break
                old_data = self.scan_data
                old_point = self.scan_point
                #self.scan_data = SpecScan.get_SCAN_D(self.SpecScan_sess)
                try:
                    self.scan_point = json.JSONDecoder.decode(json.JSONDecoder(), SpecScan.get_SCAN_PT(self.SpecScan_sess))
                except ValueError:
                    pass
                #elif array_equal(old_data, self.scan_data):
                if not old_point == self.scan_point: # here is where you would graph it/save it to the csv
                    # print self.scan_data
                    if self.scan_point[0] > self.scan_array_counter:
                        print "Scan point ignored"
                    elif self.scan_point[0] == self.scan_array_counter:
                        self.scan_array.insert(self.scan_point[0], self.scan_point[1])
                        self.scan_array_counter = self.scan_array_counter + 1
                        self.monitor.update(VAR.SCAN_ARRAY,self.scan_array)
                    else:
                        print "Entering data into the scan array has not worked properly"
                    self.scan_SB_sleeper(ratio=0.75, _min=False)
                    pass
                elif not self.is_scanning():
                    self.scan_SB_sleeper()
                else:
                    self.scan_SB_sleeper(ratio=0.5, _min=False)

            self.scan_SB_sleeper()

    def scan_stop(self):
        SpecScan.abort(self.SpecScan_sess)
        self.scan_event.clear()
        print "Scan Stopped"
        return False  # Saying the scan is stopped

    def scan_settings(self, motor_name, startpos_SB, stoppos_SB, Motors, wait_time_SB):
        self.wait_time_SB = wait_time_SB
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Name == motor_name:
                if Motor_inst.Enabled:
                    (min_lim, max_lim) = self.check_limits(Motor_inst)
                    startpos_SB.setRange(min_lim, max_lim)
                    stoppos_SB.setRange(min_lim, max_lim)

    def scan_SB_sleeper(self, default_time=3.0, ratio=1.0, _min=True):
        try:  # Setting wait times to the interval time of the scan's spinbox if it isn't too small
            if self.wait_time_SB.value() > 0.5 or not _min:
                sleep_time = self.wait_time_SB.value() * ratio
            else:
                sleep_time = default_time
        except:
            sleep_time = default_time
        #print "Scanning Thread is sleeping for " + repr(sleep_time)
        time.sleep(sleep_time)

    """ RANDOM UTILITIES """

    def init_Spec(self):
        # starting up the Spec server, completed in main_window as monitor needs to load
        Spec.connectToSpec(self.Spec_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))

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