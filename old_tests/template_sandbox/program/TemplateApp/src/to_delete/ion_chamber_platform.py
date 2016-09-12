# System Imports
from PyQt4 import QtCore

# App imports
import settings
from utils import Constant
from utils import to_rad
from utils import to_float

from utils.monitor import KEY as MONITOR_KEY

if settings.USE_SIMULATED_PVS:
    BASE = 'breem:'
    REL_WB = 'relWB'
else:
    BASE = ''
    REL_WB ='relativeToWB'

class PV(Constant):
    HEIGHT          = BASE + 'SMTR1605-4-I20-13:mm:sp'
    ANGLE           = BASE + 'ICPlatform1605-4-I20-01:angle'
    HEIGHT_REL_WB   = BASE + 'ICPlatform1605-4-I20-01:height:' + REL_WB

class VAR(Constant):
    CFG_HEIGHT_OFFSET   = 'var:ion:cfg:height_offset'
    CUR_HEIGHT          = 'var:ion:cur:height'


class IonChamberPlatform(QtCore.QObject):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        # Initialize the parent object
        super(IonChamberPlatform, self).__init__(*args, **kwargs)

        pvs = PV.items()
        for pv_name in pvs.itervalues():
            self.monitor.add(pv_name)

        vars = VAR.items()
        for var_name in vars.itervalues():
            self.monitor.add(var_name)

        self.monitor.connect(PV.HEIGHT, self.handle_pv_height)
        self.monitor.connect(VAR.CFG_HEIGHT_OFFSET, self.handle_pv_height)

    def handle_pv_height(self, pv_name):
        value = self.monitor.get_value(PV.HEIGHT, 0)
        offset = self.monitor.get_value(VAR.CFG_HEIGHT_OFFSET, 0)
        height = to_float(value) + to_float(offset)
        self.monitor.put(VAR.CUR_HEIGHT, height)

    def terminate(self):
        self.monitor.disconnect(self)
