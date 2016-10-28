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
import scipy.ndimage.measurements as meas
import ctypes  # An included library with Python install.

from functools import partial

# App imports
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant
from utils import graph


import SpecClient.SpecMotor as SpecMotor_module
from SpecClient.SpecMotor import SpecMotorA as SpecMotor
from SpecClient.Spec import Spec
from SpecClient.Spec import SpecConnectionsManager
from SpecClient.SpecCounter_toki import SpecCounter as SpecCounter
from SpecClient.SpecClientError import SpecClientError

from SpecClient.SpecScan_toki import SpecScanA as SpecScan

from PyQt4 import QtGui
from PyQt4.QtGui import QTableWidgetItem as tableItem
from PyQt4.QtCore import QString as str2q

import settings


class PV(Constant):

    SYSTEM_TIME         = 'WIG1405-01:systemTime'
    CYCLES              = 'TRG2400:cycles'
    BEAM_STOP           = 'BL1606-ID1:mcs09:fbk'
    PRE_OPTICS          = 'BL1606-ID1:mcs07:fbk'

    COND_DIFF_HOR_STATUS = 'PSL1606-2-I10-26:status'
    COND_DIFF_HOR_GAP_POS = 'PSL1606-2-I10-26:gap'
    COND_DIFF_HOR_CENT_POS = 'PSL1606-2-I10-26:center'
    COND_DIFF_HOR_MOT1_POS = 'SMTR16062I10100:mm'
    COND_DIFF_HOR_MOT2_POS = 'SMTR16062I10101:mm'

    COND_DIFF_VERT_STATUS = 'PSL1606-2-I10-25:status'
    COND_DIFF_VERT_GAP_POS = 'PSL1606-2-I10-25:gap'
    COND_DIFF_VERT_CENT_POS = 'PSL1606-2-I10-25:center'
    COND_DIFF_VERT_MOT1_POS = 'SMTR16062I1098:mm'
    COND_DIFF_VERT_MOT2_POS = 'SMTR16062I1099:mm'

    COND_TABLE_HOR_STATUS = 'PSL16062I1024:status'
    COND_TABLE_HOR_GAP_POS   = 'PSL16062I1024:gap'
    COND_TABLE_HOR_CENT_POS  = 'PSL16062I1024:center'
    COND_TABLE_HOR_MOT1_POS  = 'SMTR16062I1079:mm'
    COND_TABLE_HOR_MOT2_POS  = 'SMTR16062I1078:mm'

    COND_TABLE_VERT_STATUS = 'PSL16062I1023:status'
    COND_TABLE_VERT_GAP_POS = 'PSL16062I1023:gap'
    COND_TABLE_VERT_CENT_POS = 'PSL16062I1023:center'
    COND_TABLE_VERT_MOT1_POS = 'SMTR16062I1076:mm'
    COND_TABLE_VERT_MOT2_POS = 'SMTR16062I1077:mm'

    COND_PB_APER_HOR_POS = 'SMTR16062I1085:mm:sp'
    COND_PB_APER_VERT_POS = 'SMTR16062I1084:mm:sp'

    COND_DAC_PIN_HOR_POS = 'SMTR16062I1087:mm:sp'
    COND_DAC_PIN_VERT_POS = 'SMTR16062I1086:mm:sp'

    COND_BEAM_STOP_HOR_POS = 'SMTR16062I10106:mm:sp'
    COND_BEAM_STOP_VERT_POS = 'SMTR16062I10107:mm:sp'

    COND_PB_APER_HOR_POS_PUSH = 'SMTR16062I1085:mm'
    COND_PB_APER_VERT_POS_PUSH = 'SMTR16062I1084:mm'

    COND_DAC_PIN_HOR_POS_PUSH = 'SMTR16062I1087:mm'
    COND_DAC_PIN_VERT_POS_PUSH = 'SMTR16062I1086:mm'

    COND_BEAM_STOP_HOR_POS_PUSH = 'SMTR16062I10106:mm'
    COND_BEAM_STOP_VERT_POS_PUSH = 'SMTR16062I10107:mm'

    COND_PB_APER_HOR_STATUS = 'SMTR16062I1085:status'
    COND_PB_APER_VERT_STATUS = 'SMTR16062I1084:status'

    COND_DAC_PIN_HOR_STATUS = 'SMTR16062I1087:status'
    COND_DAC_PIN_VERT_STATUS = 'SMTR16062I1086:status'

    COND_BEAM_STOP_HOR_STATUS = 'SMTR16062I10106:status'
    COND_BEAM_STOP_VERT_STATUS = 'SMTR16062I10107:status'


class VAR(Constant):
    STATUS_MSG          = 'var:status_message'

    MOTOR_1_POS         = 'var:motor_1_pos'
    MOTOR_2_POS         = 'var:motor_2_pos'
    MOTOR_3_POS         = 'var:motor_3_pos'
    MOTOR_4_POS         = 'var:motor_4_pos'
    MOTOR_5_POS         = 'var:motor_5_pos'
    MOTOR_6_POS         = 'var:motor_6_pos'
    
    EXTRA_MOTOR_1_POS         = 'var:extra_motor_1_pos'
    EXTRA_MOTOR_2_POS         = 'var:extra_motor_2_pos'
    EXTRA_MOTOR_3_POS         = 'var:extra_motor_3_pos'
    EXTRA_MOTOR_4_POS         = 'var:extra_motor_4_pos'
    EXTRA_MOTOR_5_POS         = 'var:extra_motor_5_pos'
    EXTRA_MOTOR_6_POS         = 'var:extra_motor_6_pos'

    SLIT_1_MOTOR_1_POS = 'var:slit_1_motor_1_pos'
    SLIT_1_MOTOR_2_POS = 'var:slit_1_motor_2_pos'
    SLIT_1_MOTOR_3_POS = 'var:slit_1_motor_3_pos'
    SLIT_1_MOTOR_4_POS = 'var:slit_1_motor_4_pos'

    SLIT_2_MOTOR_1_POS = 'var:slit_2_motor_1_pos'
    SLIT_2_MOTOR_2_POS = 'var:slit_2_motor_2_pos'
    SLIT_2_MOTOR_3_POS = 'var:slit_2_motor_3_pos'
    SLIT_2_MOTOR_4_POS = 'var:slit_2_motor_4_pos'
    
    APER_MOTOR_1_POS         = 'var:aper_motor_1_pos'
    APER_MOTOR_2_POS         = 'var:aper_motor_2_pos'
    
    DAC_MOTOR_1_POS         = 'var:dac_motor_1_pos'
    DAC_MOTOR_2_POS         = 'var:dac_motor_2_pos'
    
    STOP_MOTOR_1_POS         = 'var:stop_motor_1_pos'
    STOP_MOTOR_2_POS         = 'var:stop_motor_2_pos'

    # SCAN_ARRAY          = 'var:scan_array'
    SCAN_MAX_Y          = 'var:scan_max_y'
    SCAN_FWHM           = 'var:scan_FWHM'
    SCAN_COM            = 'var:scan_COM'
    SCAN_CWHM           = 'var:scan_CWHM'
    SCAN_CENTROID       = 'var:scan_centroid'
    SCAN_MAX_Y_NUM      = 'var:scan_max_y_num'
    #
    # MESH_ARRAY = 'var:mesh_array'

    MESH_COM_X = 'var:mesh_com_x'
    MESH_COM_Y = 'var:mesh_com_y'
    MESH_CLICK_X = 'var:mesh_click_x'
    MESH_CLICK_Y = 'var:mesh_click_y'
    MESH_MAX_X = 'var:mesh_max_x'
    MESH_MAX_Y = 'var:mesh_max_y'
    

    CENT_NEG_MAXY       = 'var:cent_neg_maxy'
    CENT_NEG_COM        = 'var:cent_neg_com'
    CENT_NEG_CWHM       = 'var:cent_neg_cwhm'
    CENT_NAU_MAXY       = 'var:cent_nau_maxy'
    CENT_NAU_COM        = 'var:cent_nau_com'
    CENT_NAU_CWHM       = 'var:cent_nau_cwhm'
    CENT_NAU_CWHM       = 'var:cent_nau_cwhm'
    CENT_POS_MAXY       = 'var:cent_pos_maxy'
    CENT_POS_COM        = 'var:cent_pos_com'
    CENT_POS_CWHM       = 'var:cent_pos_cwhm'

    CENT_CENTERED_X     = 'var:cent_centered_x'
    CENT_CENTERED_Y     = 'var:cent_centered_y'

    CENT_SCAN_MOTOR     = 'var:cent_scan_motor'
    CENT_AMGLE_MOTOR    = 'var:cent_angle_motor'

    COUNTER_1_COUNT     = 'var:counter_1_count'
    COUNTER_2_COUNT     = 'var:counter_2_count'
    COUNT_TIME          = 'var:count_time'

    SERVER_ADDRESS      = 'var:server_address'
    SERVER_HOST         = 'var:server_host'
    SERVER_PORT         = 'var:server_port'

    VERT_BAR_SCAN_X = 'var:bar_scan_x'
    VERT_BAR_MULTI_X = 'var:bar_multi_x'
    VERT_BAR_NEG_X = 'var:bar_neg_x'
    VERT_BAR_NAU_X = 'var:bar_nau_x'
    VERT_BAR_POS_X = 'var:bar_x_x'

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

        self._terminate_flag = self._move_terminate_flag = self.mesh_started = self._teminate_rock = False

        self.count_event, self.scan_event, self.mesh_event, self.cent_event, self.rock_event, \
                self.stage_move_event, self.extra_move_event, self.check_move_event, self.scan_rw_event, \
            = (threading.Event() for _ in range(9))  # we have to do it like this to do a "deep" copy

        for clear_event in [self.count_event, self.scan_event, self.mesh_event, self.cent_event, self.rock_event]:
            clear_event.clear() # starting a bunch of event flags, some will be flagged and others not
        for set_event in [self.stage_move_event, self.extra_move_event, self.check_move_event, self.scan_rw_event,]:
            set_event.set()

        for handle in [self.handle_scan, self.handle_mesh, self.handle_cent,  self.handle_rock]:
            timer = threading.Timer(.1, handle)
            timer.start()  # starting all the threads

        self.Spec_sess = Spec()
        self.SpecMotor_sess = SpecMotor()
        self.SpecScan_sess = SpecScan()
        self.SpecMesh_sess = SpecScan()

        self.SpecMotor_sess.state = SpecMotor_module.NOTINITIALIZED

        self._SpecMotor_sess = [None]*26  # We currently have 26 possible motor slots

        self.moving_bool_dict = {}

        self.main_mesh_array, self.main_scan_array, self.old_full_array, self.scan_array, self.old_array, self.old_x, self.old_y, = ([] for _ in range(7))
        self.cent_props = ('', '', 0, 0, 0, 0, 0, [], True)
        self.CB_lock = threading.Lock()

    """ MOTOR """
    def move_motor(self, motor, moveto=None, movetype=None):  # IF CALLING PROGRAMATICALLY, DECLARE MOVETO & MOVETYPE
        if self.is_moving(motor.Name):  # Make sure the motors not moving, if so ignore the call
            self.set_status(motor.Name + " is already moving")
        else:
            if moveto == None:
                moveto = motor.Moveto_SB.value()
            if movetype == None:
                movetype = motor.MoveType_CB.currentText()
            motor_name = motor.Mne
            self.monitor.update(VAR.STATUS_MSG, "Moving Motor " + motor.Name)
            if motor.Enabled:
                motor_check = self.checkpos_motor(motor)  # This sets the motor to the correct Mne as well
                pos = motor_check['pos']
                (low, high) = self.SpecMotor_sess.getLimits()
                if movetype == 'Relative':
                    moveto = pos+moveto
                if low < moveto < high:  # make sure its within limits before
                    SpecMotor.move(self.SpecMotor_sess, moveto)
                    print "Moving motor " + motor_name + " to " + repr(moveto)
                else:
                    self._error_callback("The motor was asked to move to " + repr(moveto) + " \nwhich is outside of the accepted range of " + repr((low, high)))
            else:
                self._error_callback("Cannot Move non-enabled motor")

    def motor_stop(self, motor):
        if motor.Enabled:
            if self.checkpos_motor(motor)['moved']:  # This sets the motor to the correct Mne as well as checking if its moving
                SpecMotor.stop(self.SpecMotor_sess)
                print motor.Name + " has been stopped"
            else:
                print motor.Name + " does not appear to be moving"
        else:
            print "Cannot stop a disabled motor"

    def checkpos_motor(self, motor, print_val=True, SpecMot=None):
        if SpecMot == None:
            SpecMot = self.SpecMotor_sess
        self.check_move_event.wait()
        self.check_move_event.clear()  # We have to go one check at a time so we don't catch the wrong signal
        if not SpecMot.specName == motor.Mne:
            SpecMotor.connectToSpec(SpecMot, motor.Mne, self.monitor.get_value(VAR.SERVER_ADDRESS))
        try:
            init_pos = self.monitor.get_value(motor.Pos_VAR)
            pos = SpecMotor.getPosition(SpecMot)
            moved = not (init_pos == pos)  # Our motors are stable and when they stop the detector has never seen movement, this will break if it does
            if moved:  # this is where you can hook if motors are moving or not
                self.monitor.update(motor.Pos_VAR, pos)
                if print_val:
                    print repr(self.monitor.get_value(motor.Pos_VAR))
        except SpecClientError as e:
            print repr(e) + ' unconfig = Motor Name: ' + motor.Name
            pos = 'None'
            moved = False
        self.check_move_event.set()
        return {'pos': pos, 'moved': moved}

    def init_motor_thread(self, Motors):  # Start thread for each motor which is going to be checked
        for i, motor in enumerate(Motors):
            if motor.Enabled:
                self.move_thread = threading.Thread(group=None, target=self.handle_motor_moving_thread, name=None,
                                                    args=(motor, i))
                self.move_thread.start()

    def handle_motor_moving_thread(self, motor, id):
        moved = False  # initializing variable which gets checked before assigned on first loop
        self._SpecMotor_sess[id] = SpecMotor()
        while True:
            if motor.Extra:
                self.extra_move_event.wait()
            else:
                self.stage_move_event.wait()
            if self._move_terminate_flag: break
            if self._terminate_flag: break
            if self._SpecMotor_sess[id].specName == motor.Mne:
                '''
                moving = inst_self['state'] in [SpecMotor_module.MOVING, SpecMotor_module.MOVESTARTED]
                if moving:  # this doesnt seem to work because it doesnt properly register when the motor is moving
                # I believe this issue is with SpecClient and not with my code...
                '''
                self.check_move_event.wait()  # This stops the motors from updating each other's monitors
                motor_check = self.checkpos_motor(motor, False, SpecMot=self._SpecMotor_sess[id])
                moved, pos = motor_check['moved'], motor_check['pos']
                if moved:
                    # time.sleep(0.1)
                   print motor.Name + " has moved to " + repr(pos)
                else:
                    time.sleep(.5)
                try:
                    self.moving_bool_dict[motor.Name] = moved
                except KeyError:  # if we have no entry we add one.
                    self.moving_bool_dict.update({motor.name, moved})
            else:  # making sure we're looking at the right motor
                time.sleep(1)
                SpecMotor.connectToSpec(self._SpecMotor_sess[id], motor.Mne, self.monitor.get_value(VAR.SERVER_ADDRESS))
        print "Thread killed : " + motor.Name

    def stage_motor_track_state(self, state):
        if state:  # If the checkbox is clicked
            self.stage_move_event.set()
        else:  # Disable movecheck
            self.stage_move_event.clear()

    def extra_motor_track_state(self, state):
        if state:  # If the checkbox is clicked
            self.extra_move_event.set()
        else:  # Disable movecheck
            self.extra_move_event.clear()

    def check_limits(self, motor):
        self.checkpos_motor(motor) # check where the motor is and assigning it.
        return SpecMotor.getLimits(self.SpecMotor_sess)

    def is_moving(self, motor_name='none'):  # will return if all motors are moving or not unless motor is specified
        if motor_name == 'none':
            return not all(bool == False for bool in self.moving_bool_dict.values())
        else:
            return self.moving_bool_dict[motor_name]

    def update_motors(self, motor_names, Motors, CBs):  # updates motor variables and such and starts threads
        self._move_terminate_flag = False
        for CB in CBs:
            CB.clear()
        self.init_motor_thread(Motors)
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Enabled:
                for CB in CBs:
                    CB.addItem(Motor_inst.Name)
                motor_names[i].setText(Motor_inst.Name)
                (min_lim, max_lim) = self.check_limits(Motor_inst)
                Motor_inst.Moveto_SB.setRange(min_lim * 2, max_lim * 2)

    """ SCANNING """
    def is_scanning(self, button=None):  # We want to set the button that we use... this is not how I should've approached this
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
            if str(button.text()) == 'Stop':
                t = threading.Timer(.25, self.post_scan)  # after scan we can do some actions
                t.start()
            button.setText('Start')
            try:
                self.backup_scan()
            except OSError:
                print "Backup Directory not specified, BACKUP NOT SAVED"
        return self.SpecScan_sess.scanning

    def post_scan(self):
        if not self.is_scanning():
            print "Scan Finished"
            self.scan_event.clear()  # This stops the thread from spamming checks after the scan is done

    def scan_start(self, scantype, motor_name, startpos, endpos, intervals, count_time, Motors):
        self.mesh_event.clear()  # Stops Mesh as these use the same backend and shouldnt be run at the same time.
        for Motor_inst in Motors:
            if Motor_inst.Name == motor_name:
                if Motor_inst.Enabled:
                    self.scan_array_counter = 0
                    self.scan_event.set()
                    SpecScan.connectToSpec(self.SpecScan_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))
                    SpecScan.newScan(self.SpecScan_sess, True)
                    if scantype == 'Rel':
                        checkpos = self.checkpos_motor(Motor_inst, False)
                        pos = checkpos['pos']
                        relstartpos = startpos - pos
                        relendpos = endpos - pos
                        SpecScan.dscan(self.SpecScan_sess, Motor_inst.Mne, relstartpos, relendpos, intervals, count_time)
                    elif scantype == 'Abs':
                        SpecScan.ascan(self.SpecScan_sess, Motor_inst.Mne, startpos, endpos, intervals, count_time)
                    elif scantype == 'Rock':
                        SpecScan.rocking(self.SpecScan_sess, Motor_inst.Mne, startpos, endpos, intervals, count_time)
                    self.scan_array = []  # starting/wiping an array for the scan data to push into
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
        _rep = repeats = 0
        while True:
            if self._terminate_flag: break
            self.scan_event.wait()
            if self._terminate_flag: break
            # while self.is_scanning():
            while True:
                if self._terminate_flag: break
                self.scan_event.wait()
                # old_data = self.scan_data
                self.check_move_event.wait()
                self.check_move_event.clear()
                old_point = self.scan_point
                #self.scan_data = SpecScan.get_SCAN_D(self.SpecScan_sess)
                try:
                    # print "Grabbing Point"
                    # Note we grab SCAN_PT which is the last point, it may be better to work with SCAN_D which is the full array, but I had troubles
                    self.scan_point = json.JSONDecoder.decode(json.JSONDecoder(), SpecScan.get_SCAN_PT(self.SpecScan_sess))
                    # scan_arr = SpecScan.get_SCAN_D(self.SpecScan_sess)
                    # scan_arr = scan_arr[~np.all(scan_arr == 0, axis=1)]
                except (ValueError, TypeError):
                    print "Error: Scan Point"
                self.check_move_event.set()
                #elif array_equal(old_data, self.scan_data):
                if not old_point == self.scan_point: # here is where you would graph it/save it to the csv
                    _rep = (repeats +_rep)/2  # this is an odd thing I used to slow down requests
                    repeats = 0
                    # print "Scan point " + repr(self.scan_point[0]) + " Counter: " +repr(self.scan_array_counter)
                    if self.scan_point[0] == 1 and self.scan_array_counter == 0:
                        self.scan_array_counter = self.scan_array_counter + 1  # allows missing of 0th point
                    if self.scan_point[0] > self.scan_array_counter and self.scan_array_counter == 0: #Skips old point
                        print "Scan point ignored ScanPoint:" + repr(self.scan_point[0]) + " Counter: " + repr(self.scan_array_counter)
                    elif self.scan_point[0] == self.scan_array_counter:  #actually adds data
                        self.scan_array.insert(self.scan_point[0], self.scan_point[1])
                        self.scan_array_counter = self.scan_array_counter + 1
                        print "Scan point " + repr(self.scan_point[0]), " added to array"
                        self.scan_rw_event.wait()
                        self.scan_rw_event.clear()
                        self.main_scan_array = self.scan_array
                        self.scan_rw_event.set()
                    else:
                        print "Entering data into the scan array has not worked properly \n" \
                              "Scan Counter: " + repr(self.scan_array_counter) + " Scan Point: " + repr(self.scan_point[0])
                    self.scan_SB_sleeper(ratio=0.75, _min=False)
                    pass
                elif not self.is_scanning():
                    self.scan_SB_sleeper()
                else:
                    repeats = repeats + 1
                    ratio = 0.5 + _rep*0.1
                    self.scan_SB_sleeper(ratio=ratio, _min=False) # slows down thread
            if self._terminate_flag: break
            self.scan_SB_sleeper()

    def scan_stop(self):
        SpecScan.abort(self.SpecScan_sess)
        self.scan_event.clear()
        print "Scan Stopped"
        return False  # Saying the scan is stopped

    def scan_settings(self, motor_name, startpos_SB, stoppos_SB, Motors, wait_time_SB): #setting some properties based off motor choice
        self.scan_wait_time_SB = wait_time_SB
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Name == motor_name:
                if Motor_inst.Enabled:
                    (min_lim, max_lim) = self.check_limits(Motor_inst)
                    startpos_SB.setRange(min_lim, max_lim)
                    stoppos_SB.setRange(min_lim, max_lim)

    def scan_SB_sleeper(self, default_time=2, ratio=1.0, _min=True):
        try:  # Setting wait times to the interval time of the scan's spinbox if it isn't too small
            if not _min:
                sleep_time = default_time
            elif self.scan_wait_time_SB.value() >= 0.01:
                sleep_time = self.wait_time_SB.value() * ratio
            else:
                sleep_time = self.wait_time_SB.value()/ratio
        except:
            sleep_time = default_time
        # print "Scanning Thread is sleeping for " + repr(sleep_time)
        time.sleep(sleep_time)

    def get_data(self, x_index, y_index, array='scan_array'):
        if array == 'scan_array':  # if we have not provided an array
            self.scan_rw_event.wait()
            self.scan_rw_event.clear()
            array = self.main_scan_array
            self.scan_rw_event.set()
        if array is None or not array:
            return False, [], []
        else:
            try:  # getting data relevant to the array entry we actually want
                (x, y) = [point[x_index] for point in array], [point[y_index] for point in array]
                return True, x, y
            except IndexError:
                print "Non valid choice for data, returning closest match"
                fixed = True  # fixed unless proven otherwise
                try:  # If you move from contour to anything else, your data choice will be off, so we will try to fix this by slightly altering indicies
                    x = [point[x_index] for point in array]
                except IndexError:
                    try:
                        x = [point[x_index - 1] for point in array]
                    except IndexError:
                        x=[]
                        fixed = False
                try:
                    y = [point[y_index] for point in array]
                except IndexError:
                    try:
                        y = [point[y_index - 1] for point in array]
                    except IndexError:
                        y=[]
                        fixed = False
                return fixed, x, y

    def scan_calculations(self, x, y):
        calc = Calculation(x, y)  # we do some calculations and set the monitor to them
        # self.monitor.update(VAR.SCAN_MAX_Y, calc.y_max_string())
        self.monitor.update(VAR.SCAN_MAX_Y_NUM, calc.x_at_y_max())
        self.monitor.update(VAR.SCAN_FWHM, calc.FWHM())
        self.monitor.update(VAR.SCAN_COM, calc.COM())
        self.monitor.update(VAR.SCAN_CWHM, calc.CFWHM())

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

    """ MESHING """

    def is_meshing(self, button=None):
        if button == None:  # Silly button stuff is same as scan
            try:
                button = self.saved_button
            except UnboundLocalError:
                pass
        else:
            self.saved_button = button
            # This property is checked, so functions here will work
        self.SpecMesh_sess.meshing = SpecScan.isMeshing(self.SpecMesh_sess)
        if self.SpecMesh_sess.meshing:
            button.setText('Stop')
            if not self.mesh_started:
                self.update_CB(self.x_mesh_data_CB, self.y_mesh_data_CB, 'mesh')
                self.mesh_started = True
        else:
            button.setText('Start')
            try:
                # self.backup_mesh()
                pass
            except OSError:
                print "Backup Directory not specified, BACKUP NOT SAVED"
            if self.mesh_started:
                self.mesh_event.clear()  # stops the meshing thread when the mesh isn't running
                self.mesh_started = False
        return self.SpecMesh_sess.meshing

    def mesh_start(self, fast_motor_name, slow_motor_name, fast_startpos, fast_endpos, 
                   slow_startpos, slow_endpos, fast_intervals, slow_intervals, count_time, Motors):
        (fast_found, slow_found) = False, False
        # self.scan_event.clear()
        for i in range(len(Motors)):
            if not fast_found:
                Fast_Motor_inst = Motors[i]
                if Fast_Motor_inst.Name == fast_motor_name:
                    if Fast_Motor_inst.Enabled:
                        fast_found = True
            if not slow_found:
                Slow_Motor_inst = Motors[i]
                if Slow_Motor_inst.Name == slow_motor_name:
                    if Slow_Motor_inst.Enabled:
                        slow_found = True
            if slow_found and fast_found:
                self.mesh_array_counter = 0
                self.mesh_array_fast = fast_intervals
                SpecScan.connectToSpec(self.SpecMesh_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))
                SpecScan.newScan(self.SpecMesh_sess, True)
                SpecScan.mesh(self.SpecMesh_sess, Fast_Motor_inst.Mne, fast_startpos, fast_endpos, fast_intervals,
                              Slow_Motor_inst.Mne, slow_startpos, slow_endpos, slow_intervals, count_time)
                self.mesh_event.set()
                self.mesh_array = []  # starting/wiping an array for the mesh data to push into
                break
        if slow_found and fast_found:
            print "Mesh Started"
            t = threading.Timer(1, self.is_meshing)
            t.start()
            return True  # Saying the mesh is started

        else:
            raise Exception('Mesh cannot be started as the motor was not Enabled')

    def handle_mesh(self):
        # Thread which handles mesh data, incredibly similar to scan, doing a class would've made more sense in retrospect
        self.mesh_event.wait()
        self.mesh_data = []  # Initalizing empty arrays
        self.mesh_point = []
        while True:
            if self._terminate_flag: break
            self.mesh_event.wait()
            if self._terminate_flag: break
            old_data = self.mesh_data
            old_point = self.mesh_point
            # self.mesh_data = SpecMesh.get_MESH_D(self.SpecMesh_sess)
            try:
                self.mesh_point = json.JSONDecoder.decode(json.JSONDecoder(),
                                                          SpecScan.get_SCAN_PT(self.SpecMesh_sess))
            except (ValueError, TypeError):
                print "Error: Mesh Point"
                pass
            # elif array_equal(old_data, self.mesh_data):
            if not old_point == self.mesh_point:  # here is where you would graph it/save it to the csv
                print "Mesh point " + repr(self.mesh_point[0]) + " Counter: " + repr(self.mesh_array_counter)
                if self.mesh_point[0] == 1 and self.mesh_array_counter == 0:
                    self.mesh_array_counter = self.mesh_array_counter + 1
                if self.mesh_point[0] > self.mesh_array_counter and self.mesh_array_counter == 0:  # Skips old point
                    print "Mesh point ignored MeshPoint:" + repr(self.mesh_point[0]) + " Counter: " + repr(
                        self.mesh_array_counter)
                elif self.mesh_point[0] == self.mesh_array_counter:
                    self.mesh_array.insert(self.mesh_point[0], self.mesh_point[1])
                    self.mesh_array_counter = self.mesh_array_counter + 1
                    self.main_mesh_array = self.mesh_array
                else:
                    print "Entering data into the mesh array has not worked properly \n" \
                          "Mesh Counter: " + repr(self.mesh_array_counter) + " Mesh Point: " + repr(
                        self.mesh_point[0])
                if self.mesh_array_fast+1 == self.mesh_array_counter:
                    self.mesh_array_counter = 0  # We've gone through a fast scan, resetting counter
                self.mesh_SB_sleeper(ratio=0.75, _min=False)
                pass
            elif not self.is_meshing():
                self.mesh_SB_sleeper()
            else:
                self.mesh_SB_sleeper(ratio=0.5, _min=False)

    def mesh_stop(self):
        SpecScan.abort(self.SpecMesh_sess)
        self.mesh_event.clear()
        t = threading.Timer(1, self.is_meshing)
        t.start()
        print "Mesh Stopped"
        return False  # Saying the mesh is stopped

    def mesh_settings(self, fast_motor_name, fast_startpos_SB, fast_stoppos_SB, 
                      slow_motor_name, slow_startpos_SB, slow_stoppos_SB, Motors, wait_time_SB):
        self.mesh_wait_time_SB = wait_time_SB
        for i in range(len(Motors)):
            Fast_Motor_inst = Motors[i]
            if Fast_Motor_inst.Name == fast_motor_name:
                if Fast_Motor_inst.Enabled:
                    (min_lim, max_lim) = self.check_limits(Fast_Motor_inst)
                    fast_startpos_SB.setRange(min_lim, max_lim)
                    fast_stoppos_SB.setRange(min_lim, max_lim)
            Slow_Motor_inst = Motors[i]
            if Slow_Motor_inst.Name == slow_motor_name:
                if Slow_Motor_inst.Enabled:
                    (min_lim, max_lim) = self.check_limits(Slow_Motor_inst)
                    slow_startpos_SB.setRange(min_lim, max_lim)
                    slow_stoppos_SB.setRange(min_lim, max_lim)

    def mesh_SB_sleeper(self, default_time=3.0, ratio=1.0, _min=True):
        try:  # Setting wait times to the interval time of the mesh's spinbox if it isn't too small
            if not min:
                sleep_time = default_time
            elif self.mesh_wait_time_SB.value() >= 0.01:
                sleep_time = self.wait_time_SB.value() * ratio
            else:
                sleep_time = default_time * ratio
        except:
            sleep_time = default_time
        # print "Meshing Thread is sleeping for " + repr(sleep_time)
        time.sleep(sleep_time)

    def get_mesh_data(self, x_index, y_index, intes_index, array='mesh_array'):
        if array == 'mesh_array':  # if we have not provided an array
            array = self.main_mesh_array
        if array is None or not array:
            return False, [], [], []
        else:
            (x, y, intes) = [point[x_index] for point in array], \
                            [point[y_index] for point in array], \
                            [point[intes_index] for point in array]
            # print "Got Mesh Data"
            return True, x, y, intes

    def mesh_calculations(self, x, y, z):
        calc = Calculation3D(x, y, z)
        x_com, y_com = (calc.COM())
        self.monitor.update(VAR.MESH_COM_X, x_com)
        self.monitor.update(VAR.MESH_COM_Y, y_com)
        x_max, y_max = (calc.MAX())
        self.monitor.update(VAR.MESH_MAX_X, x_max)
        self.monitor.update(VAR.MESH_MAX_Y, y_max)
    
    def mesh_move(self, movetype, xmne, ymne, Motors):
        if movetype == 'Click':
            xvar, yvar = VAR.MESH_CLICK_X, VAR.MESH_CLICK_Y
        elif movetype == 'Max':
            xvar, yvar = VAR.MESH_MAX_X, VAR.MESH_MAX_Y
        elif movetype == 'COM':
            xvar, yvar = VAR.MESH_COM_X, VAR.MESH_COM_Y
        self.move_motor(self.get_motor(xmne, Motors), moveto=float(self.monitor.get_value(xvar)), movetype='Absolute')
        time.sleep(0.01)
        self.move_motor(self.get_motor(ymne, Motors), moveto=float(self.monitor.get_value(yvar)), movetype='Absolute')

    # SAVING DOES NOT EXIST IN THIS VERSION, but here is framwork slightly altered from scan

    # def save_mesh_curr(self, filename, x_CB, y_CB):
    #     filedir = self.mesh_dir
    #     go, x, y = self.get_data(x_CB.currentIndex(), y_CB.currentIndex())
    #     if go:
    #         curr_time = time.strftime("%b_%d_%Y_%H-%M-%S")  # getting time also so we wont have name conflicts
    #         with open(filedir + '/' + filename + '_' + curr_time + ".csv", 'wb') as csvfile:
    #             header = [str(x_CB.currentText()), str(y_CB.currentText())]
    #             writer = csv.writer(csvfile)
    #             writer.writerow(header)
    #             for i in range(len(x)):
    #                 writer.writerow([x[i], y[i]])
    #             writer.writerow(["Max Y", "FWHM", "CWHM", "COM", "Centroid"])
    #             writer.writerow([self.monitor.get_value(VAR.MESH_MAX_Y),
    #                              self.monitor.get_value(VAR.MESH_FWHM),
    #                              self.monitor.get_value(VAR.MESH_CWHM),
    #                              self.monitor.get_value(VAR.MESH_COM),
    #                              self.monitor.get_value(VAR.MESH_CENTROID),
    #                              ])
    #             print "Successfully saved " + filename + '_' + curr_time + ".csv" + " In : " + filedir
    #     else:
    #         print "Cannot Write, No data acquired"
    #
    # def backup_mesh(self):
    #     if not self.old_array == self.mesh_array:
    #         self.old_array = self.mesh_array
    #         back_dir = self.mesh_dir + '/backup'
    #         if not os.path.exists(back_dir):
    #             os.makedirs(back_dir)
    #             print "Backup directory in " + back_dir + "\nhas been created"
    #         if self.mesh_array and self.meshner_names:
    #             curr_time = time.strftime("%b_%d_%Y_%H-%M-%S")  # getting time also so we wont have name conflicts
    #             with open(back_dir + '/' + "BACKUP" + '_' + curr_time + ".csv", 'wb') as csvfile:
    #                 writer = csv.writer(csvfile)
    #                 header = []
    #                 for k in range(len(self.meshner_names)):
    #                     header.append(self.meshner_names[str(k)])
    #                 writer.writerow(header)
    #                 for i in range(len(self.mesh_array)):
    #                     mesh_row = self.mesh_array[i]
    #                     row = []
    #                     for j in range(len(mesh_row)):
    #                         row.append(mesh_row[j])
    #                     writer.writerow(row)
    #                 print "Backup csv has been created in " + repr(csvfile)

    """ CENTER """
    def cent_settings(self, scan_motor_name, angle_motor_name, relmax_SB, relmin_SB, angle_pm_SB, angle_o_SB, Motors, wait_time_SB, center_calc_CB):
        self.wait_time_SB = wait_time_SB
        items = ['Max Y', 'COM', 'Curser', 'CWHM']
        center_calc_CB.setMaxCount(len(items))    # At init we have to do some limit setting/setting up of UI elements
        for item in items:  # we do it here because they are mostly calcs which rely on the motors chosen
            center_calc_CB.addItem(item)  # This combo box is not one of those though
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Enabled:
                (min_lim, max_lim) = self.check_limits(Motor_inst)
                full_range = abs(min_lim) + abs(max_lim)
                if Motor_inst.Name == scan_motor_name:
                    relmax_SB.setRange(-1 * full_range, full_range)
                    relmin_SB.setRange(-1 * full_range, full_range)
                elif Motor_inst.Name == angle_motor_name:
                    angle_o_SB.setRange(min_lim, max_lim)
                    angle_pm_SB.setRange(-1 * full_range/2, full_range/2)

    def is_centering(self, start_stop_PB, label = None):
        if start_stop_PB == None:
            try:
                start_stop_PB = self.start_stop_PB
            except UnboundLocalError:
                pass
        else:
            self.start_stop_PB = start_stop_PB
            # This property is checked, so functions here will work
        if label == None:
            try:
                label = self.start_stop_label
            except UnboundLocalError:
                pass
        else:
            self.start_stop_label = label
            # This property is checked, so functions here will work
        if self.cent_event._Event__flag:
            start_stop_PB.setText('Stop')
            label.setText('Curr Pos')
            self.update_CB(self.x_cent_data_CB, self.y_cent_data_CB, 'cent')
        else:
            start_stop_PB.setText('Start')
            label.setText('Center')
        return self.cent_event._Event__flag

    def cent_stop(self):
        self.cent_event.clear()
        self._teminate_cent = True
        self.w_neg_array, self.w_naught_array, self.w_pos_array = ([] for i in range(3))
        self.is_centering(None)
        if self.is_scanning():
            self.scan_stop()
        if self.is_meshing():
            self.mesh_stop()

    def cent_start(self, scan_motor_name, angle_motor_name, relmax, relmin, center, angle_pm, angle_o, steps, waittime, Motors):
        self.angle_pm=angle_pm
        if self.is_centering(self.start_stop_PB):
            self.cent_stop()
        self.cent_props = (scan_motor_name, angle_motor_name, center + relmin, center + relmax,
                            angle_o - angle_pm, angle_o, angle_o + angle_pm, steps, waittime, Motors, center, False)
        self._teminate_cent = False
        self.cent_started = False
        self.cent_event.set()  # Just allowing thread to start after setting props

    def cent_command_buff(self, wait_condit, command, commandargs, message, command2=None, command2args=None, waitsleep=1, finalsleep=7.5):
        while wait_condit():
            time.sleep(waitsleep)
        command(*commandargs)
        if not command2 == None:
            command2(*command2args)
        self.set_status(message)
        time.sleep(finalsleep) # The final sleep is very long, and I belive that this was to solve an issue with the EPICS sudomotors, can be reduced if SPEC probably?

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
            if self._terminate_flag: break
            self.w_neg_array, self.w_naught_array, self.w_pos_array = ([] for i in range(3))
            (scan_motor_name, angle_motor_name, cent_scan_start, cent_scan_stop,
             cent_angle_m, cent_angle_o, cent_angle_p, steps, waittime, Motors, cent, terminate) = self.cent_props
            for i in range(len(Motors)):
                motor_inst = Motors[i]
                if scan_motor_name == motor_inst.Name:
                    scan_motor = motor_inst
                elif angle_motor_name == motor_inst.Name:
                    angle_motor = motor_inst
            if not terminate:
                self.is_centering(None)
                # Each of these blocks are nearly identical, they just tell the motor to go to a position and then scan
                # we have waits and opportunities to break out at every stage which makes it look quite odd.
                try:
                    self.cent_command_buff(self.is_moving, self.move_motor, (angle_motor, cent_angle_m, "Absolute"),
                                       "CENTERING: MOVING TO W-", command2=self.move_motor,
                                       command2args=(scan_motor, cent_scan_start, "Absolute"), finalsleep=0)
                except UnboundLocalError:
                    self._error_callback = "No Motor Chosen \nWill Reset"
                    self.cent_event.clear()
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.scan_start, ('Abs', scan_motor_name, cent_scan_start, cent_scan_stop, steps, waittime, Motors), "SCANNING: W-")
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_started = self.is_centering(None)
                self.cent_command_buff(self.is_scanning, self.set_array, ('neg', False), "W- Scan Successful", waitsleep=3,  finalsleep = 2 )
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.move_motor, (angle_motor, cent_angle_o, "Absolute"),
                                       "CENTERING: MOVING TO Wo", command2=self.move_motor,
                                       command2args=(scan_motor, cent_scan_start, "Absolute"))
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.scan_start, ('Abs', scan_motor_name, cent_scan_start, cent_scan_stop, steps, waittime, Motors), "SCANNING: Wo")
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_scanning, self.set_array, ('nau',False), "Wo Scan Successful", waitsleep=3, finalsleep =2)
                if self._terminate_flag: break
                if self._teminate_cent: continue

                self.cent_command_buff(self.is_moving, self.move_motor, (angle_motor, cent_angle_p, "Absolute"),
                                       "CENTERING: MOVING TO W+", command2=self.move_motor,
                                       command2args=(scan_motor, cent_scan_start, "Absolute"))
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.scan_start, ('Abs', scan_motor_name, cent_scan_start, cent_scan_stop, steps, waittime, Motors), "SCANNING: W+")
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_scanning, self.set_array, ('pos', False), "W+ Scan Successful", waitsleep=3, finalsleep =2)
                if self._terminate_flag: break
                if self._teminate_cent: continue
                self.cent_command_buff(self.is_moving, self.move_motor, (angle_motor, cent_angle_o, "Absolute"),
                                       "CENTERING: MOVING BACK", command2=self.move_motor,
                                       command2args=(scan_motor, cent, "Absolute"),  finalsleep = 2 )
                self.cent_event.clear()
                self.is_centering(None)
            print "Centering Complete"
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
        real_name_arr = [x_CB.currentText()] # starting table headers
        (go, x_arr, y_arr, length) = self.cent_grab_data(x_CB, y_CB)
        if not self.old_x == x_arr or not self.old_y == y_arr and go:  # Should we regraph?
            namearr = ['  w-  ', '  wo  ', '  w+  ']  #defining names and vars for the diff data sets
            max_array = [VAR.CENT_NEG_MAXY, VAR.CENT_NAU_MAXY, VAR.CENT_POS_MAXY]
            com_array = [VAR.CENT_NEG_COM, VAR.CENT_NAU_COM, VAR.CENT_POS_COM]
            cwhm_array = [VAR.CENT_NEG_CWHM, VAR.CENT_NAU_CWHM, VAR.CENT_POS_CWHM]
            bar_vars = [VAR.VERT_BAR_NEG_X, VAR.VERT_BAR_NAU_X, VAR.VERT_BAR_POS_X, VAR.VERT_BAR_MULTI_X]
            for i in range(length):
                try:
                    (x, y) = x_arr[i], y_arr[i]
                except IndexError:
                    (x, y) = [0], [0]
                calc = Calculation(x, y) # initializing the calculation class with each data set
                real_name_arr.append(namearr[i])
                self.update_bar_pos(bar_vars[i], x)
                self.monitor.update(max_array[i], calc.x_at_y_max())
                self.monitor.update(com_array[i], calc.COM())
                self.monitor.update(cwhm_array[i], calc.CFWHM())
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
                        plot[i].new_plot(x_arr[i], y_arr[i])
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
        if length >= 3:  # if we have enough data to calculate the center x,y we do it
            if str(calc_CB.currentText()) == 'Max Y':
                pos = self.monitor.get_value(VAR.CENT_POS_MAXY)
                neg = self.monitor.get_value(VAR.CENT_NEG_MAXY)
            elif str(calc_CB.currentText()) == 'COM':
                pos = self.monitor.get_value(VAR.CENT_POS_COM)
                neg = self.monitor.get_value(
                    VAR.CENT_NEG_COM)  # these are center x/y calcs \/ J Synchrotron Rad 2009 16 83-96 sect eqn 7 + 8 -- http://journals.iucr.org/s/issues/2009/01/00/ie5024/ie5024.pdf
            elif str(calc_CB.currentText()) == 'Curser':
                pos = self.monitor.get_value(VAR.VERT_BAR_POS_X)
                neg = self.monitor.get_value(VAR.VERT_BAR_NEG_X)
            elif str(calc_CB.currentText()) == 'CWHM':
                pos = self.monitor.get_value(VAR.CENT_POS_CWHM)
                neg = self.monitor.get_value(VAR.CENT_NEG_CWHM)
            self.monitor.update(VAR.CENT_CENTERED_X, (pos + neg) / (2 * (1 - np.cos(np.degrees(self.angle_pm)))))
            self.monitor.update(VAR.CENT_CENTERED_Y, (pos - neg) / (2 * (np.sin(np.degrees(self.angle_pm)))))

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
            
    """ROCKING"""
    def save_rock_curr(self, filename, x_CB, y_CB):
        pass

    def handle_rock(self):
        while True:
            if self._terminate_flag:break
            self.rock_event.wait()
            if self._terminate_flag:break
            if self._teminate_rock:continue
            (motor_name, startpos, endpos, intervals, count_time, Motors, omit, rock_time) = self.rock_props
            for i in range(len(Motors)):
                motor_inst = Motors[i]
                if motor_name == motor_inst.Name:
                    motor = motor_inst
            start_stop = sorted([startpos, endpos])
            ## This block simply sorts the omitted regions into usable sets of values
            omitted=[]
            lows = [start_stop[0]]
            highs = [start_stop[1]]
            for region in omit:
                lows.sort()
                highs.sort()
                ignore=False
                region_sort = sorted(region)
                if region_sort[0] < lows[0] or region_sort[1] > highs[-1]:
                    print "The omitted region of " + repr(region) + " has been ignored as it is outside of the start/stop range"
                    ignore = True
                for regions in omitted:
                    if regions[0] < region_sort[0] < regions[1]:
                        print "The omitted region of " + repr(region) + " has been ignored as it is inside an omitted zone"
                        ignore = True
                if not ignore:
                    omitted.append(region_sort)
                    lows.append(region_sort[0])
                    highs.append(region_sort[1])
            full_list= sorted(lows+highs)
            regions = []
            tot_size = 0
            for i in range(len(full_list)/2):
                if not full_list[i*2] == full_list[(i*2) +1]:
                    regions.append([full_list[i*2], full_list[(i*2) +1]])
                    tot_size = tot_size + abs(full_list[i*2] - full_list[(i*2) +1])
            # This is the end of the omitted regions code, with the final regions list containing relevant pairs
            try:
                while self.is_moving(motor.Name):
                    time.sleep(.25)
            except UnboundLocalError:
                self.rock_event.clear()
                print "You have not assigned a motor. Aborting"
                continue
            self.start_rock = time.time()
            while rock_time * 60 > time.time() - self.start_rock:  # checking if all the time to rock has passed
                self.is_rocking()
                if self._terminate_flag: break
                if self._teminate_rock: break
                self.rock_progress.setMaximum(int(rock_time*60))
                self.rock_progress.setMinimum(0)
                print time.time() - self.start_rock
                found = False
                while not found:
                    dict = self.checkpos_motor(motor, False)
                    curr = dict['pos']
                    # looping so we can check what the index is and move if its not an end position
                    for index in range(len(start_stop)):
                        if abs(curr) == start_stop[index]:  # where are we?
                            found = True
                            break
                    if not found:
                        self.move_motor(motor, min(start_stop, key=lambda x: abs(x - curr)), 'Absolute')  # Moving to closest point
                        time.sleep(3)
                        while self.is_moving(motor.Name):
                            time.sleep(.25)
                regions_meta = []
                used_pts = 0
                percent_start = 0
                (start, stop, size, percent_size, percent_stop, points, dist) = ([] for v in range(7))
                for i in range(len(regions)):
                    start.append(regions[i][index])
                    stop.append(regions[i][index - 1])
                    size.append(abs(start[i] - stop[i]))
                    percent_size.append(size[i] / tot_size)
                    percent_stop.append(percent_start + percent_size[i])
                    percent_start = (percent_size[i] + percent_start)
                    points.append(math.floor(intervals * percent_size[i]))
                    used_pts = (used_pts + points[i])
                    dist.append(abs(curr - start[i]))
                regions_meta = [start, stop, size, [m - n for m, n in zip(percent_stop, percent_size)], percent_stop, points, dist]
                unused_pts = intervals - used_pts
                for i in range(int(
                        unused_pts)):  # distributing all of the unused points randomly based off of the distributions
                    num = np.random.random()
                    for j in range(len(regions_meta[0])):
                        if regions_meta[4][j] > num > regions_meta[3][j]:
                            regions_meta[5][j] = regions_meta[5][j] + 1
                            used_pts = used_pts + 1
                def sort_by_dist(X, Y = regions_meta[6]):
                    return [x for (y, x) in sorted(zip(Y, X))]
                self.rock_roll(motor, sort_by_dist(regions_meta[0]), sort_by_dist(regions_meta[1]), sort_by_dist(regions_meta[5]), count_time, Motors)
            self.rock_event.clear()
            print "DONE ROCKING"
            self.is_rocking()

    def rock_stop(self, Motors):
        self.rock_event.clear()
        self._teminate_rock = True
        self.is_rocking()
        if self.is_scanning():
            self.scan_stop()
        if self.is_meshing():
            self.mesh_stop()
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Enabled:
                self.motor_stop(Motor_inst)

    def rock_roll(self, motor, startlist, stoplist, intervallist, count_time, Motors):
        """Here is where we should start the rocking and then push it to the plot"""
        self.scan_start('Rock', motor.Name, startlist, stoplist, intervallist, count_time, Motors)
        time.sleep(3)
        while True:
            while self.is_moving() or self.is_scanning():
                time.sleep(.25)
                self.label_motor_currpos.setText(str(self.monitor.get_value(motor.Pos_VAR)))
            time.sleep(1)
            if self.is_moving() or self.is_scanning():  #The check has to get two repeated checks that the motor is not scanning or moving, 1 sec apart
                continue
            else:
                break
        pass

    def rock_start(self, motor_name, startpos, endpos, intervals, count_time, Motors, omit, rock_time, currpos_label, prog_bar):
        self.label_motor_currpos = currpos_label
        self.rock_progress = prog_bar
        if self.is_rocking(self.start_stop_PB_rock):
            self.rock_stop(Motors)
        self.old_rock_x, self.old_rock_y, self.rock_array = ([] for i in range(3))
        self.rock_props = (motor_name, startpos, endpos, intervals, count_time, Motors, omit, rock_time)
        self._teminate_rock = False
        self.rock_started = False
        self.rock_event.set()

    def is_rocking(self, start_stop_PB=None):
        if start_stop_PB == None:
            try:
                start_stop_PB = self.start_stop_PB_rock # Make this specific to rocking
            except UnboundLocalError:
                pass
        else:
            self.start_stop_PB_rock = start_stop_PB
            # This property is checked, so functions here will work
        if self.rock_event._Event__flag:
            start_stop_PB.setText('Stop')
            self.update_CB(self.x_rock_data_CB, self.y_rock_data_CB, 'rock')
        else:
            start_stop_PB.setText('Start')
        return self.rock_event._Event__flag

    def rock_settings(self, motor_name, startpos_SB, stoppos_SB, Motors, wait_time_SB):
        self.rock_wait_time_SB = wait_time_SB
        for i in range(len(Motors)):
            Motor_inst = Motors[i]
            if Motor_inst.Name == motor_name:
                if Motor_inst.Enabled:
                    (min_lim, max_lim) = self.check_limits(Motor_inst)
                    startpos_SB.setRange(min_lim, max_lim)
                    stoppos_SB.setRange(min_lim, max_lim)

    def rock_plotting(self, plot, x_CB, y_CB):
        (go, x, y) = self.rock_grab_data(x_CB, y_CB)
        if not self.old_rock_x == x or not self.old_rock_y == y and go:
            plot.new_plot(x, y)
        (self.old_rock_x, self.old_rock_y) = x, y

    def rock_grab_data(self, x_CB, y_CB):
        try:
            scan_array = self.main_scan_array
            # comb_list = self.rock_array + scan_array
            for elem in scan_array:
                if elem not in self.rock_array:
                    self.rock_array.append(elem)
        except TypeError, e:
            # print e
            pass
        if self.rock_array is None or not self.rock_array:
            return False, [], []
        else:
            (x, y) = [point[x_CB.currentIndex()] for point in self.rock_array], [point[y_CB.currentIndex()] for point in self.rock_array]
            return True, x, y
    """SAVE/LOAD"""
    def save_table(self, filename, table, vert_head, hor_head):
        filedir = self.pos_dir
        curr_time = time.strftime("%b_%d_%Y_%H-%M-%S")
        vert_head = [''] + vert_head
        with open(filedir + '/' + filename + '_' + curr_time + ".csv", 'wb') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(vert_head)
            for row in range(table.rowCount()):
                rowdata = [hor_head[row]]
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item is not None:
                        rowdata.append(
                            unicode(item.text()).encode('utf8'))
                    else:
                        rowdata.append('')
                writer.writerow(rowdata)
        print "Successfully saved " + filename + '_' + curr_time + ".csv" + " In : " + filedir
        # print "Cannot Write, No data acquired"

    """CONDITIONING"""
    def cond_move(self, PV, to, movetype): #should add status check
        currpos = self.monitor.get_value(PV)
        if movetype == 'Relative':
            to = currpos+to
        if self.monitor.put(PV, to):
            print "Moving " + repr(PV)+ " to " + repr(to)

    """ RANDOM UTILITIES """
    def update_bar_pos(self, var, x):
        # print "update bar pos"
        pos = self.monitor.get_value(var)
        try:  # if its not set or outside bounds of graph, then move
            if pos == None:
                v_bar_pos = min(x) + (max(x) - min(x)) / 2.0
            elif not max(x)+(max(x) - min(x))*0.01 > pos:
                v_bar_pos = max(x)
            elif not pos > min(x)-(max(x) - min(x))*0.01:
                v_bar_pos = min(x)
            else:
                v_bar_pos = pos
        except ValueError:
            if pos == None:
                v_bar_pos = 0
            else:
                v_bar_pos = pos
        if not v_bar_pos == pos:
            self.monitor.update(var, v_bar_pos)

    def update_CB(self, x_data_CB, y_data_CB, type, intes_CB=None):
        self.CB_lock.acquire()
        try:
            if type == 'scan':
                self.x_scan_data_CB = x_data_CB
                self.y_scan_data_CB = y_data_CB
            elif type == 'cent':
                self.x_cent_data_CB = x_data_CB
                self.y_cent_data_CB = y_data_CB
            elif type == 'rock':
                self.x_rock_data_CB = x_data_CB
                self.y_rock_data_CB = y_data_CB
            elif type == 'mesh':
                self.x_mesh_data_CB = x_data_CB
                self.y_mesh_data_CB = y_data_CB
            self.scanner_names = self.get_var('SCAN_COLS')
            i=0
            indicies = []
            CBs = [x_data_CB, y_data_CB]
            if not intes_CB == None:
                CBs.append(intes_CB)
            for j, cb in enumerate(CBs):
                if not cb == None:
                    indicies.append(cb.currentIndex())
                    cb.clear()
                    for i in range(len(self.scanner_names)):
                        cb.addItem(self.scanner_names[str(i)])
                    if indicies[j] < len(self.scanner_names):
                        cb.setCurrentIndex(indicies[j])
                else:
                    indicies.append(0)
        finally:
            self.CB_lock.release()

    def send_cmd(self, cmd):
        if self.Spec_sess.connection.isSpecConnected():
            self.Spec_sess.connection.send_msg_cmd(cmd)
            return True
        else:
            return False

    def get_var(self, var_name):
        """Return variable"""
        if self.Spec_sess.connection is not None:
            c = self.Spec_sess.connection.getChannel('var/'+var_name)
            return c.read()

    def init_Spec(self):
        # starting up the Spec server, completed in main_window as monitor needs to load
        self.Spec_man = Spec.connectToSpec(self.Spec_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))
        pass

    def update_filepath(self, filepath, name):
        filepath = str(filepath.text())
        if name == 'scan':
            self.scan_dir = filepath
        elif name == 'cent':
            self.cent_dir = filepath
        elif name == 'rock':
            self.rock_dir = filepath
        elif name == 'pos':
            self.pos_dir = filepath

    def set_status(self, status_msg):
        self.monitor.update(VAR.STATUS_MSG, status_msg)

    def set_server(self, host='10.52.36.1', port='8585'):
        # we set the default server, if none is set. Lazy code.
        self.monitor.update(VAR.SERVER_HOST, host)
        self.monitor.update(VAR.SERVER_PORT, port)
        self.monitor.update(VAR.SERVER_ADDRESS, ''.join((self.monitor.get_value(VAR.SERVER_HOST), ':', self.monitor.get_value(VAR.SERVER_PORT))))

    def terminate(self):
        self._terminate_flag = True
        print "core.terminate called"
        for event in [self.count_event, self.stage_move_event, self.extra_move_event, self.scan_event, self.mesh_event, self.cent_event, self.rock_event]:
            event.set() # allow any blocked threads to terminate
        self.scan_stop()
        sess_list = [  # self.SpecCounter_ic2,
            # self.SpecCounter_pinf,
            self.SpecScan_sess,
            self.SpecMotor_sess,
            self.Spec_sess,
        ]
        for motor in self._SpecMotor_sess:
            sess_list.insert(0, motor)
        for sess in sess_list:
            sess = self.term_sess(sess)
            del sess
        SpecConnectionsManager.SpecConnectionsManager().stop()

    def term_sess(self, sess):
        try:
            connection = sess.connection
            try:
                sess.stop()
            except Exception, e:
                print repr(e)
            if connection is not None:
                try:
                    for key, channel in connection.dispatcher.registeredChannels.iteritems():
                        channel.unregister()
                    connection.abort()
                    pass
                except SpecClientError:
                    print "Successfully disconnected " + repr(sess) + " ?"
                connection.dispatcher.disconnect()
                # connection.disconnect()
            else:
                print repr(connection) + " was not initialized and hence was not closed"
            return sess
        except AttributeError:
            print "Passing on killing session: " + repr(sess)

    def get_motor(self, motor_name, Motors):
        for motor in Motors:
            if motor_name == motor.Name:
                return motor
            elif motor_name == motor.Mne:
                return motor
        return False  # Failed to find Motor

    def error_callback(self, callback):
        self._error_callback = callback

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
        # Modified from http://stackoverflow.com/a/16489955 second comment
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
            return np.average(self.x, weights=(np.array(self.y)-min(self.y)))  # 1D weighted average is a COM
        except ZeroDivisionError:
            return 0

class Calculation3D:
    def __init__(self, x, y, z):
        (self.x, self.y, self.z) = x, y, z
        self.array_z, self.array_labels = self.array_maker()
            
    def COM(self):  # Find COM, then we get indicies back so we have to do some linear "interpolation"
        x_com_cord, y_com_cord = self.com(self.array_z)
        try:
            x_low, y_low = self.array_labels[int(math.floor(x_com_cord)), int(math.floor(y_com_cord))]
            x_high, y_high = self.array_labels[int(math.ceil(x_com_cord)), int(math.ceil(y_com_cord))]
            return (x_low * abs(x_com_cord - math.floor(x_com_cord))) + (x_high * (1 - abs(x_com_cord - math.floor(x_com_cord)))),\
                   (y_low * abs(y_com_cord - math.floor(y_com_cord))) + (y_high * (1 - abs(y_com_cord - math.floor(y_com_cord))))
        except ValueError:
            return None, None
        except TypeError:
            return None, None

    def com(self, inp, labels=None, index=None): # find COM indicies, based on the scipy COM calc, but that is in a later version
        normalizer = meas.sum(inp, labels, index)

        grids = np.ogrid[[slice(0, i) for i in inp.shape]]

        results = [meas.sum(inp * grids[dir].astype(float), labels) / normalizer
                   for dir in range(inp.ndim)]

        if np.isscalar(results[0]):
            return tuple(results)

        return [tuple(v) for v in np.array(results).T]

    def array_maker(self): # Thus makes an array, most of this is error handling
        x, y, z = (self.x, self.y, self.z)
        xyz = zip(x, y, z)
        array_z = np.empty((x.count(x[0]), y.count(y[0])))
        array_labels = np.empty((x.count(x[0]), y.count(y[0])), dtype=object)
        for i, (_x, _y, _z) in enumerate(xyz):
            (x_ind, y_ind) = x[:i].count(_x), y[:i].count(_y)
            try:
                array_z[x_ind, y_ind] = _z - min(z)
                array_labels[x_ind, y_ind] = (_x, _y)
            except IndexError:  # The dimentionality can be incorrect due to an issue with SPEC data output
                adj = False  # This is a crude fix which just adjusts the size of the array up by one to accomidate
                _i, _j = array_z.shape
                if x_ind == _i:
                    a = np.empty((x_ind + 1, _j), dtype=object)
                    b = np.empty((x_ind + 1, _j))
                    a[:-1, :] = array_labels
                    b[:-1, :] = array_z
                    array_labels, array_z = a, b
                    adj = True
                if y_ind == _j:
                    a = np.empty((_i, y_ind + 1), dtype=object)
                    b = np.empty((_i, y_ind + 1))
                    a[:, :-1] = array_labels
                    b[:, :-1] = array_z
                    array_labels, array_z = a, b
                    adj = True
                if adj:
                    array_z[x_ind, y_ind] = _z - min(z)
                    array_labels[x_ind, y_ind] = (_x, _y)
        return array_z, array_labels

    def MAX(self):
        x_ind, y_ind = np.unravel_index(np.argmax(self.array_z), self.array_z.shape)
        try:
            ret_x, ret_y = self.array_labels[x_ind, y_ind]
            return ret_x, ret_y
        except TypeError:
            return None, None

