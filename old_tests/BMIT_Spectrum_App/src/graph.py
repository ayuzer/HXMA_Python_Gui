# Library imports
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4 import Qwt5 as Qwt

class Plotter(Qwt.QwtPlot):

    def __init__(self, *args):

        Qwt.QwtPlot.__init__(self, *args)

        self.setCanvasBackground(Qt.Qt.white)

        # Set the title
        title = Qwt.QwtText("Title")
        titleFont = QtGui.QFont('SansSerif', 10)
        titleFont.setWeight(QtGui.QFont.Light)
        title.setFont(titleFont)
        self.setTitle(title)

        # self.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.BottomLegend);
        self.curve = Qwt.QwtPlotCurve()

        # self.curve.setStyle(Qwt.QwtPlotCurve.Sticks)

        self.curve.setPen(Qt.QPen(Qt.Qt.blue))
        self.curve.attach(self)

        mY = Qwt.QwtPlotMarker()
        mY.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        mY.setLineStyle(Qwt.QwtPlotMarker.HLine)
        mY.setYValue(0.0)
        mY.attach(self)

        # Set the title
        xAxisLabel = Qwt.QwtText("X Value")
        xAxisLabel.setFont(titleFont)

        yAxisLabel = Qwt.QwtText("Y Value")
        yAxisLabel.setFont(titleFont)

        self.setAxisTitle(Qwt.QwtPlot.xBottom, xAxisLabel)
        self.setAxisTitle(Qwt.QwtPlot.yLeft, yAxisLabel)

    def new_plot(self, data):

        x = [point[0] for point in data]
        y = [point[1] for point in data]

        self.curve.setData(x, y)
        self.replot()

class MouseTracker(Qt.QObject):

    SIGNAL = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, plotter):

        self.plotter = plotter
        self.parent = self.plotter.canvas()

        super(MouseTracker, self).__init__(self.parent)

        self.parent.setMouseTracking(True)

        # Install this object as an eventFilter
        self.parent.installEventFilter(self)

    def eventFilter(self, _, event):
        if event.type() == Qt.QEvent.MouseMove:

            self.SIGNAL.emit(event.pos())

        # False indicates event should NOT be eaten
        return False

class PlotterLog(Qwt.QwtPlot):

    def __init__(self, *args):

        Qwt.QwtPlot.__init__(self, *args)

        self.setCanvasBackground(Qt.Qt.white)
        #self.alignScales()

        # self.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.BottomLegend);
        self.curve = Qwt.QwtPlotCurve('Unfiltered Spectrum')
        self.curve.setPen(Qt.QPen(Qt.Qt.red))
        self.curve.attach(self)

        # Make 100 "gray" curves
        self.curve_gray = []
        for i in xrange(50):
            curve = Qwt.QwtPlotCurve('Cumulative Filter Attenuation')
            if i > 0:
                curve.setItemAttribute(Qwt.QwtPlotItem.Legend, False)
            curve.setPen(Qt.QPen(Qt.Qt.gray))
            curve.attach(self)
            self.curve_gray.append(curve)

        self.curve2 = Qwt.QwtPlotCurve('Filtered Spectrum')
        self.curve2.setPen(Qt.QPen(Qt.Qt.blue))
        self.curve2.attach(self)

        self.curve3 = Qwt.QwtPlotCurve()
        self.curve3.setItemAttribute(Qwt.QwtPlotItem.Legend, False)
        self.curve3.setPen(Qt.QPen(Qt.Qt.green))
        self.curve3.attach(self)

        self.curve_white = Qwt.QwtPlotCurve()
        self.curve_white.setItemAttribute(Qwt.QwtPlotItem.Legend, False)
        self.curve_white.setPen(Qt.QPen(Qt.Qt.white))
        self.curve_white.attach(self)

        self.curve_green = Qwt.QwtPlotCurve('Mono Energy')
        self.curve_green.setPen(Qt.QPen(Qt.Qt.darkGreen))
        self.curve_green.attach(self)

        mY = Qwt.QwtPlotMarker()
        mY.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        mY.setLineStyle(Qwt.QwtPlotMarker.HLine)
        mY.setYValue(0.0)
        mY.attach(self)

        self.setAxisScaleEngine(Qwt.QwtPlot.xBottom, Qwt.QwtLog10ScaleEngine())
        self.setAxisScaleEngine(Qwt.QwtPlot.yLeft, Qwt.QwtLog10ScaleEngine())

        # Add grid to plot
        grid = Qwt.QwtPlotGrid()
        pen = Qt.QPen(Qt.Qt.DotLine)
        pen.setColor(Qt.Qt.black)
        pen.setWidth(0)
        grid.setPen(pen)
        grid.attach(self)

    def lock(self, state):

        if state == True:
            print "plotter lock scale"
            xScale = self.axisScaleDiv(Qwt.QwtPlot.xBottom)
            self.setAxisScaleDiv(Qwt.QwtPlot.xBottom, xScale)

            yScale = self.axisScaleDiv(Qwt.QwtPlot.yLeft)
            self.setAxisScaleDiv(Qwt.QwtPlot.yLeft, yScale)

        else:
            print "plotter unlock scale"
            self.setAxisAutoScale(Qwt.QwtPlot.xBottom)
            self.setAxisAutoScale(Qwt.QwtPlot.yLeft)
            self.setAxisScaleEngine(Qwt.QwtPlot.xBottom, Qwt.QwtLog10ScaleEngine())
            self.setAxisScaleEngine(Qwt.QwtPlot.yLeft, Qwt.QwtLog10ScaleEngine())

    def handle_mouse_position_signal(self, position):

        if self.mouse_position_callback:
            x = self.invTransform(Qwt.QwtPlot.xBottom, position.x())
            y = self.invTransform(Qwt.QwtPlot.yLeft, position.y())
            self.mouse_position_callback(x, y)

    def set_mouse_position_callback(self, callback):

        self.mouse_position_callback = callback
        self.tracker = MouseTracker(self)
        self.tracker.SIGNAL.connect(self.handle_mouse_position_signal)

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

    def set_title(self, title):

        title = Qwt.QwtText(title)
        titleFont = QtGui.QFont('Monospace', 10)
        titleFont.setWeight(QtGui.QFont.Light)
        title.setFont(titleFont)
        self.setTitle(title)

    def set_legend(self):
        legend = Qwt.QwtLegend()
        self.insertLegend(legend, Qwt.QwtPlot.BottomLegend)

    #def alignScales(self):
    #
    #    self.canvas().setFrameStyle(Qt.QFrame.Box | Qt.QFrame.Plain)
    #    self.canvas().setLineWidth(1)
    #
    #    for i in range(Qwt.QwtPlot.axisCnt):
    #        scaleWidget = self.axisWidget(i)
    #
    #        if scaleWidget:
    #            scaleWidget.setMargin(0)
    #        scaleDraw = self.axisScaleDraw(i)
    #
    #        if scaleDraw:
    #            scaleDraw.enableComponent(
    #                Qwt.QwtAbstractScaleDraw.Backbone, False)

    #def plot_mono_energy(self, energy):
    #
    #    yScale = self.axisScaleDiv(Qwt.QwtPlot.yLeft)
    #
    #    print "this is the y_scale", yScale
    #    print "this is the y_scale", repr(yScale)
    #    print dir(yScale)
    #    print "lower bound", yScale.lowerBound()
    #    print "upper bound", yScale.upperBound()
    #    print "range", yScale.range()
    #
    #    x = [energy, energy]
    #    y = [yScale.lowerBound(), yScale.upperBound()]
    #
    #    self.curve_green.setData(x, y)
    #    self.replot()

    def new_plot(self, data1, data2=None, data3=None, white=None, gray=None, mono_energy=None):

        print "==============================="
        print "new plot called:"
        print "======================="
        bogus_point = [(0, 0)]

        if data1:
            x = [point[0] for point in data1]
            y = [point[1] for point in data1]
            self.curve.setData(x, y)
            bogus_point = [data1[0]]
            min_y = min(y)

        for i in xrange(50):
            curve = self.curve_gray[i]
            d = bogus_point
            if gray:
                try:
                    d = gray[i]
                except:
                    pass

            x = [point[0] for point in d]
            y = [point[1] for point in d]
            curve.setData(x, y)

        if not data2:
            data2 = bogus_point

        x = [point[0] for point in data2]
        y = [point[1] for point in data2]
        self.curve2.setData(x, y)

        if not data3:
            data3 = bogus_point

        x = [point[0] for point in data3]
        y = [point[1] for point in data3]
        self.curve3.setData(x, y)

        if not white:
            white = bogus_point

        x = [point[0] for point in white]
        y = [point[1] for point in white]
        self.curve_white.setData(x, y)

        # Get rid of existing mono energy plot by plotting bogus point
        green = bogus_point
        x = [point[0] for point in green]
        y = [point[1] for point in green]
        self.curve_green.setData(x, y)

        if mono_energy:
            # If mono energy is to be plotted, determine current axes bounds
            # based on spectrum plot without the mono energey, then add it
            self.updateAxes()
            yScale = self.axisScaleDiv(Qwt.QwtPlot.yLeft)

            x = [mono_energy, mono_energy]
            y = [yScale.lowerBound(), yScale.upperBound()]
            y = [min_y, yScale.upperBound()]
            self.curve_green.setData(x, y)

        self.replot()


