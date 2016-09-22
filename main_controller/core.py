# System imports
import random
import math
import threading
import time
import json
import operator
import csv
import time
import os

import numpy as np

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
    STATUS_MSG          = 'var:status_message'

    MOTOR_1_POS         = 'var:motor_1_pos'
    MOTOR_2_POS         = 'var:motor_2_pos'
    MOTOR_3_POS         = 'var:motor_3_pos'
    MOTOR_4_POS         = 'var:motor_4_pos'
    MOTOR_5_POS         = 'var:motor_5_pos'
    MOTOR_6_POS         = 'var:motor_6_pos'

    SCAN_ARRAY          = 'var:scan_array'
    SCAN_MAX_Y          = 'var:scan_max_y'
    SCAN_FWHM           = 'var:scan_FWHM'
    SCAN_COM            = 'var:scan_COM'
    SCAN_CWHM           = 'var:scan_CWHM'
    SCAN_CENTROID       = 'var:scan_centroid'

    COUNTER_1_COUNT     = 'var:counter_1_count'
    COUNTER_2_COUNT     = 'var:counter_2_count'
    COUNT_TIME          = 'var:count_time'

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

        self.scan_array = self.old_x = self.old_y = self.old_array= []


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
            if self.checkpos_motor(motor)['moved']:  # This sets the motor to the correct Mne as well as checking if its moving
                SpecMotor.stop(self.SpecMotor_sess)
                print motor.Name + " has been stopped"
            else:
                print motor.Name + " does not appear to be moving"
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
            self.update_scan_CB(self.x_data_CB, self.y_data_CB)
        else:
            button.setText('Start')
            self.backup_scan()
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

    def update_scan_CB(self, x_data_CB, y_data_CB):
        self.x_data_CB = x_data_CB
        self.y_data_CB = y_data_CB
        self.scanner_names = self.get_var('SCAN_COLS')
        i=0
        (x_index, y_index) = x_data_CB.currentIndex(), y_data_CB.currentIndex()
        x_data_CB.clear()
        y_data_CB.clear()
        for i in range(len(self.scanner_names)):
            x_data_CB.addItem(self.scanner_names[str(i)])
            y_data_CB.addItem(self.scanner_names[str(i)])
        #print scanner_names
        x_data_CB.setCurrentIndex(x_index)
        y_data_CB.setCurrentIndex(y_index)

    def get_data(self, x_index, y_index):
        data = self.monitor.get_value(VAR.SCAN_ARRAY)
        if data is None:
            return False, [], []
        else:
            (x,y) = [point[x_index] for point in data], [point[y_index] for point in data]
            return True, x, y

    def scan_calculations(self, x, y):
        if not self.old_x == x or not self.old_y == y:
            calc = Calculation(x, y)
            self.monitor.update(VAR.SCAN_MAX_Y, calc.y_max_string())
            self.monitor.update(VAR.SCAN_FWHM, calc.FWHM())
            self.monitor.update(VAR.SCAN_COM, calc.COM())
            self.monitor.update(VAR.SCAN_CWHM, calc.CFWHM())
            self.monitor.update(VAR.SCAN_CENTROID, calc.Centroid())
        (self.old_x, self.old_y) = x, y

    def save_scan_curr(self, filename, x_CB, y_CB):
        filedir = self.scan_dir
        go, x, y = self.get_data(x_CB.currentIndex(), y_CB.currentIndex())
        if go:
            curr_time = time.strftime("%b_%d_%Y_%H-%M-%S")  # getting time also so we wont have name conflicts
            with open(filedir+'/'+filename+'_'+curr_time+".csv", 'wb') as csvfile:
                header = [str(x_CB.currentText()), str(y_CB.currentText())]
                writer = csv.writer(csvfile)
                writer.writerow(header)
                for i in range(len(x)):
                    writer.writerow([x[i], y[i]])
                writer.writerow(["Max Y", "FWHM", "CWHM", "COM", "Centroid"])
                writer.writerow([self.monitor.get_value(VAR.SCAN_MAX_Y),
                                 self.monitor.get_value(VAR.SCAN_FWHM),
                                 self.monitor.get_value(VAR.SCAN_CWHM),
                                 self.monitor.get_value(VAR.SCAN_COM),
                                 self.monitor.get_value(VAR.SCAN_CENTROID),
                                 ])
                print "Successfully saved " + filename+'_'+curr_time+".csv" + " In : " + filedir
        else:
            print "Cannot Write, No data acquired"

    def backup_scan(self):
        if not self.old_array == self.scan_array:
            self.old_array = self.scan_array
            back_dir = self.scan_dir+'/backup'
            if not os.path.exists(back_dir):
                os.makedirs(back_dir)
                print "Backup directory in " + back_dir + "\nhas been created"
            if self.scan_array and self.scanner_names:
                curr_time = time.strftime("%b_%d_%Y_%H-%M-%S")  # getting time also so we wont have name conflicts
                with open(back_dir + '/' + "BACKUP" + '_' + curr_time + ".csv", 'wb') as csvfile:
                    writer = csv.writer(csvfile)
                    header = []
                    for k in range(len(self.scanner_names)):
                        header.append(self.scanner_names[str(k)])
                    writer.writerow(header)
                    for i in range(len(self.scan_array)):
                        scan_row = self.scan_array[i]
                        row = []
                        for j in range(len(scan_row)):
                            row.append(scan_row[j])
                        writer.writerow(row)
                    print "Backup csv has been created in " + repr(csvfile)


    def update_scan_filepath(self, filepath):
        self.scan_dir = filepath

    """ RANDOM UTILITIES """
    def get_var(self, var_name):
        """Return variable"""
        if self.Spec_sess.connection is not None:
            c = self.Spec_sess.connection.getChannel('var/'+var_name)
            return c.read()

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
        self._terminate_flag = True
        print "core.terminate called"
        sess_list = [self.SpecMotor_sess,
                           self.SpecCounter_ic2,
                           self.SpecCounter_pinf,
                           self.SpecScan_sess,
                           self.SpecScan_sess,
                           ]
        for sess in sess_list:
            self.term_sess(sess)
        self.count_event.set()  # allow any blocked threads to terminate
        self.move_event.set()
        self.scan_event.set()
        self.scan_stop()

    def term_sess(self, sess):
        connection = sess.connection
        try:
            sess.stop()
        except Exception, e:
            print repr(e)
        if connection is not None:
            connection.dispatcher.disconnect()
        else:
            print repr(connection) + " was not initialized and hence was not closed"


class Calculation:

    def __init__(self, x, y):
        (self.x, self.y) = x, y

    def y_max_full(self):
        i, y_val = max(enumerate(self.y), key=operator.itemgetter(1))
        x_at_y_max = self.x[i]
        return y_val, x_at_y_max

    def y_max(self):
        (y_max, unused) = self.y_max_full()
        return y_max

    def y_max_string(self):
        (y_max, x_val) = self.y_max_full()
        return " " + "{:.2f}".format(y_max) + "\n@" + r"{:.2f}".format(x_val)

    def FWHM_full(self):
        # modified from http://stackoverflow.com/a/16489955 second comment
        zeroed_y = np.array(self.y) - min(self.y)
        diff = zeroed_y - ((self.y_max()- min(self.y))/ 2)
        indexes = np.where(diff > 0)[0]
        try :
            return np.array(self.x)[indexes[-1]], np.array(self.x)[indexes[0]], abs(np.array(self.x)[indexes[-1]] - np.array(self.x)[indexes[0]])
        except IndexError:
            return 0, 0, 0

    def FWHM(self):
        (bound_1, bound_2, FWHM) = self.FWHM_full()
        return FWHM

    def CFWHM(self):
        (bound_1, bound_2, FWHM) = self.FWHM_full()
        return (bound_1+bound_2)/2

    def COM(self):
        try:
            return np.average(self.x, weights=self.y)
        except ZeroDivisionError:
            return 0

    def Centroid(self):
        x_y=[]
        x_step=[]
        steps=[]
        for i in range(len(self.x)):
            pos = self.x[i]
            intes = self.y[i]
            x_y.append(pos*intes)
            try:
                step = abs(self.x[i+1] - self.x[i])
            except IndexError:
                step = abs(self.x[i] - self.x[i-1])
            steps.append(step)
            x_step.append(step*intes)
        step = np.average(steps)
        return (step*np.sum(x_y))/(np.sum(x_step))


