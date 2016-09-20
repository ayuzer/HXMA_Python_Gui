# System imports
import os
import math

# App imports
from elements import ELEMENTS
import settings
from utils import Constant

class INDEX(Constant):
    MEV             = 0
    KEV             = 1
    KEV_LOG         = 2
    MASS_ATTEN      = 3
    MASS_ATTEN_LOG  = 4
    MASS_EN_ABS     = 5

class KEY(Constant):
    DENSITY         = 'density'
    ELEMENTS        = 'elements'
    ATOMIC_NUMBER   = 'number'
    ATOMIC_WEIGHT   = 'weight'
    ATOMIC_SYMBOL   = 'symbol'
    DATA            = 'data'
    SEARCH_STRING   = 'search'
    MASS_ATTEN      = 'atten'
    LAYERS          = 'layers'
    OPAQUE          = 'opaque'
    MATERIAL        = 'material'
    PROPORTION      = 'proportion'

class MaterialsManager(object):
    """
    This manager looks after all the materials data, which comes from:

    1 - The list of elements in elements.py
    2 - The files containing mass attenuation coefficients
    3 - Compound definitions (compounds.txt)
        - "True" compounds
        - "Layered" (e.g., AL + Sn)
        - "Equivalents (e.g., Glasseous)

    """
    def __init__(self, error_callback=None):

        self.data = {}
        self.error_callback = error_callback
        self.mass_attenuation_cache = {}

        # First, read the element data into the data dict
        for item in ELEMENTS:
            name = item[2].strip()
            data = {
                KEY.ATOMIC_NUMBER   : item[0],
                KEY.DENSITY         : item[5],
                KEY.ATOMIC_WEIGHT   : item[6],
                KEY.ATOMIC_SYMBOL   : item[1].strip(),
                KEY.SEARCH_STRING   : name.lower(),
            }
            self.data[name] = data

        # Add special case
        self.data['Not in Position'] = {
            KEY.OPAQUE : True,
            KEY.SEARCH_STRING : 'not in position'
        }

        # Next, find a list of data files.  This will find the compounds file
        files, compound_file = self.find_data_files()

        # Parse compounds file.  Do this before reading mass atten data files
        compounds = self.parse_compound_file(compound_file)

        for key, value in compounds.iteritems():
            name = key.strip()

            data = {
                KEY.DENSITY         : value.get(KEY.DENSITY),
                KEY.SEARCH_STRING   : name.lower(),
                KEY.ELEMENTS        : value.get(KEY.ELEMENTS),
                KEY.LAYERS          : value.get(KEY.LAYERS),
            }
            if self.data.has_key(name):
                raise ValueError("'%s' already defined" % name)

            self.data[name] = data

        # for key, value in self.data.iteritems():
        #     print "KEY ==================>>>", key
        #    print "VALUE", value

        for file in files:
            self.read_data_file(file)

        # Enumerate elements that are missing mass atten data
        for key, value in self.data.iteritems():
            if value.has_key(KEY.ATOMIC_NUMBER):
                if not value.has_key(KEY.MASS_ATTEN):
                    print "Element %s (%d) missing mass attenuation data" % \
                        (key, value.get(KEY.ATOMIC_NUMBER))

    def parse_clean_line(self, line):

        parts = line.split('#')
        line = parts[0]
        line = line.strip()
        return line

    def parse_find_compound(self, line):
        if not line.startswith('['):
            return

        if not line.endswith(']'):
            return

        compound = line[1:-1].strip()
        return compound

    def parse_find_density(self, line):
        parts =  line.split(':')
        parts = [part.strip().lower() for part in parts]

        if len(parts) != 2:
            return

        if parts[0] != KEY.DENSITY:
            return

        density = float(parts[1])
        return density

    def parse_find_element(self, line):
        parts = line.split(':')
        parts = [part.strip().lower() for part in parts]

        if len(parts) != 2:
            return None, None

        element = self.resolve_material(parts[0])

        if not element:
            return None, None

        item = self.data.get(element)
        atomic_symbol = item.get(KEY.ATOMIC_SYMBOL)
        if not atomic_symbol:
            msg = "The resolved material '%s' is not an element" % element
            raise ValueError(msg)

        percentage = float(parts[1])

        if percentage > 0.0 and percentage < 1.0:
            return None, None

        try:
            count = int(parts[1])
        except:
            raise ValueError("int() failed for %s" % line)

        if count < 1 or count > 500:
            raise ValueError("Invalid count in line '%s'" % line)

        return element, count

    def parse_find_layer(self, line):
        parts =  line.split(':')
        parts = [part.strip().lower() for part in parts]

        if len(parts) != 2:
            return None, None

        material = self.resolve_material(parts[0])

        if not material:
            return None, None

        proportion = float(parts[1])

        if proportion > 0.0 and proportion < 1.0:
            return material, proportion

        return None, None

    def parse_compound_file(self, file):

        result = {}

        try:
            f = open(file, 'r')

            current_compound = None
            for line in f:
                line = self.parse_clean_line(line)
                if not line:
                    continue

                compound = self.parse_find_compound(line)

                if compound:
                    current_compound = compound
                    result[compound] = {}
                    continue

                density = self.parse_find_density(line)

                if density:
                    data = result.get(current_compound)
                    data[KEY.DENSITY] = density
                    result[current_compound] = data
                    continue

                element, count = self.parse_find_element(line)
                if element:
                    data = result.get(current_compound)
                    elements = data.get(KEY.ELEMENTS, {})
                    elements[element] = count
                    data[KEY.ELEMENTS] = elements
                    continue

                material, proportion = self.parse_find_layer(line)
                if material:
                    data = result.get(current_compound)
                    layers = data.get(KEY.LAYERS, [])
                    layers.append({
                        KEY.MATERIAL   : material,
                        KEY.PROPORTION : proportion
                    })
                    data[KEY.LAYERS] = layers
                    continue

                msg = "Unable to parse line '%s' in %s" % (line, file)
                self.error(msg)

        finally:
            f.close()

        for key, value in result.iteritems():
            print "Compound: '%s' " % key
            print "Data", value

        return result

    def error(self, msg):
        print msg
        if self.error_callback:
            self.error_callback(msg)

    def set_error_callback(self, error_callback):
        self.error_callback = error_callback

    def has_nist_data(self, material):
        material = self.resolve_material(material)
        if material is None:
            return False

        if material == 'none' or material == 'None':
            return False

        data = self.data.get(material)

        if not data:
            self.error("No material data for '%s'" % material)
            return False

        if data.has_key(KEY.MASS_ATTEN):
            return True

        return False

    def is_opaque(self, material):

        material = self.resolve_material(material)
        if material is None:
            return False

        if material == 'none' or material == 'None':
            return False

        data = self.data.get(material)

        if not data:
            self.error("No material data for '%s'" % material)
            return False

        return data.get(KEY.OPAQUE, False)

    def get_filter_layers(self, name, material, thickness):
        """
        NOTE: materials like: "AL 3mm + SN 0.5" that must be handled
        Returns a list of (material, thickness) tuples
        """
        # print "get_keys_from_pvs called for '%s'" % material

        material = self.resolve_material(material)

        if material is None or thickness is None:
            return []

        if material == 'none' or material == 'None' or thickness == '0.0':
            return []

        data = self.data.get(material)

        if not data:
            self.error("No material data for '%s'" % material)
            return []

        layers = data.get(KEY.LAYERS)

        if not layers:
            return [(name, material, thickness)]

        result = []
        for layer in layers:
            material = layer.get(KEY.MATERIAL)
            proportion = layer.get(KEY.PROPORTION)
            result.append((name, material, proportion * thickness))

        return result

    def read_data_file(self, file):

        # print "Reading data file '%s'" % file
        name = os.path.basename(file)

        # Get rid of the .txt which at this point should be there
        name = name[:-4]

        material = self.resolve_material(name)
        if not material:
            raise ValueError("Cannot find material '%s'" % name)

        data_points = []

        try:
            f = open(file, 'r')

            for line in f:

                line = line.strip()

                if not line:
                    continue

                parts = line.split()
                part_count = len(parts)

                if part_count == 3:
                    d = (float(parts[0]), float(parts[1]), float(parts[2]))

                elif part_count == 4:
                    d = (float(parts[1]), float(parts[2]), float(parts[3]))

                elif part_count == 5:
                    d = (float(parts[2]), float(parts[3]), float(parts[4]))

                else:
                    m = "Unexpected number of elements in line '%s' file '%s'" % \
                        (line, file)
                    self.error(m)
                    continue

                point = (
                    d[0],                           # 0: MEV
                    d[0] * 1000.0,                  # 1: KEV
                    math.log(d[0] * 1000.0, 10),    # 2: KEV_LOG
                    d[1],                           # 3: MASS_ATTEN
                    math.log(d[1], 10),             # 4: MASS_ATTEN_LOG
                    d[2],                           # 5: MASS_E_ABS
                )

                data_points.append(point)

        finally:
            f.close()

        item = self.data.get(material)
        item[KEY.MASS_ATTEN] = data_points

    def find_data_files(self):
        """
        Finds the mass attenuation coefficient files
        """
        files = []
        compound_file = None

        result = os.walk(os.getcwd())

        for item in result:

            if not item[0].endswith(settings.DATA_DIRECTORY):
                # print "skip directory '%s'" % item[0]
                continue

            # print "consider directory: '%s'" % item[0]
            for file in item[2]:

                if file == 'compounds.txt':
                    compound_file = os.path.join(item[0], file)
                    continue

                if not file.endswith('.txt'):
                    # print "skip file '%s': does not end with '.txt'" % file
                    continue

                files.append(os.path.join(item[0], file))

        return files, compound_file

    def get_list(self, formatted=False, atomic_number=True):

        # Put the element number in pos 0 of the tuple for sorting purposes
        result = [(v.get(KEY.ATOMIC_NUMBER, 0), k) for k, v in self.data.iteritems()]

        if not formatted:
            return result

        result2 = []
        for item in result:
            if atomic_number and item[0] > 0:
                desc = "%s (%d)" % (item[1], item[0])
            else:
                desc = item[1]
            result2.append(desc)

        result2.sort()
        return result2

    def get_density(self, material):

        material_key = self.resolve_material(material)
        item = self.data.get(material_key)
        return item.get(KEY.DENSITY)

    def resolve_material(self, name, return_possible=False):

        name = name.lower().strip()

        # print "CHECKING MATERIAL '%s' (%s)" % (name, type(name))

        # None is a 'special case'
        if not name or name == 'none' or name == 'None':
            return 'None'

        # First, look at atomic symbols
        for key, value in self.data.iteritems():
            atomic_symbol = value.get(KEY.ATOMIC_SYMBOL)
            if atomic_symbol and name == atomic_symbol.lower():
                return key

        # Next look at elements and compounds
        possible = []

        for key, value in self.data.iteritems():
            search_string = value.get(KEY.SEARCH_STRING)

            if name == search_string:
                # This is an exact match, return it
                return key

            pos = search_string.find(name)
            if pos >= 0:
                possible.append(key)

        # If there is only one possible match, return it
        if len(possible) == 1:
            return possible[0]

        if return_possible and len(possible) > 1:
            return possible

        # Finally look at atomic numbers
        try:
            have = int(name)
        except:
            return

        for key, value in self.data.iteritems():
            atomic_number = value.get(KEY.ATOMIC_NUMBER)
            if atomic_number and have == atomic_number:
                return key

        return

    def get_mass_attenuation_compound(self, material, kevs):

        material_key = self.resolve_material(material)
        # print "get_mass_attenuation_compound", material, material_key

        item = self.data.get(material_key)

        if not item or not kevs:
            # print "retrning none", kevs
            # print "item", item
            return None

        elements = item.get(KEY.ELEMENTS)

        temp = []
        for element, value in elements.iteritems():

            print "Material '%s' --> element: '%s'" % (material, element)

            element_data = self.data.get(element)
            atomic_weight = element_data.get(KEY.ATOMIC_WEIGHT)

            data = {
                'element' : element,
                'weight'  : atomic_weight * value,
                'atten'   : self.get_mass_attenuation(element, kevs),
            }
            temp.append(data)

        total_weight = 0.0
        for item in temp:
            total_weight += item.get('weight')

        for item in temp:
            item['factor'] = item.get('weight') / total_weight

        result = []
        for i in xrange(len(kevs)):
            v = 0
            for item in temp:
                atten = item.get('atten')
                factor = item.get('factor')

                v += atten[i][1] * factor

            result.append(v)

        result = zip(kevs, result)

        return result

    def get_mass_attenuation(self, material, kevs=None):

        material_key = self.resolve_material(material)
        item = self.data.get(material_key)

        #print "==============="
        #print "material: '%s'" % material
        #print "material key: '%s'" % material_key
        #print "==============="

        if not item:
            self.error("Unknown/unsupported material '%s'" % material)
            return

        key = "%s-%s" % (material_key, id(kevs))
        result = self.mass_attenuation_cache.get(key)

        if result:
            # print "get_mass_attenuation(%s) -> cache hit" % material_key
            return result

        print "Cache miss: mass attenuation data for '%s'" % material_key
        data = item.get(KEY.MASS_ATTEN)

        if data:
            if kevs:
                result = self.interpolate(data, kevs)

            else:
                result = [(x[INDEX.KEV], x[INDEX.MASS_ATTEN]) for x in data]

        else:
            elements = item.get(KEY.ELEMENTS)

            if elements:
                # This appears to be a compound with no mass attenuation
                # data file.  Attempt to compute.
                result = self.get_mass_attenuation_compound(material, kevs)

        if result:
            self.mass_attenuation_cache[key] = result
        else:
            msg = "Unable to generate mass attenuation data for '%s'" % material
            self.error(msg)

        return result

    def get_mass_energy_absorption(self, material):

        return None
        #material_key = self.resolve_material(material)
        #item = self.data.get(material_key)
        #
        #data = self.data.get()
        #if not data:
        #    return None
        #
        #data = element_data.get(KEY.DATA)
        #result = [(x[INDEX.KEV], x[INDEX.MASS_EN_ABS]) for x in data]
        #return result

    def interpolate(self, atten, kevs, debug=False):
        """
        """
        result = []

        for k in kevs:

            low = None
            high = None
            for item in atten:
                if item[INDEX.KEV] <= k:
                    low = item

                if not high and item[INDEX.KEV] > k:
                    high = item

            # Interpolate in the log10 domain where plots appear linear
            rise = high[INDEX.MASS_ATTEN_LOG] - low[INDEX.MASS_ATTEN_LOG]
            run  = high[INDEX.KEV_LOG] - low[INDEX.KEV_LOG]

            slope = rise / run

            val = low[INDEX.MASS_ATTEN_LOG] + \
                  (math.log(k, 10) - low[INDEX.KEV_LOG]) * slope

            result.append(math.pow(10, val))

        result = zip(kevs, result)
        return result
