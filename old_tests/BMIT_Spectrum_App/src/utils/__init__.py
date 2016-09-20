import math

MIN_ATAN_VAL = 1e-4

def to_rad(degrees):
    return degrees * math.pi / 180.0

def to_deg(radians):
    result = radians * 180.0 / math.pi
    if result > 359.999:
        result = 0
    return result

def atan2(y, x):
    # print "ATAN2", y, x
    if abs(y) < MIN_ATAN_VAL and abs(x) < MIN_ATAN_VAL:
        return 0.0
    return math.atan2(y, x)

class Constant(object):

    @classmethod
    def validate(cls, value):

        for k, v in cls.__dict__.iteritems():
            if value == v:
                if not k.startswith('_'):
                    return True

    @classmethod
    def name(cls, value):

        for k, v in cls.__dict__.iteritems():
            if value == v:
                if not k.startswith('_'):
                    return '%s.%s' % (cls.__name__, k)

        return '%s.UNKNOWN' % cls.__name__

    @classmethod
    def items(cls):
        result = {}
        for k, v in cls.__dict__.iteritems():
            # print k, v
            if not k.startswith('_'):
                result[k] = v
        return result

def clean_float(value):

    p = value.find('.')

    value = value.strip().lstrip('0')

    if p >= 0:
        # Strip trailing 0s if there is a decimal point
        value = value.strip().rstrip('0')

    if value.endswith('.'):
        value += '0'

    p = value.find('.')
    if p < 0:
        value = value + '.0'

    if value.startswith('.'):
        value = '0' + value

    p = value.find('e')
    if p >= 0:
        if value.endswith('.0'):
            value = value[:-2]

    if value == '-0.0':
        value = '0.0'
    # print "clean_float returning '%s'" % value
    return value
