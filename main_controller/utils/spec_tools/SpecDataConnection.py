#******************************************************************************
#
#  @(#)SpecDataConnection.py	2.3  09/01/16 CSS
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
import sys
import time
import copy
import socket
import weakref
import numpy as np


jsonok = False
try:
    import json
    jsonok = True
except ImportError:
    pass

if not jsonok:
    try:
        import simplejson as json
        jsonok = True
    except ImportError:
        print(
            "Cannot find json module. Only basic functionality will be provided", logging.WARNING)
        print(
            "Hint: Install json or simplejson python module in your system", logging.WARNING)

from SpecClient import SpecEventsDispatcher as Dispatcher
from SpecClient.SpecConnectionsManager import SpecConnectionsManager
from SpecClient.Spec import Spec
from SpecClient.SpecCommand import SpecCommand, SpecCommandA
from SpecClient.SpecChannel import SpecChannel
from SpecClient.SpecVariable import SpecVariable
from SpecClient.SpecMotor import SpecMotorA
from SpecClient.SpecConnection import SpecConnectionDispatcher

try:
    import datashm
    from SharedMemoryData import isupdated
    no_datashm = False
except:
    no_datashm = True

from DataArrayInfo import DataArrayInfo

class SpecDataConnection:

    scand_var = "SCAN_D"
    point_var = "SCAN_PT"
    metadata_var = "SCAN_META"
    plotconfig_var = "SCAN_PLOTCONFIG"
    status_var = "SCAN_STATUS"
    columns_var = "SCAN_COLS"
    npts_var = "NPTS"
    ldt_var = "LDT"
    plotselect_var = "PLOT_SEL"
    hkl_var = "_hkl_col"

    def __init__(self, source, host, specname, variable=None, mode=None):

        self.connected = False
        self.conn_pending = True
        if source:
            self.source = weakref.ref(source)
        else:
            self.source = None

        self.differ_connected = False

        self.specSrv = None
        self.specname = None
        self.host = None
        self.variable = None

        self.server_conn = None
        self.shm_conn = None
        self.server_conn_ok = False
        self.shm_conn_ok = False

        self.data = None
        self.info = None
        self.metadata = {}
        self.filename = None
        self.connMode = None

        self.allMotorMnes = ""

        self.npts = 0
        self.status = "idle"
        self.columns = []

        self.shmmeta_updated = True
        self.shmdata_updated = True

        self.arrayinfo = None

        self.plotconf = None
        self.hkl_columns = -1

        # decide when do we have enough info for first scan (server mode)

        self.ptno = 0
        self.data_channel = None

        self._oldmetadata = None
        self._oldcolumns = None
        self._oldstatus = None

        self.info_completed = False
        self.got_columns = False
        self.got_metadata = False
        self.got_plotselect = False
        self.got_status = False
        self.got_lastpoint = False

        self.motors_followed = {}
        self.followed_motor = None

        self.is_closed = False

        self.array_info = None

        self.connect(host, specname, variable, mode)

    def connect(self, host, specname, variable=None, mode=None):
        """ Connect parameters is a string with the format [host:]specname """

        if no_datashm:
            print(
                "Shared memory functionality not available. Trying to connect via server to localhost", logging.ERROR)
            # host = "localhost"

        #if not host:
            #host = "localhost"

        self.host = host
        self.specname = specname

        if not variable:
            self.variable = self.scand_var
        else:
            self.variable = variable

        if not specname:
            print("No specname given.", logging.ERROR)
            return

        if mode != "shm" or no_datashm:
            # first see if it is possible to connect via server 
            #server_found = self._checkServer(host,specname)

            #print("Server found: %s" % server_found)
            if (host is not None) or mode == "server":
                self.server_conn = self._connectToServer(host, specname)
            else:
                # if server is not running connect by default via shm and wait for spec
                self.shm_conn = self._checkConnectToSHM(specname)
        else:
            self.shm_conn = self._checkConnectToSHM(specname)
            
        if self.server_conn or self.shm_conn:
            self.connected = True

    def _checkServer(self,host,specname):
        found = SpecConnectionDispatcher("%s:%s" % (host,specname)).checkServer()
        return found

    def disconnect(self):
        if self.server_conn:
            print("Disconnecting")
            self.server_conn.dispatcher.disconnect()

    def isRemote(self):
        if self.isServerMode():
            if self.host == 'localhost':
                return False
            local_ip = socket.gethostbyname(socket.gethostname())
            host_ip = socket.gethostbyname(self.host)
            if local_ip == host_ip:
                return False
            else:
                return True
        else:
            return False

    def _checkConnectToSHM(self, specname):

        if not self.variable:
            return False

        if self.variable not in datashm.getarraylist(specname):
            return False

        arrinfo = datashm.getarrayinfo(specname, self.variable)
        self.arrayinfo = DataArrayInfo( datashm.getarrayinfo(specname, self.variable) )
    
        return True

    def checkConnection(self):
        self.shm_conn = self._checkConnectToSHM(self.specname)
        return self.shm_conn

    def isImage(self):
        if not self.arrayinfo: 
            return False

        return self.arrayinfo.isImage()

    def isScanData(self):
        return (self.variable == self.scand_var)

    def isConnected(self):
        return self.shm_conn or self.server_conn

    def isSharedMemory(self):
        return self.shm_conn

    def isServerMode(self):
        return self.server_conn

    def getVariable(self):
        return self.variable

    def getName(self):
        return self.specname

    def getHost(self):
        return self.host

    def getConnectionMode(self):
        if self.isServerMode():
            return "SERVER"
        elif self.isSharedMemory():
            return "SHM"
        else:
            return "NOT CONNECTED"

    def getStatus(self):
        return self.status

    def getDataColumns(self):
        return self.columns

    def getLastPointNo(self):
        return self.npts + 1

    def updateData(self):
        if self.isServerMode():
            self.updateDataServer()
        elif self.isSharedMemory():
            self.updateDataSHM()

    def getData(self, noinfo=False):

        # By default all arrays are bidimensional. With the second dimension index referring
        # to column number.  Row wise, col wise operation are not supported for now.
        # Still for one dimensional arrays special treatment is necessary.

        self.updateData()

        if self.data.any():
            if self.data.shape[0] == 1:  # Make it column wise if we have only one row
                self.data = self.data.transpose()

            if self.isImage():
                return self.data

        if noinfo:
            if self.data.any():
                # index of lastpoint that was not zero
                self.npts = self.data[:, 0].nonzero()[0][-1] 
            else:
                self.npts = 0
            self.metadata = {}

        try:
            return self.data[:self.npts + 1]
        except:
            return self.data

    def getDataPoint(self, ptidx):
        if self.isServerMode():
            ptdata = self.getDataPointServer(ptidx)
            return ptdata
        elif self.isSharedMemory():
            return self.getDataPointSHM(ptidx)
        else:
            print("Wrong connection mode", logging.ERROR)
            return []

    def getFilePath(self):
        return self.getMeta("datapath")

    def getScanNumber(self):
        return self.getMeta("scanno")

    def getMeta(self, keyw):

        if self.isSharedMemory() and self.shmmeta_updated:
            self.updateMeta()

        try:
            return self.metadata[keyw]
        except TypeError:
            return ""
        except KeyError:
            return ""
        except AttributeError:
            return ""

    def hasNewData(self):
        if self.isSharedMemory():

            if isupdated(self.specname, self.variable, self.source().getGraphName()):
                self.shmmeta_updated = True
                self.shmdata_updated = True
                return True
            else:
                return False

    def updateMeta(self):
        if not jsonok:
            return

        _meta = datashm.getmetadata(self.specname, self.variable)

        self._mcols = []

        if (_meta.strip()):
            uncoded_meta = json.loads(_meta)
            if type(uncoded_meta) is list:

                if len(uncoded_meta) >= 2:
                    self._mcols = uncoded_meta[0]
                    self.metadata = uncoded_meta[1]

                if len(uncoded_meta) >= 3:
                    plotconfig = uncoded_meta[2]
                    if plotconfig != self.plotconf:
                        self.source().updatePlotConfig(plotconfig)
                        self.plotconf = copy.copy(plotconfig)

            elif type(uncoded_meta) is dict:
                self.metadata = uncoded_meta
            else:
                print(" cannot decode metadata")

            self.shmmeta_updated = False

    def updateDataSHM(self):
        if self.shmdata_updated:
            self.data = np.array(datashm.getdata(self.specname, self.variable))

    def getDataPointSHM(self, ptidx):
        if self.data.shape[1] == 1:
            return np.array(datashm.getdatacol(self.specname, self.variable, ptidx))
        else:
            return np.array(datashm.getdatarow(self.specname, self.variable, ptidx))

    def updateInfo(self):

        if not jsonok:
            return False

        if self.isSharedMemory() and self.shmmeta_updated:
            self.updateMeta()

        _jinfo = datashm.getinfo(self.specname, self.variable).strip()

        infoOk = False

        self.columns = []

        if _jinfo:
            try:
                uncoded_info = json.loads(_jinfo)
                if type(uncoded_info) is list:
                    if len(uncoded_info) == 2:   # macro providing only npts and status
                        _npts, _status = uncoded_info
                        _cols = self._mcols
                    elif len(uncoded_info) == 3:
                        _npts = uncoded_info[0]
                        _status = uncoded_info[1]
                        if self._mcols:   # we got the info from metadata, trust it
                            _cols = self._mcols
                        else:
                            _cols = uncoded_info[2]

                self.npts = int(_npts)
                self.status = _status
                for idx in range(len(_cols)):
                    self.columns.append(_cols[str(idx)])
                infoOk = True
            except:
                import traceback
                print("cannot decode info.  %s " % traceback.format_exc())

        return infoOk

    def getSHMVariableList(self):
        varlist = datashm.getarraylist(self.specname)
        return varlist

    # Server callbacks
    def _connectToServer(self, host, specname):

        server_conn = SpecConnectionsManager(
            False).getConnection("%s:%s" % (host, specname))
        #server_conn = SpecConnection("%s:%s" % (host,specname))

        if server_conn:
            # if we use an already existing spec connection the dispatcher will not send events.
            # but as the connection is already available. we do not need them
            if server_conn.dispatcher.connected:
                self.differ_connected = True
            else:
                Dispatcher.connect(server_conn, 'connected',
                                   self.server_connected)
                Dispatcher.connect(server_conn, 'disconnected',
                                   self.server_disconnected)

        return server_conn

    def server_connected(self):

        #print(" *************** spec server is now connected")

        self.server_conn_ok = True
        self.conn_pending = True

        self.server_conn.registerChannel('status/ready', self.statusReady,
                                         dispatchMode=Dispatcher.FIREEVENT)
        self.server_conn.registerChannel('status/shell', self.statusShell,
                                         dispatchMode=Dispatcher.FIREEVENT)

        if self.isScanData():
            self.conn_vars = [
                [self.columns_var,    self.columnsChanged,
                    Dispatcher.UPDATEVALUE, False],
                [self.metadata_var,   self.metadataChanged,
                    Dispatcher.UPDATEVALUE, False],
                [self.plotconfig_var, self.plotconfigChanged,
                 Dispatcher.UPDATEVALUE, False],
                # [ self.plotselect_var, self.plotSelectionChanged, Dispatcher.UPDATEVALUE, False ],
                [self.status_var,     self.statusChanged,
                 Dispatcher.FIREEVENT, False],
                [self.point_var,      self.gotScanPoint,
                 Dispatcher.FIREEVENT, False],
            ]

            self.data_channel = SpecVariable(
                self.scand_var, "%s:%s" % (self.host, self.specname))
            self.npts_channel = SpecVariable(
                self.npts_var,  "%s:%s" % (self.host, self.specname))
            self.ldt_channel = SpecVariable(
                self.ldt_var,  "%s:%s" % (self.host, self.specname))

            self.hkl_columns = SpecVariable(
                self.hkl_var, "%s:%s" % (self.host, self.specname)).getValue()

            if self.conn_pending:
                self.checkVariables()
        else:
            self.conn_pending = False
            self.data_channel = SpecVariable(
                self.variable, "%s:%s" % (self.host, self.specname))

        self.source().connected()

    def run(self):
        if self.differ_connected:
            self.server_connected()

        self.source().startWatch()

    def server_disconnected(self):
        self.server_conn_ok = False
        self.source().disconnected()

    def server_close(self):
        if self.server_conn_ok:
            self.is_closed = True
            # if self.isScanData():
            # for varinfo in self.conn_vars:
            #varname, varcb, varupdmode, varstat = varinfo
            #self.server_conn.unregisterChannel('var/%s' % varname, varcb)

    def checkVariables(self):

        self.conn_pending = False

        for varinfo in self.conn_vars:
            varname, varcb, varupdmode, varstat = varinfo
            if not varstat:
                try:
                    #print( "Register with variable %s." % varname)
                    #var = SpecVariable(varname, "%s:%s" % (self.host, self.specname) ).getValue()
                    self.server_conn.registerChannel(
                        'var/%s' % varname,    varcb, dispatchMode=varupdmode)
                    varinfo[3] = True
                except:
                    import traceback
                    logmsg = traceback.format_exc()
                    print("Cannot register with variable %s." %
                           varname, logging.ERROR)
                    print(logmsg, logging.DEBUG)
                    self.conn_pending = True
                    varinfo[3] = False
                    break
            else:
                pass

    def variableDataUpdated(self, data):
        self.data = data

    def updateDataServer(self):
        if self.data_channel:
            self.data = self.data_channel.getValue()
            if self.isScanData():
                #self.npts = self.npts_channel.getValue()
                self.npts = self.ldt_channel.getValue()

    def getDataPointServer(self, ptidx):
        self.updateData()
        point_val = self.data[ptidx, :]
        return point_val

    def getMotorPosition(self, mne):
        try:
            motpos = SpecMotorA(mne, "%s:%s" %
                                (self.host, self.specname)).getPosition()
            return motpos
        except:
            return None

    def followMotor(self, mne):

        if not self.server_conn_ok:
            return

        channel_name = 'motor/%s/position' % mne
        self.server_conn.registerChannel(channel_name, self.scanMotorPositionChanged,
                                         dispatchMode=Dispatcher.FIREEVENT)
        self.followed_motor = mne
        self.motors_followed[mne] = True

    def unfollowMotor(self, mne):
        if not self.server_conn_ok:
            return

        if mne in self.motors_followed and self.motors_followed[mne] == True:
            channel_name = 'motor/%s/position' % mne
            # self.server_conn.unregisterChannel(channel_name)
            self.motors_followed[mne] = False

    def scanMotorPositionChanged(self, position):
        if self.is_closed:
            return

        self.source().scanMotorPositionChanged(self.followed_motor, position)

    def getHKLColumns(self):
        return self.hkl_columns

    def metadataChanged(self, metadata):

        if self.is_closed:
            return

        self.got_metadata = True
        if self._oldmetadata == metadata:
            return

        self._oldmetadata = metadata
        self.metadata = metadata

        if 'allmotorm' in self.metadata:
            allmotorm = self.metadata['allmotorm']
            if allmotorm != self.allMotorMnes:
                self.source().updateMotorTable(allmotorm)
                self.allMotorMnes = allmotorm

        if not self.info_completed:
            self.checkInfo()

    def plotconfigChanged(self, plotconfig):
        if self.is_closed:
            return

        if plotconfig != self.plotconf:
            self.source().updatePlotConfig(plotconfig)
            self.plotconf = copy.copy(plotconfig)

    def columnsChanged(self, columns):

        if self.is_closed:
            return

        if self._oldcolumns == columns:
            return

        self._oldcolumns = copy.copy(columns)

        self.got_columns = True

        self.columns = [0, ] * len(columns)
        for i in columns:
            try:
                self.columns[int(i)] = columns[i]
            except:
                print("Problem with columns variable", logging.ERROR)
                return

        if not self.info_completed:
            self.checkInfo()

        self.source().setColumnNames(self.columns)

    def plotSelectionChanged(self, selection):
        self.got_plotselect = True

        if self.plotconf is None:
            self.source().plotSelectionChanged(selection)

        if not self.info_completed:
            self.checkInfo()

    def statusChanged(self, newstatus):
        if self.is_closed:
            return

        self.got_status = True
        if self._oldstatus == newstatus:
            return

        self._oldstatus = newstatus
        self.source().statusChanged(newstatus)

        if not self.info_completed:
            self.checkInfo()

    def gotScanPoint(self, pointval):

        if self.is_closed:
            return
        self.ptno += 1

        if not jsonok:
            return

        try:
            pointno, point = json.loads(pointval)
            self.source().addScanPoint(pointno, point)
        except:
            import traceback
            traceback.print_exc()
            print("Cannot decode scan point %s" % pointval, logging.ERROR)
            return

        self.got_lastpoint = True
        if not self.info_completed:
            self.checkInfo()

    def statusReady(self, newstatus):
        if self.is_closed:
            return

        self.source().statusReady(newstatus)

        if self.conn_pending:
            self.checkVariables()

    def statusShell(self, newstatus):
        if self.is_closed:
            return

        self.source().statusShell(newstatus)

    def checkInfo(self):
        #                      self.got_plotselect  and
        self.info_completed = self.got_columns     and \
            self.got_metadata    and \
            self.got_status      and \
            self.got_lastpoint

        if self.info_completed:
            self.source().newScan()

    def abort(self):
        if not self.isServerMode():
            return

        self.server_conn.abort()

    def sendCommand(self, cmdstring):
        if not self.isServerMode():
            return

        cmd = SpecCommand(cmdstring, self.server_conn)
        return cmd()

    def sendCommandA(self, cmdstring):
        if not self.isServerMode():
            return

        cmd = SpecCommandA(cmdstring, self.server_conn)
        cmd()


def mainConnection(connectpars):
    specConn = SpecDataConnection(connectpars)
    print("   SHM: ", specConn.shm_conn)
    print("SERVER: ", specConn.server_conn)

    print(specConn.getDataColumns())

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:
        print("Usage: %s spec" % sys.argv[0])
        sys.exit(0)

    spec = sys.argv[1]
    mainConnection(spec)
