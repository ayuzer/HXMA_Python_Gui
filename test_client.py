

from collections import namedtuple

import time

from ctypes import *

class svr_HEAD(Structure):
    _fields_ = [("magic", c_uint),
                ("vers", c_int),
                ("size", c_uint),
                ("sn", c_uint),
                ("sec", c_uint),
                ("usec", c_uint),
                ("cmd", c_int),
                ("type", c_int),
                ("rows", c_uint),
                ("cols", c_uint),
                ("len", c_uint)]

command = 'scaler/.all/count'

#header = namedtuple("svr_head","magic vers size sn sec usec cmd type rows cols len")

magic = int(0xFEEDFACE)
vers = int(2)
name_len = c_uint(80)
size = c_uint(132)
sn = c_uint(27) #random number as header said it is unimportant
sec = c_uint(0)#lazy for testing
usec = c_uint(0)#lazy
cmd  = int(3) #sending an event
type = int(8) #sending a string
rows = c_uint(0)#lazy for testing
cols = c_uint(0)#lazy for testing
len = int(len(command))

#head = header(magic = magic, vers = vers, size = size, sn = sn, sec = sec, usec = usec, cmd = cmd, type = type, rows = rows, cols = cols, len = len)

svr_head = svr_HEAD(magic, vers, size, sn, sec, usec, cmd, type, rows, cols,  len)



import socket

serv_add = ('10.52.36.1',8585)
serv_add_host = '10.52.36.1'
serv_add_port = '8585'
serv_name = 'OPI1606-101'

#socket.getaddrinfo(serv_add_host,serv_add_port)
serv = socket.create_connection(serv_add)

#serv.send(head)

#serv.send(tuple_head)

serv.send(svr_head)
#serv.send(command)
#serv.send('001')

print("sucess?",svr_head)

serv.close()