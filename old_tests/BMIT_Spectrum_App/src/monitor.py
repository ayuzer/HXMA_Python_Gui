# System imports
import copy

# Library imports
from PyQt4 import QtCore
from epics import PV

# Application imports
from emitter import Emitter

class EpicsPVMarker(object):
    pass

# The EPICS_PV_MARKER is used to differentiate between EPICS and LOCAL
# vars in the add statement.  LOCAL vars can be added with any value
# (including None)
EPICS_PV_MARKER = EpicsPVMarker()

class KEY(object):
    KWARG           = 'monitor'
    LOCAL_PREFIX    = '_local_'
    PV_NAME         = 'pvname'      # Defined by pyepics
    PV_CONNECTED    = 'conn'        # Defined by pyepics
    PV_VALUE        = 'value'       # Defined by pyepics

class EpicsMonitor(QtCore.QObject):
    """
    This class caches EPICS PV data and calls user registered callbacks
    when PVs change.

    It also allows "local" (i.e., non-EPICS) variables to be defined.
    The usage of these local variables follows the same pattern as the
    EPICS variables.  That is, clients can register callbacks for EPICS
    and/or non-EPICS variables using the same pattern.
    """
    SIGNAL = QtCore.pyqtSignal(unicode)

    def __init__(self, *args, **kwargs):

        super(EpicsMonitor, self).__init__(*args, **kwargs)

        self.local_dict = {}
        self.pv_data = {}
        self.pv_dict = {}
        self.pv_connected = {}
        self.callback_dict = {}
        self.emitter = Emitter()

        self.SIGNAL.connect(self.signal_handler)

    def epics_version(self):
        import epics
        from epics.ca import find_libca

        dllname = find_libca()
        # print "DLL NAME", dllname
        return epics.__version__, dllname

    def emit(self, signal, value):
        self.emitter.emit(signal, value)

    def signal_handler(self, name):

        name = str(name)
        callbacks = self.callback_dict.get(name, [])

        if len(callbacks) > 5:
            print "MONITOR: Warning: callbacks for %s: %d" % \
                  (name, len(callbacks))

        for func in callbacks:
            func(name)
            #try:
            #    func(name)

            #except Exception, e:
            #    print "MONITOR: Exception: %s calling callback for %s" % \
            #          (str(e), name)
            #    print "  CALLBACK: %s" % repr(func)

    def get_callback_list(self):
        """
        This method returns a dict of registered callbacks.
        It was added as a debugging tool
        """
        result = {}

        for key, value in self.pv_dict.iteritems():
            callbacks = self.callback_dict.get(key, [])
            if len(callbacks):
                result[key] = callbacks

        for key, value in self.local_dict.iteritems():
            callbacks = self.callback_dict.get(key, [])
            if len(callbacks):
                result[key] = callbacks

        return result

    def print_unconnected(self):
        """
        Prints unconnected EPICs PVs.  This is done for debugging as
        all EPICs PVs should be connected.
        """
        for key, value in self.pv_dict.iteritems():
            result = value.wait_for_connection(timeout=0)
            if result is False:
                print "----------------------------------------"
                print "NOT CONNECTED '%s': %s" % (key, value)

    def get_pv_list(self):
        """
        Returns a list of all PVs
        """
        return [name for name in self.pv_dict.iterkeys()]

    def is_monitored(self, pv_name):
        local_list = self.get_local_list()
        if pv_name in local_list:
            return True

        pv_list = self.get_pv_list()
        if pv_name in pv_list:
            return True

        return False

    def is_local(self, pv_name):

        local_list = self.get_local_list()
        if pv_name in local_list:
            return True

        return False

    def get_local_list(self):
        """
        Returns a list of all local vars
        """
        return [name for name in self.local_dict.iterkeys()]

    def print_list(self):

        for key, value in self.pv_dict.iteritems():
            print "----------------------------------------"
            print "MONITOR '%s': %s" % (key, value)
            print "  VALUE: %s" % repr(self.get_value(key))

            callbacks = self.callback_dict.get(key, [])
            for callback in callbacks:
                print "  CALLBACK: %s" % callback

        for key, value in self.local_dict.iteritems():
            print "MONITOR (LOCAL) '%s': %s" % (key, value)
            callbacks = self.callback_dict.get(key, [])
            for callback in callbacks:
                print "  CALLBACK: %s" % callback

        self.print_unconnected()

    def stop(self):
        print "MONITOR: stop() called"
        self.emitter.stop()

    def start(self):
        """
        Emit a signal for each local variable of EPICS PV.
        this will call registered callbacks and allow clients
        to initialize themselves with monitored variable values.
        """
        for name in self.local_dict.iterkeys():
            self.emit(self.SIGNAL, name)

        # Connect to actual EPICs PVs
        for name in self.pv_dict.iterkeys():

            pv = self.pv_dict.get(name)
            if pv is None:
                # Just creating PV object but not accessing any of its
                # properties will not cause any network traffic
                # (i.e. connection (attempt) to the pv).
                pv = PV(name, connection_callback=self.connection_callback)
                self.pv_dict[name] = pv

                # print "ADDING CALLBACK FOR PV: %s" % name
                pv.add_callback(self.pv_callback, index=0)

            else:
                self.emit(self.SIGNAL, name)

    def reset(self, name):
        """
        Sometimes on startup a PV init is missed.  I have no idea
        why this happens (it is very rare).  Perhaps there is a race
        condition that causes a signal to be missed.  At any rate,
        this method call pv.info (the idea being that the PV will be
        queried across the network if necessary), then the callback
        is triggered.  This should signal the client to (re)read the PV
        """
        print "MONITOR: reset(%s) called" % name
        pv = self.pv_dict.get(name)
        if not name:
            print "MONITOR: cannot find PV '%s' for reset" % name
            return

        print pv.info
        pv.run_callback(0)

    def call_callbacks(self, name):

        # print "monitor.call_callbacks(): emitting SIGNAL(%s)" % name
        self.emit(self.SIGNAL, name)
        return True

    def put(self, name, value):
        if self.local_dict.has_key(name):
            return self.update(name, value)

        pv = PV(name)
        pv.put(value)

    def update(self, name, value):

        #print "monitor %s %s " % (name, repr(value))
        if self.local_dict.has_key(name):
            if self.local_dict[name] == value:
                #print "monitor: no need to update %s %s" % (name, repr(value))
                return False

        self.local_dict[name] = value
        self.pv_connected[name] = True

        # print "monitor.update(): emitting SIGNAL(%s) (value: %s)" % (name, repr(value))
        self.emit(self.SIGNAL, name)

        return True

    def add(self, pvs, var=EPICS_PV_MARKER):
        """
        Add variable to list of monitored variables
        """
        local_flag = False

        if not isinstance(var, EpicsPVMarker):
            local_flag = True

        if not local_flag:
            if not isinstance(pvs, list):
                if pvs.startswith(KEY.LOCAL_PREFIX):
                    print "monitor.add(): Local variable: '%s'" % pvs
                    local_flag = True

        if local_flag:
            # Assume this is a "local" variable (i.e., not EPICS)
            if self.local_dict.has_key(pvs):
                print "monitor.add(%s): WARNING: re-adding: ignoring new value" % pvs
                return
            self.local_dict[pvs] = var
            self.pv_connected[pvs] = True
            return

        if not isinstance(pvs, list):
            pvs = [pvs]

        for name in pvs:
            if not self.pv_dict.has_key(name):
                if self.local_dict.has_key(name):
                    raise ValueError("PV '%s' already a local var" % name)

                self.pv_dict[name] = None
            else:
                # Already know about this PV
                pass

    def connection_callback(self, *args, **kwargs):

        # print "MONITOR: connection callback called"
        # print "ARGS", args
        # print "KWARGS", kwargs

        name = unicode(kwargs.get(KEY.PV_NAME))
        connected = kwargs.get(KEY.PV_CONNECTED)
        self.pv_connected[name] = connected

        # print "monitor.connection_callback(): emitting SIGNAL(%s)" % name
        self.emit(self.SIGNAL, name)

    def pv_callback(self, **kwargs):
        """
        Handle PV update callback.
        """

        # Determine the name of the PV
        name = unicode(kwargs.get(KEY.PV_NAME))

        # Store the results returned in the callback kwargs in a local dict
        self.pv_data[name] = kwargs
        self.emit(self.SIGNAL, name)

    def get_connected(self, name):
        return self.pv_connected.get(name, None)

    def get_data(self, name):
        data = self.pv_data.get(name, None)
        if data:
            data[KEY.PV_CONNECTED] = self.get_connected(name)

        return data

    def get_value(self, name, default=None):
        if not self.pv_connected.get(name, False):
            return None

        data = self.pv_data.get(name)

        if data:
            return data.get(KEY.PV_VALUE)

        data = self.local_dict.get(name)

        if data is not None:
            if isinstance(data, dict):
                return copy.copy(data)
            return data

        if default is not None:
            return default

        #print "monitor.get_value(): Failed to find results for >%s< (%s)" % \
        #      (name, type(name))
        #
        #for key, value in self.pv_data.iteritems():
        #    print "These are the EPICs keys: >%s<" % key
        #    print "this is the value", value
        #
        #for key, value in self.local_dict.iteritems():
        #    print "These are the LOCAL keys: >%s< (%s)" % (key, type(key))
        #    print "this is the value", value

    def disconnect(self, caller):

        print "MONITOR: disconnect(%s) ID: %d" % (caller, id(caller))

        # Remove all callbacks that were registered by the caller
        for name, callbacks in self.callback_dict.iteritems():
            updated = [c for c in callbacks if id(c.__self__) != id(caller)]
            self.callback_dict[name] = updated

    def disconnect_handler(self, name, func):

        name = unicode(name)
        callbacks = self.callback_dict.get(name, [])

        try:
            callbacks.remove(func)
            self.callback_dict[name] = callbacks
        except:
            pass

    def connect(self, name, func):
        """
        This registers a callback that is called whenever a
        variable value changes (or monitor.start() is called)
        """
        name = unicode(name)

        # Get list of registered callbacks
        callbacks = self.callback_dict.get(name, [])

        # print "MONITOR: PV: '%s': Adding callback %s" % (name, repr(func))

        # Add the specified function to the list of callbacks to call
        callbacks.append(func)

        # Filter out duplicate callbacks
        self.callback_dict[name] = list(set(callbacks))
