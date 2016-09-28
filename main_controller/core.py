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

from PyQt4.QtGui import QTableWidgetItem as tableItem
from PyQt4.QtCore import QString as str2q

from SpecDataConnection import SpecDataConnection

import settings


class PV(Constant):

    SYSTEM_TIME         = 'WIG1405-01:systemTime'
    CYCLES              = 'TRG2400:cycles'

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

    CENT_NEG_MAXY       = 'var:cent_neg_maxy'
    CENT_NEG_COM        = 'var:cent_neg_com'
    CENT_NAU_MAXY       = 'var:cent_nau_maxy'
    CENT_NAU_COM        = 'var:cent_nau_com'
    CENT_POS_MAXY       = 'var:cent_pos_maxy'
    CENT_POS_COM        = 'var:cent_pos_com'

    CENT_CENTERED_X     = 'var:cent_centered_x'
    CENT_CENTERED_Y     = 'var:cent_centered_y'

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
        self.check_move_event = threading.Event()
        self.check_move_event.set()
        self._move_terminate_flag = False

        self._scan_timer = threading.Timer(1, self.handle_scan)
        self._scan_timer.start()
        self.scan_event = threading.Event()
        self.scan_event.clear()

        self._cent_timer = threading.Timer(1, self.handle_cent)
        self._cent_timer.start()
        self.cent_event = threading.Event()
        self.cent_event.clear()
        
        self.Spec_sess = Spec()
        self.SpecMotor_sess = SpecMotor()
        self.SpecScan_sess = SpecScan()

        self.SpecMotor_sess.state = SpecMotor_module.NOTINITIALIZED

        self.moving_bool_dict = {}
        self.old_full_array, self.scan_array, self.old_array, self.old_x, self.old_y = ([] for i in range(5))
        self.cent_props = ('', '', 0, 0, 0, 0, 0, [], True)
        self.CB_lock = threading.Lock()


    """ MOTOR """
    def move_motor(self, motor, moveto=None, movetype=None):
        if moveto == None:
            moveto = motor.Moveto_SB.value()
        if movetype == None:
            movetype = motor.MoveType_CB.currentText()
        motor_name = motor.Mne
        self.monitor.update(VAR.STATUS_MSG, "Moving Motor " + motor.Name)
        if motor.Enabled:
            motor_check = self.checkpos_motor(motor)  # This sets the motor to the correct Mne as well
            pos = motor_check['pos']
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
            if self._move_terminate_flag: break
            if self._terminate_flag: break
            self.check_move_event.wait()  # This stops the motors from updating each other's monitors
            if _SpecMotor_sess.specName == motor.Mne:
                '''
                moving = inst_self['state'] in [SpecMotor_module.MOVING, SpecMotor_module.MOVESTARTED]
                if moving:  # this doesnt seem to work because it doesnt properly register when the motor is moving
                # I believe this issue is with SpecClient and not with my code...
                '''
                self.check_move_event.clear()
                motor_check = self.checkpos_motor(motor, False)
                self.check_move_event.set()
                moved = motor_check['moved']
                pos = motor_check['pos']
                if moved:
                    time.sleep(0.33)
                    print motor.Name + " has moved to " + repr(pos)
                else:
                    time.sleep(1)
                try:
                    self.moving_bool_dict[motor.Name] = moved
                except KeyError:
                    self.moving_bool_dict.update({motor.name, moved})
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

    def is_moving(self, motor_name='none'):  # will return if all motors are moving or not unless motor is specified
        if motor_name == 'none':
            return not all(bool==False for bool in self.moving_bool_dict.values())
        else:
            return self.moving_bool_dict[motor_name]

    def update_motors(self, motor_names, Motors, CBs):
        self._move_terminate_flag = False
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Enabled:
                for CB in CBs:
                    CB.addItem(Motor_inst.Name)
                motor_names[i].setText(Motor_inst.Name)
                (min_lim, max_lim) = self.check_limits(Motor_inst)
                Motor_inst.Moveto_SB.setRange(min_lim * 2, max_lim * 2)

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
            # print i
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
            self.update_CB(self.x_scan_data_CB, self.y_scan_data_CB, 'scan')
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
                    if self.scan_point[0] > self.scan_array_counter and self.scan_array_counter == 0: #Skips old point
                        print "Scan point ignored"
                    elif self.scan_point[0] == self.scan_array_counter:
                        self.scan_array.insert(self.scan_point[0], self.scan_point[1])
                        self.scan_array_counter = self.scan_array_counter + 1
                        self.monitor.update(VAR.SCAN_ARRAY, self.scan_array)
                    else:
                        print "Entering data into the scan array has not worked properly \n" \
                              "Scan Counter: " + repr(self.scan_array_counter) + " Scan Point: " + repr(self.scan_point[0])
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
        self.scan_wait_time_SB = wait_time_SB
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Name == motor_name:
                if Motor_inst.Enabled:
                    (min_lim, max_lim) = self.check_limits(Motor_inst)
                    startpos_SB.setRange(min_lim, max_lim)
                    stoppos_SB.setRange(min_lim, max_lim)

    def scan_SB_sleeper(self, default_time=3.0, ratio=1.0, _min=True):
        try:  # Setting wait times to the interval time of the scan's spinbox if it isn't too small
            if self.scan_wait_time_SB.value() > 0.5 or not _min:
                sleep_time = self.wait_time_SB.value() * ratio
            else:
                sleep_time = default_time
        except:
            sleep_time = default_time
        #print "Scanning Thread is sleeping for " + repr(sleep_time)
        time.sleep(sleep_time)

    def get_data(self, x_index, y_index, array='scan_array'):
        if array == 'scan_array':  # if we have not provided an array
            array = self.monitor.get_value(VAR.SCAN_ARRAY)
        if array is None or not array:
            return False, [], []
        else:
            (x, y) = [point[x_index] for point in array], [point[y_index] for point in array]
            return True, x, y

    def scan_calculations(self, x, y):
        calc = Calculation(x, y)
        self.monitor.update(VAR.SCAN_MAX_Y, calc.y_max_string())
        self.monitor.update(VAR.SCAN_FWHM, calc.FWHM())
        self.monitor.update(VAR.SCAN_COM, calc.COM())
        self.monitor.update(VAR.SCAN_CWHM, calc.CFWHM())
        self.monitor.update(VAR.SCAN_CENTROID, calc.Centroid())

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

    """ CENTER """
    def cent_settings(self, scan_motor_name, angle_motor_name, relmax_SB, relmin_SB, center_SB, angle_pm_SB, angle_o_SB, Motors, wait_time_SB, center_calc_CB):
        self.wait_time_SB = wait_time_SB
        center_calc_CB.setMaxCount(2)    # At init we have to do some limit setting/setting up of UI elements
        center_calc_CB.addItem('Max Y')  # we do it here because they are mostly calcs which rely on the motors chosen
        center_calc_CB.addItem('COM')    # This combo box is not one of those though
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Enabled:
                (min_lim, max_lim) = self.check_limits(Motor_inst)
                full_range = abs(min_lim) + abs(max_lim)
                if Motor_inst.Name == scan_motor_name:
                    center_SB.setRange(min_lim, max_lim)
                    relmax_SB.setRange(-1 * full_range, full_range)
                    relmin_SB.setRange(-1 * full_range, full_range)
                elif Motor_inst.Name == angle_motor_name:
                    angle_o_SB.setRange(min_lim, max_lim)
                    angle_pm_SB.setRange(-1 * full_range/2, full_range/2)

    def is_centering(self, start_stop_PB):
        if start_stop_PB == None:
            try:
                start_stop_PB = self.start_stop_PB
            except UnboundLocalError:
                pass
        else:
            self.start_stop_PB = start_stop_PB
            # This property is checked, so functions here will work
        if self.cent_event._Event__flag:
            start_stop_PB.setText('Stop')
            self.update_CB(self.x_cent_data_CB, self.y_cent_data_CB, 'cent')
        else:
            start_stop_PB.setText('Start')
        return self.cent_event._Event__flag

    def cent_stop(self):
        self.cent_event.clear()
        self._teminate_cent = True
        self.is_centering(None)
        if self.is_scanning():
            self.scan_stop()

    def cent_start(self, scan_motor_name, angle_motor_name, relmax, relmin, center, angle_pm, angle_o, steps, waittime, Motors):
        self.angle_pm=angle_pm
        if self.is_centering(self.start_stop_PB):
            self.cent_stop()
        self.cent_props = (scan_motor_name, angle_motor_name, center + relmin, center + relmax,
                            angle_o - angle_pm, angle_o, angle_o + angle_pm, steps, waittime, Motors, False)
        self._teminate_cent = False
        self.cent_started = False
        self.cent_event.set()

    def cent_command_buff(self, wait_condit, command, commandargs, message, command2=None, command2args=None, waitsleep=1, finalsleep=3):
        while wait_condit():
            time.sleep(waitsleep)
        command(*commandargs)
        if not command2 == None:
            command2(*command2args)
        self.set_status(message)
        time.sleep(finalsleep)

    def set_array(self, name, dummy):
        if name == 'neg':
            self.w_neg_array =self.scan_array
        elif name == 'nau':
            self.w_naught_array = self.scan_array
        elif name == 'pos':
            self.w_pos_array = self.scan_array

    def handle_cent(self):
        while True:
            if self._terminate_flag:break
            self.cent_event.wait()
            self.w_neg_array, self.w_naught_array, self.w_pos_array = ([] for i in range(3))
            (scan_motor_name, angle_motor_name, cent_scan_start, cent_scan_stop,
             cent_angle_m, cent_angle_o, cent_angle_p, steps, waittime, Motors, terminate) = self.cent_props
            for i in range(len(Motors)):
                motor_inst = Motors[i]
                if scan_motor_name == motor_inst.Name:
                    scan_motor = motor_inst
                elif angle_motor_name == motor_inst.Name:
                    angle_motor = motor_inst
            if not terminate:
                self.is_centering(None)
                # Each of these blocks are nearly identical, they just tell the motor to go to a position and then scan
                self.cent_command_buff(self.is_moving, self.move_motor, (angle_motor, cent_angle_m, "Absolute"),
                                       "CENTERING: MOVING TO W-", command2=self.move_motor,
                                       command2args=(scan_motor, cent_scan_start, "Absolute"))
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.scan_start, (False, scan_motor_name, cent_scan_start, cent_scan_stop, steps, waittime, Motors), "SCANNING: W-", finalsleep=5)
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_started = self.is_centering(None)
                self.cent_command_buff(self.is_scanning, self.set_array, ('neg', False), "W- Scan Successful", waitsleep=3)
                if self._terminate_flag: break
                if self._teminate_cent: continue

                self.cent_command_buff(self.is_moving, self.move_motor, (angle_motor, cent_angle_o, "Absolute"),
                                       "CENTERING: MOVING TO Wo", command2=self.move_motor,
                                       command2args=(scan_motor, cent_scan_start, "Absolute"))
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.scan_start, (False, scan_motor_name, cent_scan_start, cent_scan_stop, steps, waittime, Motors), "SCANNING: Wo", finalsleep=5)
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_scanning, self.set_array, ('nau',False), "Wo Scan Successful", waitsleep=3)
                if self._terminate_flag: break
                if self._teminate_cent: continue

                self.cent_command_buff(self.is_moving, self.move_motor, (angle_motor, cent_angle_p, "Absolute"),
                                       "CENTERING: MOVING TO W+", command2=self.move_motor,
                                       command2args=(scan_motor, cent_scan_start, "Absolute"))
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.scan_start, (False, scan_motor_name, cent_scan_start, cent_scan_stop, steps, waittime, Motors), "SCANNING: W+",finalsleep=5)
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_scanning, self.set_array, ('pos', False), "W+ Scan Successful", waitsleep=3)
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_event.clear()
                self.is_centering(None)
            time.sleep(1)

    def cent_grab_data(self, x_CB, y_CB):
        full_array, go_bool_array,  x_arr, y_arr= ([] for i in range(4))
        def data_add(x_i, y_i, arr='scan_array'):  # grab the current scan's array if none is provided
            go, x, y = self.get_data(x_i, y_i, arr)  # grabbing x column and y column appropriate to what is defined in the combobox
            if go:
                full_array.append([x, y])
            go_bool_array.append(go)
        for arr in [self.w_neg_array, self.w_naught_array, self.w_pos_array, 'scan_array']:
            data_add(x_CB.currentIndex(), y_CB.currentIndex(), arr)  # we're just grabbing all the same columns
        length = len(full_array)
        if length == 4: length = 3  # Four columns means we have dup data, therefore cent scan = over
        shorten = False
        for i in range(length):
            (x, y) = full_array[i][0], full_array[i][1]
            if x == full_array[i-1][0] and y == full_array[i-1][1] and i>0:
                shorten=True
            else:
                x_arr.append(x)  # grab the appropriate data if it exists
                y_arr.append(y)
        if shorten:
            length = length-1
        return any(go_bool_array), x_arr, y_arr, length

    def cent_plotting(self, plot, table, x_CB, y_CB, calc_CB, single):
        real_name_arr = [x_CB.currentText()]
        (go, x_arr, y_arr, length) = self.cent_grab_data(x_CB, y_CB)
        if go or not self.old_x == x_arr or not self.old_y == y_arr:  # Should we regraph?
            namearr = ['w neg', 'w naught', 'w pos']  #defining names and vars for the diff data sets
            max_array = [VAR.CENT_NEG_MAXY, VAR.CENT_NAU_MAXY, VAR.CENT_POS_MAXY]
            com_array = [VAR.CENT_NEG_COM, VAR.CENT_NAU_COM, VAR.CENT_POS_COM]
            for i in range(length):
                (x, y) = x_arr[i], y_arr[i]
                calc = Calculation(x, y) # initializing the calculation class with each data set
                real_name_arr.append(namearr[i])
                self.monitor.update(max_array[i], calc.x_at_y_max())
                self.monitor.update(com_array[i], calc.COM())
                if i==2: # if we have enough data to calculate the center x,y we do it
                    if str(calc_CB.currentText()) == 'Max Y':
                        pos = self.monitor.get_value(VAR.CENT_POS_MAXY)
                        neg = self.monitor.get_value(VAR.CENT_NEG_MAXY)
                    elif str(calc_CB.currentText()) == 'COM':
                        pos = self.monitor.get_value(VAR.CENT_POS_COM)
                        neg = self.monitor.get_value(VAR.CENT_NEG_COM)  # these are center x/y calcs \/ J Synchrotron Rad 2009 16 83-96 sect eqn 7 + 8 -- http://journals.iucr.org/s/issues/2009/01/00/ie5024/ie5024.pdf
                    self.monitor.update(VAR.CENT_CENTERED_X, (pos + neg)/(2*(1-np.cos(np.degrees(self.angle_pm)))))
                    self.monitor.update(VAR.CENT_CENTERED_Y, (pos - neg) / (2 * (np.sin(np.degrees(self.angle_pm)))))
            if not self.cent_started:
                (x_arr, y_arr) = ([[], [], []], [[], [], []])  # Passing an empty variable if the centering has not begun to clear
                for i in range(3):
                    self.monitor.update(max_array[i], None)
                    self.monitor.update(com_array[i], None)
                self.monitor.update(VAR.CENT_CENTERED_X, None)
                self.monitor.update(VAR.CENT_CENTERED_Y, None)
            if single:
                plot.multi_plot(x_arr, y_arr)
            else:
                for i in range(len(plot)):
                    try:
                        plot[i].new_plot(x_arr[i], y_arr[i], name = i+1)
                    except IndexError:
                        pass
            table.setHorizontalHeaderLabels(real_name_arr)
            table.setColumnCount(length + 1)  # All of the y's plus one x
            table.setRowCount(len(x_arr[0]))
            for row in range(len(x_arr[0])):  # Just assigning table variables with their format
                table.setItem(row, 0, tableItem(str2q("%1").arg(x_arr[0][row])))
            for i in range(length):
                for row in range(len(x_arr[0])):
                    try:
                        table.setItem(row, i + 1, tableItem(str2q("%1").arg(y_arr[i][row])))
                    except IndexError: # If it's outside of range this means no entry, hence blank
                        table.setItem(row, i + 1, tableItem(str2q("%1").arg('')))
            (self.old_x, self.old_y) = x_arr, y_arr

    def save_cent_curr(self, filename, x_CB, y_CB):
        filedir = self.cent_dir
        real_name_arr = [x_CB.currentText()]
        namearr = ['w neg', 'w naught', 'w pos', 'omega '+repr(self.angle_pm)]
        (go, x_arr, y_arr, length) = self.cent_grab_data(x_CB, y_CB)
        if go:
            curr_time = time.strftime("%b_%d_%Y_%H-%M-%S")  # getting time also so we wont have name conflicts
            with open(filedir+'/'+filename+'_'+curr_time+".csv", 'wb') as csvfile:
                writer = csv.writer(csvfile)
                for i in range(length):
                    real_name_arr.append(namearr[i])
                real_name_arr.append(namearr[-1])
                writer.writerow(real_name_arr)
                for i in range(len(x_arr[0])):
                    row = [x_arr[0][i]]
                    for j in range(length):
                        try:
                            row.append(y_arr[j][i])
                        except IndexError:  # No data to be shown
                            row.append('')
                    writer.writerow(row)
                if length==3:
                    writer.writerow(['w- Max Y', 'wo Max Y', 'w+ Max Y', 'Max Y Center X', 'Max Y Center Y'])
                    pos = self.monitor.get_value(VAR.CENT_POS_MAXY)
                    neg = self.monitor.get_value(VAR.CENT_NEG_MAXY)
                    writer.writerow([neg, self.monitor.get_value(VAR.CENT_NAU_MAXY), pos,
                                     (pos + neg) / (2 * (1 - np.cos(np.degrees(self.angle_pm)))),
                                     (pos - neg) / (2 * (np.sin(np.degrees(self.angle_pm))))
                                     ])
                    writer.writerow(['w- COM', 'wo COM', 'w+ COM', 'COM Center X', 'COM Center Y'])
                    pos = self.monitor.get_value(VAR.CENT_POS_COM)
                    neg = self.monitor.get_value(VAR.CENT_NEG_COM)
                    writer.writerow([neg, self.monitor.get_value(VAR.CENT_NAU_COM), pos,
                                     (pos + neg) / (2 * (1 - np.cos(np.degrees(self.angle_pm)))),
                                     (pos - neg) / (2 * (np.sin(np.degrees(self.angle_pm)))),
                                     ])
            print "Successfully saved " + filename + '_' + curr_time + ".csv" + " In : " + filedir
        
    """ RANDOM UTILITIES """
    def update_CB(self, x_data_CB, y_data_CB, type):
        self.CB_lock.acquire()
        try:
            if type == 'scan':
                self.x_scan_data_CB = x_data_CB
                self.y_scan_data_CB = y_data_CB
            elif type == 'cent':
                self.x_cent_data_CB = x_data_CB
                self.y_cent_data_CB = y_data_CB
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
        finally:
            self.CB_lock.release()

    def get_var(self, var_name):
        """Return variable"""
        if self.Spec_sess.connection is not None:
            c = self.Spec_sess.connection.getChannel('var/'+var_name)
            return c.read()

    def init_Spec(self):
        # starting up the Spec server, completed in main_window as monitor needs to load
        Spec.connectToSpec(self.Spec_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))

    def update_filepath(self, filepath, name):
        if name == 'scan':
            self.scan_dir = filepath
        elif name == 'cent':
            self.cent_dir = filepath

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

    def x_at_y_max(self):
        (unused, x_at_y_max) = self.y_max_full()
        return x_at_y_max

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