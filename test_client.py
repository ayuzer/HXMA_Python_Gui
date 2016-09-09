import os
import inspect
import sys
import time



#Import directories from settings
import settings

# Determine from which directory app is running
cur_frame = inspect.currentframe()
cur_file = inspect.getfile(cur_frame)
base = os.path.split(cur_file)[0]
base_abs = os.path.abspath(base)

# Override settings.BASE_PATH
settings.BASE_PATH = os.path.realpath(base_abs)


for dir in settings.IMPORT_DIRS:
    dir_real = os.path.join(settings.BASE_PATH, dir)
    if dir_real not in sys.path:
        sys.path.insert(0, dir_real)

#
#
#
# from collections import namedtuple
#
# import time
#
# from ctypes import *
#
# class svr_HEAD(Structure):
#     _fields_ = [("magic", c_uint),
#                 ("vers", c_int),
#                 ("size", c_uint),
#                 ("sn", c_uint),
#                 ("sec", c_uint),
#                 ("usec", c_uint),
#                 ("cmd", c_int),
#                 ("type", c_int),
#                 ("rows", c_uint),
#                 ("cols", c_uint),
#                 ("len", c_uint)]
#
# command = 'scaler/.all/count'
#
# #header = namedtuple("svr_head","magic vers size sn sec usec cmd type rows cols len")
#
# magic = int(0xFEEDFACE)
# vers = int(2)
# name_len = c_uint(80)
# size = c_uint(132)
# sn = c_uint(27) #random number as header said it is unimportant
# sec = c_uint(0)#lazy for testing
# usec = c_uint(0)#lazy
# cmd  = int(3) #sending an event
# type = int(8) #sending a string
# rows = c_uint(0)#lazy for testing
# cols = c_uint(0)#lazy for testing
# len = int(len(command))
#
# #head = header(magic = magic, vers = vers, size = size, sn = sn, sec = sec, usec = usec, cmd = cmd, type = type, rows = rows, cols = cols, len = len)
#
# svr_head = svr_HEAD(magic, vers, size, sn, sec, usec, cmd, type, rows, cols,  len)
#
#
#
# import socket

import Spec
import SpecMotor
import SpecCounter


serv_add = ('10.52.36.1',8585)
serv_add_host = '10.52.36.1'
serv_add_port = '8585'
serv_name = 'OPI1606-101'
serv_add_str = ''.join((serv_add_host,':',serv_add_port))
#
# #socket.getaddrinfo(serv_add_host,serv_add_port)
# serv = socket.create_connection(serv_add)
#
# #serv.send(head)
#
# #serv.send(tuple_head)
#
# serv.send(svr_head)
# #serv.send(command)
# #serv.send('001')
#
# print("sucess?",svr_head)
motor_name = 'phi'


Spec_test = Spec.Spec()
SpecMotor_test = SpecMotor.SpecMotor()
SpecCounter_test = SpecCounter.SpecCounter()

class test_client(object):
    def __init__(self,*args, **kwargs):
        self.debug = True
        serv_add = ('10.52.36.1', 8585)
        serv_add_host = '10.52.36.1'
        serv_add_port = '8585'
        serv_name = 'OPI1606-101'
        serv_add_str = ''.join((serv_add_host, ':', serv_add_port))

        self.server_name = serv_add_str
        self.motor_name = 'phi'
    def connect(self):
        Spec.Spec.connectToSpec(Spec_test,self.server_name)
        self.MotorMne = Spec.Spec.getMotorsMne(Spec_test)
        self.MotorNames = Spec.Spec.getMotorsNames(Spec_test)
        if self.debug == True:
            print self.MotorNames
            print self.MotorMne
    def motor_connect(self,motor_name):
        SpecMotor.SpecMotor.connectToSpec(SpecMotor_test,motor_name,self.server_name)
        self.motor_pos = SpecMotor.SpecMotor.getPosition(SpecMotor_test)
        if self.debug == True:
            print self.motor_pos
    def motor_move_rel(self,dist):
        SpecMotor.SpecMotor.moveRelative(SpecMotor_test,dist)
        self.motor_pos = SpecMotor.SpecMotor.getPosition(SpecMotor_test)
        if self.debug == True:
            print self.motor_pos
    def counter_connect(self,count_name):
        SpecCounter.SpecCounter.connectToSpec(SpecCounter_test,count_name,self.server_name)
    def counter_count(self,time):
        self.count = SpecCounter.SpecCounter.count(SpecCounter_test,time)
        print self.count
    def counter_read(self):
        print SpecCounter.SpecCounter.getValue(SpecCounter_test)



test = test_client()
test.connect()
# test.motor_connect('phi')
# test.motor_move_rel(10)
test.counter_connect('sec')
test.counter_count(1)
test.counter_connect('ic2')
test.counter_read()
test.counter_connect('pinf')
test.counter_read()



#serv.close()