"""
Does not know about GUI
"""

# System imports
import math
import copy

# Library imports
import scipy.special as sp
from PyQt4 import QtCore

# App imports
from utils import clean_float


BMIT_ID_WIGGLER_FULL_POLES = 25
BMIT_ID_WIGGLER_HALF_POLES = 2

class Spectrum(QtCore.QObject):

    def __init__(self, material_manager):

        self.material_manager = material_manager
        self.error_callback = None

        super(Spectrum, self).__init__()

    def error(self, msg):
        print msg
        if self.error_callback:
            self.error_callback(msg)

    def set_error_callback(self, error_callback):
        self.error_callback = error_callback

    def apply_filters(self, spectrum, filters, kevs=None, msg=None):
        """
        This method applies the filter (attenuation) to the
        passed in spectrum.  The result is a list of cumulative
        spectrums, i.e.,

        result 0 -> attenuation due to F0
        result 1 -> attenuation due to F0, F1
        result 2 -> attenuation due to F0, F1, F2
        etc
        """

        # print "apply_filters() called --------- "

        cumulative = [copy.copy(spectrum)]

        if not kevs:
            kevs = [item[0] for item in spectrum]

        for filter in filters:
            material = filter[1]

            if msg is not None:
                thk = clean_float("%0.4f" % filter[2])
                msg.append("%s (%s mm)" % (filter[1], thk))

            if self.material_manager.is_opaque(material):
                # print "Found opaque material '%s'" % material
                flat = [(item[0], 0.0) for item in spectrum]
                cumulative.append(flat)
                return cumulative

            # Need thickness in cm.... PVs are in mm
            thickness = float(filter[2]) / 10.0

            # print "Apply filter '%s, '%s' thickness (cm) '%s'" % \
            #       (filter[0], material, thickness)

            data = self.material_manager.get_mass_attenuation(material, kevs)
            density = self.material_manager.get_density(material)
            atten = self.compute_attenuation(data, density, thickness)
            spectrum = self.apply_attenuation(spectrum, atten)

            cumulative.append(copy.copy(spectrum))

        return cumulative

    def apply_attenuation(self, attenuated, atten):
        if len(atten) != len(attenuated):
            raise ValueError("Len spectrum %d != len filter %d" %
                                     (len(attenuated), len(atten)))

        for i in xrange(len(atten)):
            point = attenuated[i]
            factor = atten[i]
            new_point = (point[0], point[1] * factor[1])
            attenuated[i] = new_point

        return attenuated

    def compute_attenuation(self, mass_atten, density, thickness):

        result = []
        for item in mass_atten:

            x = item[0]
            u = item[1]
            p = u * density * thickness
            y = math.exp(-1.0 * p)
            result.append((x, y))

        return result

    def make_log_sequence(self, min, max, points):
        """
        Generates a log10 sequence.
        """

        # Uniform distribution
    #    span = max - min
    #    step_size = span / float(points - 1)
    #    kevs = [min + i * step_size for i in range(points)]

        # Log distribution
        min_exp = math.log(min, 10.0)
        max_exp = math.log(max, 10.0)
        step_size = (max_exp - min_exp) / (float(points) - 1.0)
        kevs = [math.pow(10.0 , min_exp + i * step_size) for i in range(points)]

        return kevs

    def hxy(self, range, x):

        result = []

        x2 = x * x

        order_23 = 2.0 / 3.0
        order_13 = 1.0 / 3.0

        for y in range:
            ksi = 0.5 * y * math.pow(1 + x2, 1.5)
            k = sp.kv(order_23, ksi)
            term1 = k * k
            k = sp.kv(order_13, ksi)
            term2 = k * k * x2 / (1.0 + x2)
            ans = y * y * (1.0 + x2) * (1.0 + x2) * (term1 + term2)
            result.append(ans)

        return result

    def spectrum_id(self, ring_energy, ring_current, wiggler_field, kevs):

        # gamma = 1957.0 * ring_energy
        ec = 0.665 * ring_energy * ring_energy * wiggler_field
        poles = BMIT_ID_WIGGLER_FULL_POLES

        factor = 1.327e13

        if ec == 0.0:
            return [(k, 0.0) for k in kevs]

        y_range = [float(k)/ec for k in kevs]
        # print "Y_RANGE", y_range

        h = self.h2(y_range)
        # print "H2", h

        m = factor * ring_energy * ring_energy * ring_current * poles
        result = [m * x for x in h]

        return zip(kevs, result)

    def h2(self, range):

        result = []
        order = 2.0/3.0
        for x in range:
            # b = sp.yv(order, 0.5 * x)
            b = sp.kv(order, 0.5 * x)
            h = x * x * b * b
            result.append(h)

        return result

    def spectrum(self, ring_energy, ring_current, bm_field, kevs):

        # gamma = 1957.0 * ring_energy
        ec = 0.665 * ring_energy * ring_energy * bm_field

        factor = 1.327e13

        y_range = [float(k)/ec for k in kevs]

        # print "Y_RANGE", y_range

        h = self.h2(y_range)

        # print "H2", h

        m = factor * ring_energy * ring_energy * ring_current
        result = [m * x for x in h]

        return zip(kevs, result)
