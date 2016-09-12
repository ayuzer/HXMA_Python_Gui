class LineGeneric(object):

    def __init__(self, x_start, z_start, x_stop, z_stop):

        self.x_start = x_start
        self.z_start = z_start
        self.x_stop = x_stop
        self.z_stop = z_stop

        rise = self.z_stop - self.z_start
        run = self.x_stop - self.x_start

        self.slope = float(rise)/float(run)
        self.intercept = float(self.z_start) - self.slope * float(self.x_start)

        # print "slope", self.slope
        # print "intercept", self.intercept

    def get_height(self, x):

        # print "Want to get height at x", x
        return self.slope * x + self.intercept


class LineClip(object):
    """
    This class is used to clip lines according to the scene dimensions.
    It just uses a "brute force" algorithm.

    I can't figure out how to get the QGraphicsScene to clip the lines.
    What happens is that lines that extend outside the view frame cause
    the whole thing to become scrollable
    """
    def __init__(self, x_start, z_start, x_stop, z_stop, mapper):

        self.x_start = x_start
        self.z_start = z_start
        self.x_stop = x_stop
        self.z_stop = z_stop

        self.x_start_orig = x_start
        self.z_start_orig = z_start
        self.x_stop_orig = x_stop
        self.z_stop_orig = z_stop

        self.mapper = mapper
        self.swapped = False

        self.z_pixel_max = self.mapper.get_z_pixel_max()
        self.z_pixel_min = self.mapper.get_z_pixel_min()
        self.x_pixel_max = self.mapper.get_x_pixel_max()
        self.x_pixel_min = self.mapper.get_x_pixel_min()

        self.clipped = False
        if z_start > self.z_pixel_max or z_start < self.z_pixel_min:
            self.clipped = True
        elif z_stop > self.z_pixel_max or z_stop < self.z_pixel_min:
            self.clipped = True
        elif x_start > self.x_pixel_max or x_start < self.x_pixel_min:
            self.clipped = True
        elif x_stop > self.x_pixel_max or x_stop < self.x_pixel_min:
            self.clipped = True

    def clip(self):

        if not self.clipped:
            return self.x_start, self.z_start, self.x_stop, self.z_stop

        # The thing is clipped
        rise = self.z_stop - self.z_start
        run = self.x_stop - self.x_start

        if abs(rise) > abs(run):
            self.swapped = True

        if self.swapped:
            # Swap the axis
            self.swapped = True

            self.x_start = self.z_start_orig
            self.z_start = self.x_start_orig
            self.x_stop = self.z_stop_orig
            self.z_stop = self.x_stop_orig

            self.z_pixel_max = self.mapper.get_x_pixel_max()
            self.z_pixel_min = self.mapper.get_x_pixel_min()
            self.x_pixel_max = self.mapper.get_z_pixel_max()
            self.x_pixel_min = self.mapper.get_z_pixel_min()

            rise = self.z_stop - self.z_start
            run = self.x_stop - self.x_start

        try:
            slope = float(rise)/float(run)
        except Exception, e:
            print "Error computing line slope: %s rise: %s run:%s" % \
                  (str(e), repr(rise), repr(run))
            return None, None, None, None

        intercept = float(self.z_start) - slope * float(self.x_start)

        step = 1
        if self.x_stop < self.x_start:
            step = -1

        result = []

        loops = abs(self.x_start - self.x_stop)

        x = self.x_start - step

        # print "clipped line"
        # print "x start %d stop %d" % (self.x_start, self.x_stop)

        while loops:
            x += step
            if x > self.x_pixel_min and x < self.x_pixel_max:
                z = int(slope * float(x) + intercept)
                if z > self.z_pixel_min and z < self.z_pixel_max:
                    result.append((x, z))

            loops -= 1

        # print "this is the result"
        # print result

        if len(result) == 0:
            return None, None, None, None

        start = result[0]
        start_x = start[0]
        start_z = start[1]

        stop = result[-1]
        stop_x = stop[0]
        stop_z = stop[1]

        if self.swapped:
            return start_z, start_x, stop_z, stop_x

        return start_x, start_z, stop_x, stop_z


