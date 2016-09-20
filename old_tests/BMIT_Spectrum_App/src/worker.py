# System imports
import math

# Library imports
from PyQt4 import QtCore

# Application imports
from utils import Constant
from utils import to_rad

from monitor import KEY as MONITOR_KEY
from filter_pvs import VAR, WBT_STATUS
from filter_pvs import PV, CT_MONO_STATUS, KES_MONO_STATUS
from settings import ID_CT_MONO_THICKNESS_MM_C1
from settings import ID_CT_MONO_THICKNESS_MM_C2
from settings import ID_KES_MONO_THICKNESS_MM

FILTER_MANAGER_SETTINGS_KEY = 'FilterManager'

# This is a total hack to support the WBT (White Beam Transport)
# functionality that was not included in the original design
WBT_MAP = {
    'ID-W4-M' : WBT_STATUS.OUT,
    'ID-W5-M' : WBT_STATUS.OUT,
    'ID-W6-M' : WBT_STATUS.IN,
    'ID-W7-M' : WBT_STATUS.IN,
}

class ID_MONO_STATUS(Constant):
    UNKNOWN = 0
    CT_IN   = 1
    KES_IN  = 2
    NO_MONO = 3
    BOTH    = 4

ID_MONO_MAP = {
    'ID-W9-M'   : [ID_MONO_STATUS.BOTH, ID_MONO_STATUS.CT_IN],
    'ID-W10-M'  : [ID_MONO_STATUS.BOTH, ID_MONO_STATUS.CT_IN],
    'ID-W11-M'  : [ID_MONO_STATUS.BOTH, ID_MONO_STATUS.KES_IN],
}

MONO_STATUS_MAP = {
    (CT_MONO_STATUS.IN,     KES_MONO_STATUS.IN  )       : ID_MONO_STATUS.BOTH,
    (CT_MONO_STATUS.IN,     KES_MONO_STATUS.OUT )       : ID_MONO_STATUS.CT_IN,
    (CT_MONO_STATUS.IN,     KES_MONO_STATUS.MOVING)     : ID_MONO_STATUS.CT_IN,
    (CT_MONO_STATUS.IN,     KES_MONO_STATUS.IN_BETWEEN) : ID_MONO_STATUS.CT_IN,
    (CT_MONO_STATUS.OUT,    KES_MONO_STATUS.IN  )       : ID_MONO_STATUS.KES_IN,
    (CT_MONO_STATUS.OUT,    KES_MONO_STATUS.MOVING)     : ID_MONO_STATUS.NO_MONO,
    (CT_MONO_STATUS.OUT,    KES_MONO_STATUS.IN_BETWEEN) : ID_MONO_STATUS.NO_MONO,
    (CT_MONO_STATUS.OUT,    KES_MONO_STATUS.OUT )       : ID_MONO_STATUS.NO_MONO,
}

class SimulatedFilter(QtCore.QObject):
    """
    This 'simulated' filter makes the carbon filters that have a  'closed'
    PV appear like the other filters that have multiple options.
    This reduces the 'special case' handling required.
    """
    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        del kwargs[MONITOR_KEY.KWARG]

        super(SimulatedFilter, self).__init__(*args, **kwargs)

    def set_pvs(self, pvs):

        self.pv_mat     = pvs[0]
        self.pv_thk     = pvs[1]
        self.pv_closed  = pvs[2]
        self.pv_mat_1   = pvs[3]
        self.pv_mat_2   = pvs[4]
        self.pv_thk_1   = pvs[5]
        self.pv_thk_2   = pvs[6]

        # These are the actual PVs on the beamline
        for pv in [self.pv_mat, self.pv_thk, self.pv_closed]:
            self.monitor.add(pv)
            self.monitor.connect(pv, self.handle_pv)

        # These are the "local" PVs of the simulated filter
        for pv in [self.pv_mat_1, self.pv_mat_2, self.pv_thk_1, self.pv_thk_2]:
            self.monitor.add(pv, 0)

    def handle_pv(self, name):

        material  = self.monitor.get_value(self.pv_mat)
        thickness = self.monitor.get_value(self.pv_thk)
        closed    = self.monitor.get_value(self.pv_closed)

        if closed == 1:
            # The filter is in the beamline
            mat_1 = material
            mat_2 = 'none'
            thk_1 = thickness
            thk_2 = 0.0

        elif closed == 0:
            # The filter is NOT in the beamline
            mat_2 = material
            mat_1 = 'none'
            thk_2 = thickness
            thk_1 = 0.0

        else:
            # raise ValueError("Unexpected value for closed: %d" % closed)
            # This can get called with a value of None when the system
            # is initializing
            return

        self.monitor.update(self.pv_mat_1, mat_1)
        self.monitor.update(self.pv_mat_2, mat_2)
        self.monitor.update(self.pv_thk_1, thk_1)
        self.monitor.update(self.pv_thk_2, thk_2)

    def terminate(self):

        self.monitor.disconnect(self)

class FilterManager(QtCore.QObject):
    """
    This object computes the spectrum based on the selected filters.
    It does not know anything about the GUI
    """

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs[MONITOR_KEY.KWARG]
        self.mat_mgr = kwargs['mat_mgr']

        del kwargs['mat_mgr']
        del kwargs[MONITOR_KEY.KWARG]

        super(FilterManager, self).__init__(*args, **kwargs)

        # This snippet adds to monitor all PVs in 'PV' class
        add_pv_dict = PV.items()
        for pv in add_pv_dict.itervalues():
            self.monitor.add(pv)

        self.monitor.connect(PV.ID_MONO_IN_CT,  self.handle_pv_id_mono_in)
        self.monitor.connect(PV.ID_MONO_IN_KES, self.handle_pv_id_mono_in)

        self.monitor.add(VAR.ID_MONO_ACTUAL, ID_MONO_STATUS.UNKNOWN)
        self.monitor.add(VAR.ID_MONO_USE, ID_MONO_STATUS.UNKNOWN)

        self.monitor.add(VAR.ID_MONO_CT_THICKNESS_C1, ID_CT_MONO_THICKNESS_MM_C1)
        self.monitor.add(VAR.ID_MONO_CT_THICKNESS_C2, ID_CT_MONO_THICKNESS_MM_C2)

        id_ct_pvs = [
            PV.ID_MONO_CT2_BRAGG,
            PV.ID_MONO_CT1_BRAGG,
            PV.ID_MONO_CT2_LATTICE,
            PV.ID_MONO_CT1_LATTICE
        ]

        for pv in id_ct_pvs:
            self.monitor.connect(pv, self.handle_pv_id_mono_ct)

        id_kes_pvs = [
            PV.ID_MONO_KES_BRAGG_ANGLE,
            PV.ID_MONO_KES_LATTICE_ANGLE
        ]

        for pv in id_kes_pvs:
            self.monitor.connect(pv, self.handle_pv_id_mono_kes)

        self.monitor.add(VAR.ID_MONO_KES_THICKNESS, ID_KES_MONO_THICKNESS_MM)

        self.error_callback = None

    def handle_pv_id_mono_kes(self, pv_name):
        """
        Compute nominal distance through the crystal
        """
        mid_dist = ID_KES_MONO_THICKNESS_MM / 2.0

        try:
            bragg = to_rad(float(self.monitor.get_value(PV.ID_MONO_KES_BRAGG_ANGLE)))
            lattice = to_rad(float(self.monitor.get_value(PV.ID_MONO_KES_LATTICE_ANGLE)))

            dist_a = mid_dist / math.cos(abs(lattice) + abs(bragg))
            dist_b = mid_dist / math.cos(abs(lattice) - abs(bragg))

            result = dist_a + dist_b

        except Exception, e:
            print "Exception computing KES thickness: %s" % str(e)
            result = ID_KES_MONO_THICKNESS_MM

        self.monitor.update(VAR.ID_MONO_KES_THICKNESS, result)

    def handle_pv_id_mono_ct(self, pv_name):
        """
        This method computes the thickness of the CT mono crystals
        """
        self.compute_id_ct_thickness(
            PV.ID_MONO_CT1_BRAGG,
            PV.ID_MONO_CT1_LATTICE,
            ID_CT_MONO_THICKNESS_MM_C1,
            VAR.ID_MONO_CT_THICKNESS_C1
        )

        self.compute_id_ct_thickness(
            PV.ID_MONO_CT2_BRAGG,
            PV.ID_MONO_CT2_LATTICE,
            ID_CT_MONO_THICKNESS_MM_C2,
            VAR.ID_MONO_CT_THICKNESS_C2
        )

    def compute_id_ct_thickness(self, pv_bragg, pv_lattice, nominal, pv_result):

        mid_dist = nominal / 2.0

        try:
            bragg = to_rad(float(self.monitor.get_value(pv_bragg)))
            lattice = to_rad(float(self.monitor.get_value(pv_lattice)))

            dist_a = mid_dist / math.cos(abs(lattice) + abs(bragg))
            dist_b = mid_dist / math.cos(abs(lattice) - abs(bragg))

            result = dist_a + dist_b

        except Exception, e:
            print "Exception computing CT thickness: %s" % str(e)
            result = nominal

        self.monitor.update(pv_result, result)

    def handle_pv_id_mono_in(self, pv_name):
        """
        Read the mono statuses and distill them into a local PV
        """
        ct_mono_status = self.monitor.get_value(PV.ID_MONO_IN_CT)
        try:
            ct_mono_status = int(ct_mono_status)
        except Exception, e:
            print "Exception: %s (ct_mono_status: %s)" % (repr(e), repr(ct_mono_status))
            ct_mono_status = CT_MONO_STATUS.UNKNOWN

        kes_mono_status = self.monitor.get_value(PV.ID_MONO_IN_KES)

        try:
            kes_mono_status = int(kes_mono_status)
        except Exception, e:
            print "Exception: %s (kes_mono_status: %s)" % (repr(e), repr(kes_mono_status))
            kes_mono_status = KES_MONO_STATUS.UNKNOWN

        mono_status = MONO_STATUS_MAP.get((ct_mono_status, kes_mono_status), ID_MONO_STATUS.UNKNOWN)
        self.monitor.update(VAR.ID_MONO_ACTUAL, mono_status)

    def set_error_callback(self, error_callback):
        self.error_callback = error_callback

    def error(self, msg):
        print msg
        if self.error_callback:
            self.error_callback(msg)

    def set_settings(self, settings):
        data = settings.get(FILTER_MANAGER_SETTINGS_KEY, {})
        self.monitor.update(VAR.OTHER_FILTERS, data)

    def get_settings(self, settings):
        data = self.monitor.get_value(VAR.OTHER_FILTERS)
        settings[FILTER_MANAGER_SETTINGS_KEY] = data
        return settings

    def update_other_filters(self, name, value):

        print "update_other_filters() --> '%s' value '%s'" % (name, value)
        value_in = value
        valid = False
        data = self.monitor.get_value(VAR.OTHER_FILTERS)
        existing = data.get(name)
        parts = name.split('-')

        try:
            value = value.strip()
        except:
            pass

        if parts[2] == 'M':
            if value == '':
                valid = True
            else:
                value_new = self.mat_mgr.resolve_material(value)
                if value_new is None:
                    possible = self.mat_mgr.resolve_material(value, return_possible=True)
                    if possible and len(possible) > 1:

                        possible = sorted(possible)

                        msg = "Unable to determine material.  " \
                            "Possible matches include:\n\n"
                        for item in possible:
                            msg = msg + "%s\n" % item

                        raise ValueError(msg)
                        # self.error(msg)

                    else:
                        msg = "Unknown/Unsupported Material '%s'" % value
                        raise ValueError(msg)
                        # self.error("Unknown/Unsupported Material '%s'" % value)

                else:
                    # print "value '%s' is valid" % value_new
                    valid = True
                    value = value_new

        if parts[2] == 'T':
            if value.strip() == '':
                value = '0.0'
                valid = True
            else:
                try:
                    test = float(value)
                    valid = True
                except:
                    msg = "Invalid thickness: '%s'" % value
                    raise ValueError(msg)
                    # self.error("Invalid thickness: '%s'" % value)

        if parts[2] == 'C':
            valid = True

        if value == existing and value_in == existing:
            print "No change.... no need to update"
            return

        if valid:
            # print "filter manager: old value", data.get(name)
            # print "filter manager: new value", value
            data[name] = value
        else:
            data[name] = existing

        # Update the variable with new value, OR with old value if new
        # value not valid
        self.monitor.update(VAR.OTHER_FILTERS, data)

    def get_beamline_filters(self, beamline):

        data = self.monitor.get_value(VAR.OTHER_FILTERS)
        wbt_status = self.monitor.get_value(VAR.WBT_STATUS)
        id_mono_status = self.monitor.get_value(VAR.ID_MONO_USE)

        filters = []

        # First, get list of filters
        for key, value in data.iteritems():

            parts = key.split('-')
            if parts[0] == beamline and parts[2] == 'M':

                material = value
                thickness_key = '%s-%s-T' % (beamline, parts[1])
                checkbox_key  = '%s-%s-C' % (beamline, parts[1])

                checked = data.get(checkbox_key)
                thickness = data.get(thickness_key)

                if thickness:
                    thickness = float(thickness)

                if not material:
                    continue

                if not thickness:
                    continue

                if checked != QtCore.Qt.Checked:
                    # print "skipping unchecked '%s' (%d)" % (material, thickness)
                    continue

                # print "OTHER FILTERS: CONSIDERING KEY---->>>>>", key
                if WBT_MAP.has_key(key) and WBT_MAP.get(key) != wbt_status:
                    # print "skipping wrong WBT status '%s' (%d)" % (material, thickness)
                    continue

                if ID_MONO_MAP.has_key(key):
                    status_list = ID_MONO_MAP.get(key)
                    if not id_mono_status in status_list:
                        # print "Skipping mono", key, status_list, id_mono_status
                        continue

                items = self.mat_mgr.get_filter_layers(key, material, thickness)
                filters.extend(items)

        return filters

    def terminate(self):

        self.monitor.disconnect(self)
