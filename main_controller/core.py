# System imports
import random
import math
import threading
import time

# App imports
from utils.monitor import KEY as MONITOR_KEY
from utils import Constant

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

    MOTOR_1_MOVETO  = 'var:motor_1_moveto'
    MOTOR_2_MOVETO  = 'var:motor_2_moveto'
    MOTOR_3_MOVETO  = 'var:motor_3_moveto'
    MOTOR_4_MOVETO  = 'var:motor_4_moveto'
    MOTOR_5_MOVETO  = 'var:motor_5_moveto'
    MOTOR_6_MOVETO  = 'var:motor_6_moveto'

    COUNTER_1_COUNT = 'var:counter_1_count'
    COUNTER_2_COUNT = 'var:counter_2_count'

    SERVER_ADDRESS  = 'var:server_address'
    SERVER_HOST     = 'var:server_host'
    SERVER_PORT     = 'var:server_port'

motor_0 = (True, 'Name', 'mne',  """Motor pos VAR""","""Motor moveto VAR""") # This is just a sample entry which fills up slot 0
motor_1 = (True, 'Phi', 'phi',   VAR.MOTOR_1_POS, VAR.MOTOR_1_MOVETO) # YOU MUST ENABLE ALL IN ORDER or numbering will break
motor_2 = (True, 'Eta', 'eta',   VAR.MOTOR_2_POS, VAR.MOTOR_2_MOVETO) # This is super jenky... FIX LATER
motor_3 = (False, 'Name3', 'n3',  VAR.MOTOR_3_POS, VAR.MOTOR_3_MOVETO)
motor_4 = (False, 'Name4', 'n4',  VAR.MOTOR_4_POS, VAR.MOTOR_4_MOVETO)
motor_5 = (False, 'Name5', 'n5',  VAR.MOTOR_5_POS, VAR.MOTOR_5_MOVETO)
motor_6 = (False, 'Name6', 'n6',  VAR.MOTOR_6_POS, VAR.MOTOR_6_MOVETO)

motor_prelist = [motor_0, motor_1, motor_2, motor_3, motor_4, motor_5, motor_6]
motor_list = []
for i in range(len(motor_prelist)):
    motor = motor_prelist[i]
    if motor[0]:
        motor_list.append(motor)
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

        self._counter_timer = threading.Timer(1,self.handle_counter)
        self._counter_timer.start()
        self.count = False

        self.Spec_sess = Spec()



        #Initalizing variables, dont know if theres a better place to
        self.monitor.update(VAR.MOTOR_1_MOVETO, 0)
        self.monitor.update(VAR.MOTOR_2_MOVETO, 0)
        self.monitor.update(VAR.MOTOR_3_MOVETO, 0)
        self.monitor.update(VAR.MOTOR_4_MOVETO, 0)
        self.monitor.update(VAR.MOTOR_5_MOVETO, 0)
        self.monitor.update(VAR.MOTOR_6_MOVETO, 0)

    def init_Spec(self):
        # starting up the Spec server, completed in main_window as monitor needs to load
        Spec.connectToSpec(self.Spec_sess, self.monitor.get_value(VAR.SERVER_ADDRESS))
        self.SpecMotor_sess = SpecMotor()

    def move_motor(self, motor_num, movetype):
        motor_var = motor_list[motor_num]
        motor_name = motor_var[2]
        self.monitor.update(VAR.STATUS_MSG, "Moving Motor " + motor_name)
        pos = self.check_motor_pos(motor_num)
        moveto = self.monitor.get_value(motor_var[4])
        if isinstance(pos, basestring):
            print "Motor " + motor_name + " " + motor_num + " is not initalized"
        elif movetype == 'Relative':
            SpecMotor.moveRelative(self.SpecMotor_sess, moveto)
            print "Moving motor " + motor_name + " to " + repr(moveto + pos)
        elif movetype == 'Absolute':
            SpecMotor.move(self.SpecMotor_sess, moveto)
            print "Moving motor " + motor_name + " to " + repr(moveto)
        else:
            print "Move command FAILED"

    def set_motor_moveto(self,value,motor_num):
        motor_var = motor_list[motor_num]
        self.monitor.update(motor_var[4], int(value))

    def check_motor_pos(self,motor_num):
        motor_var = motor_list[motor_num]
        motor_name = motor_var[2]
        SpecMotor.connectToSpec(self.SpecMotor_sess, motor_name, self.monitor.get_value(VAR.SERVER_ADDRESS))
        try:
            pos = SpecMotor.getPosition(self.SpecMotor_sess)
        except SpecClientError as e:
            print repr(e) + ' unconfig = Motor Name: ' + motor_name +' Motor Num: ' + repr (motor_num)
            pos = 'None'
        if isinstance(pos, basestring) ==  True:
            pass
        else:
            self.monitor.update(motor_var[3], pos)
            print repr(self.monitor.get_value(motor_var[3]))
        return pos

    def checkpos_motor_all(self):
        fail = []
        for i in range(1,len(motor_list)):  # Simply sending all of the "motor_num"s to the check pos command & checking
            fail.append(isinstance(self.check_motor_pos(i), basestring))  # if a string return, if so it has failed
        return any(fail)

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
            """
            try:
#                self._lock.acquire()
#                count_time = SpecCounter.count(self.SpecCounter_sec, 1, self._lock)
                count_time = SpecCounter.count(self.SpecCounter_sec, 5)
            # print "the counter counted for " + repr(count_time)
            except Exception as e:
                print "Counter Failed - sleeping for 5 sec"
                print str(e)
                time.sleep(5)
            finally:
                pass
#                self._lock.release()
            """
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



