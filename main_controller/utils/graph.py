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

        self.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.BottomLegend);

        # self.curve.setStyle(Qwt.QwtPlotCurve.Sticks)
        self.curve = Qwt.QwtPlotCurve('ongoing scan')
        self.curve.setItemAttribute(Qwt.QwtPlotItem.Legend, False)
        self.curve.setPen(Qt.QPen(Qt.Qt.blue))
        self.curve.attach(self)

        self.curve1 = Qwt.QwtPlotCurve('w-')
        self.curve1.setItemAttribute(Qwt.QwtPlotItem.Legend, False)
        self.curve1.setPen(Qt.QPen(Qt.Qt.red))
        self.curve1.attach(self)

        self.curve2 = Qwt.QwtPlotCurve('wo')
        self.curve2.setItemAttribute(Qwt.QwtPlotItem.Legend, False)
        self.curve2.setPen(Qt.QPen(Qt.Qt.darkGreen))
        self.curve2.attach(self)

        self.curve3 = Qwt.QwtPlotCurve('w+')
        self.curve3.setItemAttribute(Qwt.QwtPlotItem.Legend, False)
        self.curve3.setPen(Qt.QPen(Qt.Qt.magenta))
        self.curve3.attach(self)

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

    def new_plot(self, x, y):
        self.curve.setData(x, y)
        self.replot()

    def multi_plot(self, x_arr, y_arr):
        for i in range(len(x_arr)):
            if i == 0:
                curve = self.curve1
            elif i == 1:
                curve = self.curve2
            else:
                curve = self.curve3
            curve.setData(x_arr[i], y_arr[i])
        self.replot()
        self.set_legend()

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

