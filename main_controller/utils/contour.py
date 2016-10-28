#!/usr/bin/env python

# Based off of The Python version of Qwt-5.0.0/examples/spectrogram
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import Qwt5 as Qwt
import math

import numpy as np

class Contour(Qwt.QwtPlot):
    def __init__(self, *args, **kwargs):

        self.monitor = kwargs['monitor']
        del kwargs['monitor']

        self.VAR = kwargs['VAR']
        del kwargs['VAR']

        Qwt.QwtPlot.__init__(self, *args)
        self.contour=True
        self.__spectrogram = Qwt.QwtPlotSpectrogram()
        # LeftButton for the zooming
        # MidButton for the panning
        # RightButton: zoom out by 1
        # Ctrl+RighButton: zoom out to full size
        self.zoomer = Qwt.QwtPlotZoomer(Qwt.QwtPlot.xBottom,
                                        Qwt.QwtPlot.yLeft,
                                        Qwt.QwtPicker.DragSelection,
                                        Qwt.QwtPicker.AlwaysOn,
                                        self.canvas())
        self.zoomer.setMousePattern(Qwt.QwtEventPattern.MouseSelect2,
                                    Qt.Qt.RightButton, Qt.Qt.ControlModifier)
        self.zoomer.setMousePattern(Qwt.QwtEventPattern.MouseSelect3,
                                    Qt.Qt.RightButton)
        self.zoomer.setRubberBandPen(Qt.Qt.darkBlue)
        self.zoomer.setTrackerPen(Qt.Qt.darkBlue)

        if not hasattr(self, 'log'):
            self.log = False

        xmin = -10
        ymin = -10
        xmax = 10
        ymax = 10
        x_a = []
        y_a = []
        intes = []
        for x in np.linspace(xmin, xmax, 50):
            for y in np.linspace(ymin, ymax, 50):
                x_a.append(x)
                y_a.append(y)  # I just used a random function from https://www.physicsforums.com/threads/cool-3-d-functions-for-graphing.140087/ to display
                # intes.append(x+y) # This is the actual function I used for testing. It is much simplier and you can tell where every point should be
                intes.append(max([-2*(round(math.e**(-(x*2)**2)) + round(math.e**(-(y*2)**2)))+ 2+2*math.cos((x**2+y**2)/4), 25*math.e**(-1*(x**2+y**2)*3)]))

        self.plot(x_a, y_a, intes)

        panner = Qwt.QwtPlotPanner(self.canvas())
        panner.setAxisEnabled(Qwt.QwtPlot.yRight, False)
        panner.setMouseButton(Qt.Qt.MidButton)

        # Avoid jumping when labels with more/less digits
        # appear/disappear when scrolling vertically
        #
        fm = Qt.QFontMetrics(self.axisWidget(Qwt.QwtPlot.yLeft).font())
        self.axisScaleDraw(
            Qwt.QwtPlot.yLeft).setMinimumExtent(fm.width("100.00"))

    def mousePressEvent(self, event):
        # print "Mouse PRESS", event.pos()

        canvasPos = self.canvas().mapFrom(self, event.pos())
        xFloat = self.invTransform(Qwt.QwtPlot.xBottom, canvasPos.x())
        yFloat = self.invTransform(Qwt.QwtPlot.yLeft, canvasPos.y())

        try:
            self.monitor.update(self.VAR.MESH_CLICK_X, xFloat)
            self.monitor.update(self.VAR.MESH_CLICK_Y, yFloat)
        except (TypeError, AttributeError):
            print "Canvas not set, clicking is ineffective"

    def plot(self, x=None, y=None, z=None):
        if (x == None or x == True or x == False) and y == None and z == None:
            x, y, z = self.old_x, self.old_y, self.old_z
        else:
            self.old_x, self.old_y, self.old_z = x, y, z

        if all(p == x[0] for p in x) or all(p == y[0] for p in y):# is data 1D?
            xy = [x, y]
            for i, k in enumerate(xy):
                try: # if the data is 1D we will make it slightly bigger so we can graph a contour of it
                    if k[0] == k[1]:
                        xy[i].extend([q+0.1 for q in xy[i]])
                    else:
                        xy[i].extend(xy[i])
                except IndexError:
                    continue
            z.extend(z)
        self.data = SpectrogramData(x, y, z)
        self.__spectrogram.setData(self.data)

        self.log_check(self.log, replot = False)
        if self.zoomer.zoomRectIndex() == 0:
            self.autoscale()
        else:
            self.__spectrogram.invalidateCache()
            self.replot()

    def set_axis_label_x(self, label):

        titleFont = QtGui.QFont('Monospace', 10)
        titleFont.setWeight(QtGui.QFont.Light)

        xAxisLabel = Qwt.QwtText(label)
        xAxisLabel.setFont(titleFont)
        self.setAxisTitle(Qwt.QwtPlot.xBottom, xAxisLabel)

    def set_axis_label_y(self, label):

        titleFont = QtGui.QFont('Monospace', 10)
        titleFont.setWeight(QtGui.QFont.Light)

        yAxisLabel = Qwt.QwtText(label)
        yAxisLabel.setFont(titleFont)

        self.setAxisTitle(Qwt.QwtPlot.yLeft, yAxisLabel)

    def autoscale(self):
        """Auto scale and clear the zoom stack
        """
        self.setAxisAutoScale(Qwt.QwtPlot.xBottom)
        self.setAxisAutoScale(Qwt.QwtPlot.yLeft)
        self.__spectrogram.invalidateCache()
        self.zoomer.setZoomBase()

    def log_check(self, log, replot=True):
        self.log = log
        min_intes = self.data.intes_array.min()
        max_intes = math.ceil(self.data.intes_array.max()) + 1.0
        if log: # most of this is changing color scaling for logarithimc
            colorMap = Qwt.QwtLinearColorMap(Qt.Qt.darkCyan, Qt.Qt.red)
            if min_intes <=0:
                logmin = 0.01
            else:
                logmin = min_intes

            self.setAxisScale(Qwt.QwtPlot.yRight,
                              logmin,
                              max_intes)
            oom = int(math.log10(max_intes)) # for log scale we will add in colours depnding on order of magnatiude (oom)
            map = [[1.0/(10**oom), Qt.Qt.cyan], [0.1, Qt.Qt.yellow], [0.01, Qt.Qt.darkGreen],
                   [1.0 / (10 ** (oom-1)), Qt.Qt.blue], [1.0 / (10 ** (oom - 2)), Qt.Qt.darkBlue], [1.0 / (10 ** (oom - 3 )), Qt.Qt.green]]
            for i in range(oom):
                colorMap.addColorStop(map[i][0], map[i][1])
            self.__spectrogram.setColorMap(colorMap)
            self.setAxisScaleEngine(Qwt.QwtPlot.yRight, Qwt.QwtLog10ScaleEngine())
        else:
            colorMap = Qwt.QwtLinearColorMap(Qt.Qt.darkCyan, Qt.Qt.red)
            self.setAxisScale(Qwt.QwtPlot.yRight,
                             math.floor(min_intes),
                             math.ceil(max_intes))

            colorMap.addColorStop(0.25, Qt.Qt.cyan)
            colorMap.addColorStop(0.5, Qt.Qt.darkGreen)
            colorMap.addColorStop(0.75, Qt.Qt.yellow)
            self.setAxisScaleEngine(Qwt.QwtPlot.yRight, Qwt.QwtLinearScaleEngine())

            self.__spectrogram.setColorMap(colorMap)
        self.__spectrogram.attach(self)
        rightAxis = self.axisWidget(Qwt.QwtPlot.yRight)
        rightAxis.setTitle("Intensity")
        rightAxis.setColorBarEnabled(True)
        rightAxis.setColorMap(self.__spectrogram.data().range(),
                              self.__spectrogram.colorMap())
        self.enableAxis(Qwt.QwtPlot.yRight)
        if replot:
            self.replot()

class SpectrogramData(Qwt.QwtRasterData):
    def __init__(self, _x, _y, _z):
        self.intes = _z
        self.new_x = []
        self.new_y = []
        points = [[_x, float(1e-300)],
                  [_y, float(1e-300)]]
        for point in points:
            for each in point[0]:
                if point[1] < point[0].count(each):
                    point[1] = point[0].count(each)
        self.intes_array = np.zeros((points[0][1], points[1][1])) # creating an array based off of number of repeated entries
        for index, (x, y) in enumerate(zip(_x, _y)):
            if y not in self.new_y:
                self.new_y.append(y)
            j = self.new_y.index(y)
            if x not in self.new_x:
                self.new_x.append(x)
            i = self.new_x.index(x)
            try:
                self.intes_array[j, i] = _z[index] # build an array from flat
            except IndexError:  # The dimentionality of array can be incorrect due to an issue with SPEC data output
                adj = False   # This is a crude fix which just adjusts the size of the array up by one to accommodate
                _j, _i, = self.intes_array.shape
                if i == _i:
                    b = np.empty((_j, i+1))
                    b[:, :-1] = self.intes_array
                    self.intes_array = b
                    adj = True
                if j == _j:
                    b = np.empty((j+1, _i))
                    b[:-1, :] = self.intes_array
                    self.intes_array = b
                    adj = True
                if adj:
                    self.intes_array[j, i] = _z[index]
                else:
                    msg = "Array of Size: ", repr(self.intes_array.shape), " is indexed by : ", j, " ", i, " fed by: ", len(_z), " index: ", index
                    raise IndexError(msg)

        # print self.new_y
        # print self.new_x
        # print self.intes_array
        # print "\n----------------------------------------------------\n"
        if not min(self.new_x) == self.new_x[0]:  # Array is not sorted properly
            self.new_x = sorted(self.new_x)
            self.intes_array = np.fliplr(self.intes_array)  # we assume that it is exactly reversed so we flip the array too

        if not min(self.new_y) == self.new_y[0]:  # Array is not sorted properly
            self.new_y = sorted(self.new_y)
            self.intes_array = np.flipud(self.intes_array)  # we assume that it is exactly reversed so we flip the array too
        print self.intes_array

        Qwt.QwtRasterData.__init__(self, Qt.QRectF(min(self.new_x), min(self.new_y),
                                                   max(self.new_x)-min(self.new_x), max(self.new_y)-min(self.new_y)))
        # print "Initalized Data"

    def initRaster(self, QRect, size):
        # print "Begun Raster Initialization"
        ypix = (size.height())
        xpix = (size.width())
        x__ = sorted(np.linspace(QRect.left(), QRect.right(), xpix, endpoint=False).tolist())
        y__ = sorted(np.linspace(QRect.bottom(), QRect.top(), ypix, endpoint=False).tolist(),
                     reverse=True)  # this should be reverse but the axis are messsed up??
        pairs = []
        for y in y__:
            for x in x__:
                pairs.append((x, y))
        pairs = np.array(pairs)
        self.pairs = pairs
        # print "Initalized Raster"

        self.interp_matrix = self.interpolate_custom(self.new_x, self.new_y, self.intes_array, pairs) # interpolate full matrix so we can pull from it

    def value(self, x, y):
        (x1, y1) = self.pairs[0]  # reset count if we are starting
        if x1 == x and y1 == y:
            self.count = 0
            self.points = []
        # (xo, yo) = self.pairs[self.count - 1]  # we actually don't compare values due to floating point errors
        # if not xo == x or not yo == y:
        #     print self.count,": X: ", xo, "Xcurr: ",x, "Y: ", yo, "Ycurr: ", y
        try:
            self.count = self.count + 1
            return self.interp_matrix[self.count -1]
        except IndexError:  # This does a more intensive search if the count has been messed up, occurs during resizeing
            def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
                return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
            for pair in self.pairs:
                (xo, yo) = pair
                if isclose(xo, x) and isclose(yo, y):
                    self.count = np.nonzero(self.pairs == pair)[0][0] + 1
                    print "Fixed?"
                    return self.interp_matrix[self.count - 1]
            # print "FAILED TO FIND POINT!!", repr(pair)
            return 0
        except AttributeError:  # Just trying to reduce errors
            return 0
            pass

    # __init__()

    def copy(self):
        return self

    # copy()

    def range(self):
        # print "MIN CONTOUR = ", math.floor(self.intes_array.min())
        return Qwt.QwtDoubleInterval(int(self.intes_array.min()), math.ceil(self.intes_array.max()));

    # range()
    #
    def rasterHint(self, QwtRect):
        # print "RastHint Started"
        x_scale = int(25 * len(self.new_x)) # This is resolution, I am forcing it to be small for the most part
        y_scale = int(25 * len(self.new_y))
        if x_scale > 150:
            x_scale = 150
            if len(self.new_x) > 30:
                x_scale = 5 * len(self.new_x)
        elif x_scale < 50:
            x_scale = 50
        if y_scale > 150:
            y_scale = 150
            if len(self.new_x) > 30:
                x_scale = 5 * len(self.new_x)
        elif y_scale < 50:
            y_scale = 50
        return Qt.QSize(x_scale, y_scale)

    # This interpolation is not mine, http://www.floodhack.org/apidocs/safe.gis.interpolation2d.html or http://api.inasafe.org/_modules/safe/gis/interpolation2d.html
    # It has all been edited to fit my needs, but not extensively

    """Module for 2D interpolation over a rectangular mesh
    This module
    * provides piecewise constant (nearest neighbour) and bilinear interpolation
    * is fast (based on numpy vector operations)
    * depends only on numpy
    * guarantees that interpolated values never exceed the four nearest neighbours
    * handles missing values in domain sensibly using NaN
    * is unit tested with a range of common and corner cases
    See end of this file for documentation of the mathematical derivation used.
    """
    def interpolate2d(self, x, y, Z, points, mode='linear', bounds_error=False):
        """Fundamental 2D interpolation routine
        Input
            x: 1D array of x-coordinates of the mesh on which to interpolate
            y: 1D array of y-coordinates of the mesh on which to interpolate
            Z: 2D array of values for each x, y pair
            points: Nx2 array of coordinates where interpolated values are sought
            mode: Determines the interpolation order. Options are
                  'constant' - piecewise constant nearest neighbour interpolation
                  'linear' - bilinear interpolation using the four
                             nearest neighbours (default)
            bounds_error: Boolean flag. If True (default) an exception will
                          be raised when interpolated values are requested
                          outside the domain of the input data. If False, nan
                          is returned for those values
        Output
            1D array with same length as points with interpolated values
        Notes
            Input coordinates x and y are assumed to be monotonically increasing,
            but need not be equidistantly spaced.
            Z is assumed to have dimension M x N, where M = len(x) and N = len(y).
            In other words it is assumed that the x values follow the first
            (vertical) axis downwards and y values the second (horizontal) axis
            from left to right.
            If this routine is to be used for interpolation of raster grids where
            data is typically organised with longitudes (x) going from left to
            right and latitudes (y) from left to right then user
            self.interpolate_raster in this module
        """

        # Input checks
        x, y, Z, xi, eta = self.check_inputs(x, y, Z, points, mode, bounds_error)

        # # Identify elements that are outside interpolation domain or NaN
        # h_x = x[-1]
        # l_x = x[0]
        # a = xi < x[0]
        # b = eta < y[0]
        # c = xi > x[-1]
        # d = eta > y[-1]
        outside = (xi < x[0]) + (eta < y[0]) + (xi > x[-1]) + (eta > y[-1])
        outside += np.isnan(xi) + np.isnan(eta)

        inside = -outside
        xi = xi[inside]
        eta = eta[inside]

        # Find upper neighbours for each interpolation point
        idx = np.searchsorted(x, xi, side='left')
        idy = np.searchsorted(y, eta, side='left')

        # Internal check (index == 0 is OK)
        msg = ('Interpolation point outside domain. This should never happen. '
               'Please email Ole.Moller.Nielsen@gmail.com')
        if len(idx) > 0:
            if not max(idx) < len(x):
                raise RuntimeError(msg)
        if len(idy) > 0:
            if not max(idy) < len(y):
                raise RuntimeError(msg)

        # Get the four neighbours for each interpolation point
        x0 = x[idx - 1]
        x1 = x[idx]
        y0 = y[idy - 1]
        y1 = y[idy]

        z00 = Z[idx - 1, idy - 1]
        z01 = Z[idx - 1, idy]
        z10 = Z[idx, idy - 1]
        z11 = Z[idx, idy]

        # Coefficients for weighting between lower and upper bounds
        oldset = np.seterr(invalid='ignore')  # Suppress warnings
        alpha = (xi - x0) / (x1 - x0)
        beta = (eta - y0) / (y1 - y0)
        np.seterr(**oldset)  # Restore

        if mode == 'linear':
            # Bilinear interpolation formula
            dx = z10 - z00
            dy = z01 - z00
            z = z00 + alpha * dx + beta * dy + alpha * beta * (z11 - dx - dy - z00)
        else:
            # Piecewise constant (as verified in input_check)

            # Set up masks for the quadrants
            left = alpha < 0.5
            right = -left
            lower = beta < 0.5
            upper = -lower

            lower_left = lower * left
            lower_right = lower * right
            upper_left = upper * left

            # Initialise result array with all elements set to upper right
            z = z11

            # Then set the other quadrants
            z[lower_left] = z00[lower_left]
            z[lower_right] = z10[lower_right]
            z[upper_left] = z01[upper_left]

        # Self test
        if len(z) > 0:
            mz = np.nanmax(z)
            mZ = np.nanmax(Z)
            msg = ('Internal check failed. Max interpolated value %.15f '
                   'exceeds max grid value %.15f ' % (mz, mZ))
            if not (np.isnan(mz) or np.isnan(mZ)):
                if not mz-(1e-09) <= mZ:
                    raise RuntimeError(msg)

        # Populate result with interpolated values for points inside domain
        # and NaN for values outside
        r = np.zeros(len(points))
        r[inside] = z
        r[outside] = np.nan

        return r

    def interpolate_custom(self, x, y, Z, points, mode='linear', bounds_error=False):
        """2D interpolation of raster data
        It is assumed that data is organised in matrix Z as top down
        along the first dimension and longitudes from west to east
        along the second dimension.
        Further it is assumed that x is the vector of longitudes and y the
        vector of latitudes.
        See self.interpolate2d for details of the interpolation routine"""

        # Transpose Z to have y coordinates along the first axis and x coordinates
        # along the second axis
        Z = Z.transpose()

        # Call underlying interpolation routine and return
        res = self.interpolate2d(x, y, Z, points, mode=mode, bounds_error=bounds_error)
        return res

    def check_inputs(self, x, y, Z, points, mode, bounds_error):
        """Check inputs for self.interpolate2d function
        """

        msg = 'Only mode "linear" and "constant" are implemented. I got %s' % mode
        if mode not in ['linear', 'constant']:
            raise RuntimeError(msg)

        try:
            x = np.array(x)
        except Exception, e:
            msg = ('Input vector x could not be converted to np array: '
                   '%s' % str(e))
            raise Exception(msg)

        try:
            y = np.array(y)
        except Exception, e:
            msg = ('Input vector y could not be converted to np array: '
                   '%s' % str(e))
            raise Exception(msg)

        msg = ('Input vector x must be monotoneously increasing. I got '
               'min(x) == %.15f, but x[0] == %.15f' % (min(x), x[0]))
        if not min(x) == x[0]:
            raise RuntimeError(msg)

        msg = ('Input vector y must be monotoneously increasing. '
               'I got min(y) == %.15f, but y[0] == %.15f' % (min(y), y[0]))
        if not min(y) == y[0]:
            raise RuntimeError(msg)

        msg = ('Input vector x must be monotoneously increasing. I got '
               'max(x) == %.15f, but x[-1] == %.15f' % (max(x), x[-1]))
        if not max(x) == x[-1]:
            raise RuntimeError(msg)

        msg = ('Input vector y must be monotoneously increasing. I got '
               'max(y) == %.15f, but y[-1] == %.15f' % (max(y), y[-1]))
        if not max(y) == y[-1]:
            raise RuntimeError(msg)

        try:
            Z = np.array(Z)
            m, n = Z.shape
        except Exception, e:
            msg = 'Z must be a 2D np array: %s' % str(e)
            raise Exception(msg)

        Nx = len(x)
        Ny = len(y)
        msg = ('Input array Z must have dimensions %i x %i corresponding to the '
               'lengths of the input coordinates x and y. However, '
               'Z has dimensions %i x %i.' % (Nx, Ny, m, n))
        if not (Nx == m and Ny == n):
            raise RuntimeError(msg)

        # Get interpolation points
        points = np.array(points)
        xi = points[:, 0]
        eta = points[:, 1]  # y points

        if bounds_error:
            msg = ('Interpolation point %f was less than the smallest value in '
                   'domain %f and bounds_error was requested.' % (xi[0], x[0]))
            if xi[0] < x[0]:
                raise Exception(msg)

            msg = ('Interpolation point %f was greater than the largest value in '
                   'domain %f and bounds_error was requested.' % (xi[-1], x[-1]))
            if xi[-1] > x[-1]:
                raise Exception(msg)

            msg = ('Interpolation point %f was less than the smallest value in '
                   'domain %f and bounds_error was requested.' % (eta[0], y[0]))
            if eta[0] < y[0]:
                raise Exception(msg)

            msg = ('Interpolation point %f was greater than the largest value in '
                   'domain %f and bounds_error was requested.' % (eta[-1], y[-1]))
            if eta[-1] > y[-1]:
                raise Exception(msg)

        return x, y, Z, xi, eta

    """
    Bilinear interpolation is based on the standard 1D linear interpolation
    formula:
    Given points (x0, y0) and (x1, x0) and a value of x where x0 <= x <= x1,
    the linearly interpolated value y at x is given as
    alpha*(y1-y0) + y0
    or
    alpha*y1 + (1-alpha)*y0                (1)
    where alpha = (x-x0)/(x1-x0)           (1a)
    2D bilinear interpolation aims at obtaining an interpolated value z at a point
    (x,y) which lies inside a square formed by points (x0, y0), (x1, y0),
    (x0, y1) and (x1, y1) for which values z00, z10, z01 and z11 are known.
    This obtained be first applying equation (1) twice in in the x-direction
    to obtain interpolated points q0 and q1 for (x, y0) and (x, y1), respectively.
    q0 = alpha*z10 + (1-alpha)*z00         (2)
    and
    q1 = alpha*z11 + (1-alpha)*z01         (3)
    Then using equation (1) in the y-direction on the results from (2) and (3)
    z = beta*q1 + (1-beta)*q0              (4)
    where beta = (y-y0)/(y1-y0)            (4a)
    Substituting (2) and (3) into (4) yields
    z = alpha*beta*z11 + beta*z01 - alpha*beta*z01 +
        alpha*z10 + z00 - alpha*z00 - alpha*beta*z10 - beta*z00 +
        alpha*beta*z00
      = alpha*beta*(z11 - z01 - z10 + z00) +
        alpha*(z10 - z00) + beta*(z01 - z00) + z00
    which can be further simplified to
    z = alpha*beta*(z11 - dx - dy - z00) + alpha*dx + beta*dy + z00  (5)
    where
    dx = z10 - z00
    dy = z01 - z00
    Equation (5) is what is implemented in the function interpolate2d above.
    Piecewise constant interpolation can be implemented using the same coefficients
    (1a) and (4a) that are used for bilinear interpolation as they are a measure of
    the relative distance to the left and lower neigbours. A value of 0 will pick
    the left or lower bound whereas a value of 1 will pick the right or higher
    bound. Hence z can be assigned to its nearest neigbour as follows
        | z00   alpha < 0.5 and beta < 0.5    # lower left corner
        |
        | z10   alpha >= 0.5 and beta < 0.5   # lower right corner
    z = |
        | z01   alpha < 0.5 and beta >= 0.5   # upper left corner
        |
        | z11   alpha >= 0.5 and beta >= 0.5  # upper right corner
        """

class MouseTracker(Qt.QObject):

    SIGNAL_MOVE = QtCore.pyqtSignal(QtCore.QPoint)
    SIGNAL_PRESS = QtCore.pyqtSignal(QtCore.QPoint)
    SIGNAL_RELEASE = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, plotter):

        self.plotter = plotter
        self.parent = self.plotter.canvas()

        super(MouseTracker, self).__init__(self.parent)

        self.parent.setMouseTracking(True)

        # Install this object as an eventFilter
        self.parent.installEventFilter(self)

    def eventFilter(self, _, event):
        if event.type() == Qt.QEvent.MouseMove:
            self.SIGNAL_MOVE.emit(event.pos())

        elif event.type() == Qt.QEvent.MouseButtonPress:
            self.SIGNAL_PRESS.emit(event.pos())

        elif event.type() == Qt.QEvent.MouseButtonRelease:
            self.SIGNAL_RELEASE.emit(event.pos())
        # False indicates event should NOT be eaten
        return False


#
# class Contour()
#
#
# class MainWindow(Qt.QMainWindow):
#     def __init__(self, parent=None):
#         Qt.QMainWindow.__init__(self, parent)
#         self.plot = Contour()
#
#         self.setCentralWidget(self.plot)
#
#         toolBar = Qt.QToolBar(self)
#
#         btnSpectrogram = Qt.QToolButton(toolBar)
#         btnContour = Qt.QToolButton(toolBar)
#         btnreplot = Qt.QToolButton(toolBar)
#
#         btnSpectrogram.setText("Spectrogram")
#         btnSpectrogram.setCheckable(True)
#         btnSpectrogram.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
#         toolBar.addWidget(btnSpectrogram)
#
#         btnContour.setText("Contour");
#         btnContour.setCheckable(True)
#         btnContour.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
#         toolBar.addWidget(btnContour)
#
#         btnreplot.setText("replot")
#         # btnreplot.setCheckable(True)
#         btnreplot.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
#         toolBar.addWidget(btnreplot)
#
#         self.addToolBar(toolBar)
#
#         self.connect(btnSpectrogram, Qt.SIGNAL('toggled(bool)'),
#                      self.plot.showSpectrogram)
#         self.connect(btnContour, Qt.SIGNAL('toggled(bool)'),
#                      self.plot.showContour)
#         self.connect(btnreplot, Qt.SIGNAL('clicked(bool)'),
#                      self.plot.plot)
#
#         btnSpectrogram.setChecked(True)
#         btnContour.setChecked(False)
#
#
#         # __init__()
#
#
# #
# # MainWindow()
# #
#
# def make():
#     demo = MainWindow()
#     demo.resize(600, 400)
#     demo.show()
#     return demo
#
# #
# # make()
# #
#
# def main(args):
#     app = Qt.QApplication(args)
#
#     demo = make()
#     sys.exit(app.exec_())
#
#
# main(None)
#
#
# # Admire
# if __name__ == '__main__':
#     if 'settracemask' in sys.argv:
#         # for debugging, requires: python configure.py --trace ...
#         import sip
#
#         sip.settracemask(0x3f)
#
#     main(sys.argv)
#
#     # Local Variables: ***
#     # mode: python ***
#     # End: ***
