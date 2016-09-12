#******************************************************************************
#
#  @(#)CSSLogger.py	2.3  09/01/16 CSS
#
#  "splot" Release 2
#
#  Copyright (c) 2013,2014,2015,2016
#  by Certified Scientific Software.
#  All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software ("splot") and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  Neither the name of the copyright holder nor the names of its contributors
#  may be used to endorse or promote products derived from this software
#  without specific prior written permission.
#
#     * The software is provided "as is", without warranty of any   *
#     * kind, express or implied, including but not limited to the  *
#     * warranties of merchantability, fitness for a particular     *
#     * purpose and noninfringement.  In no event shall the authors *
#     * or copyright holders be liable for any claim, damages or    *
#     * other liability, whether in an action of contract, tort     *
#     * or otherwise, arising from, out of or in connection with    *
#     * the software or the use of other dealings in the software.  *
#
#******************************************************************************

import logging

import inspect
import os
import sys
import time

from contextlib import contextmanager
import ctypes
import io
import tempfile
import platform


libc = ctypes.CDLL(None)

pymaj, pymin = platform.python_version_tuple()[0:2]

# get pointers to C-level stdout and stderr
if platform.system() == 'Darwin':
   c_stdout = ctypes.c_void_p.in_dll(libc,'__stdoutp')
   c_stderr = ctypes.c_void_p.in_dll(libc,'__stderrp')
else:  # Linux
   c_stdout = ctypes.c_void_p.in_dll(libc,'stdout')
   c_stderr = ctypes.c_void_p.in_dll(libc,'stderr')

#
#
logger = logging.getLogger("splot")

loglevels = {
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

# In case null logging. this function will redirect ALL
# stderr output (including C-level stderr) to /dev/null
@contextmanager
def allio_redirector(stream):
    original_stderr_fd = sys.stderr.fileno()
    original_stdout_fd = sys.stdout.fileno()

    def _redirect_stdout(to_fd):
        libc.fflush(c_stdout)
        sys.stdout.close()
        os.dup2(to_fd, original_stdout_fd)
        sys.stdout = os.fdopen(original_stdout_fd, 'wb')

    def _redirect_stderr(to_fd):
        libc.fflush(c_stderr)
        sys.stderr.close()
        os.dup2(to_fd, original_stderr_fd)
        sys.stderr = os.fdopen(original_stderr_fd, 'wb')

    saved_stdout_fd = os.dup(original_stdout_fd)
    saved_stderr_fd = os.dup(original_stderr_fd)

    try:
        tfile = tempfile.TemporaryFile(mode='w+b')
        _redirect_stdout(tfile.fileno())
        _redirect_stderr(tfile.fileno())
        yield
        _redirect_stdout(saved_stdout_fd)
        _redirect_stderr(saved_stderr_fd)
        
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(unicode(tfile.read()))
    finally:
        tfile.close()
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)

class StdOutFormatter(logging.Formatter):

    def format(self, record):
        strtime = time.strftime("%H:%M:%S",time.localtime(record.created))
        basefile = os.path.basename(record.pathname)
        level = record.levelname  
        lineno = record.lineno
        funcname = record.funcName
        msg = record.msg

        return "%s |%6s| line:%-4s %-24s (func:%-14s) | %s" % \
                   ( strtime, level, lineno, basefile, funcname, msg)

def addStdOutHandler(level):
    logger = logging.getLogger("splot")
    stdh = logging.StreamHandler(sys.stdout)
    stdf = StdOutFormatter()
    stdh.setFormatter(stdf)
    stdh.setLevel(level)
    logger.addHandler(stdh)


def addFileHandler(filename, level):
    logger = logging.getLogger("splot")
    fileh = logging.FileHandler(filename)
    filef = StdOutFormatter()
    #fileh.setFormatter(logging.Formatter('%(levelname) %(pathname) %(funcName)s line-%(lineno)\t %(message)s'))
    fileh.setFormatter(filef)
    fileh.setLevel(level)
    logger.addHandler(fileh)

def addGraphicsHandler():
    try:
        from CSSLoggerTable import CSSLoggerHandler 
        graphics_handler = CSSLoggerHandler
        logger = logging.getLogger("splot")
        logger.addHandler(graphics_handler)
    except ImportError:
        pass


def noprint(msg, level=None):
    pass

def dprint(msg, level=None):

    if level is None:
        level = logging.DEBUG

    #caller = inspect.stack()[1]
    #frame = caller[0]
    #module = os.path.basename(caller[1])
    #funcname = caller[3]
#
#    varnames = frame.f_code.co_varnames
#
#    try:
#        # object of the first argument to the function (self)
        #self_obj = frame.f_locals[varnames[0]]
        #classname = self_obj.__class__.__name__
    #except:
        #classname = ""
    
    logging.getLogger("splot")._log(level, msg, None)


# The following disables all logging messages coming from SpecClient and
# any other possible loggers
