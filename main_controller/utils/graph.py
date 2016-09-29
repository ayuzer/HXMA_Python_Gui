# Library imports
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4 import Qwt5 as Qwt

class Plotter(Qwt.QwtPlot):

    def __init__(self, *args):

        Qwt.QwtPlot.__init__(self, *args)

        self.setCanvasBackground(Qt.Qt.white)

        self.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.RightLegend);
        #
        # self.curve.setStyle(Qwt.QwtPlotCurve.Sticks)
        self.curve = self.multi_curve1 = self.multi_curve2 = self.multi_curve3 = \
            self.v_bar1 = self.v_bar2 = self.v_bar3 = None
        #
        solo_curve = [self.curve, 'ongoing scan', False, Qt.Qt.blue]
        multi_curve_1 = [self.multi_curve1, 'w-', True, Qt.Qt.darkCyan]
        multi_curve_2 = [self.multi_curve2, 'wo', True, Qt.Qt.green]
        multi_curve_3 = [self.multi_curve3, 'w+', True, Qt.Qt.magenta]
        vbar_1 = [self.v_bar1, '', False, Qt.Qt.red]
        vbar_2 = [self.v_bar2, '', False, Qt.Qt.red]
        vbar_3 = [self.v_bar3, '', False, Qt.Qt.red]

        self.curves = [solo_curve, multi_curve_1, multi_curve_2, multi_curve_3, vbar_1]
        for curve in self.curves:
            curve[0] = Qwt.QwtPlotCurve(curve[1])
            curve[0].setItemAttribute(Qwt.QwtPlotItem.Legend, curve[2])
            curve[0].setPen(curve[3])
            curve[0].attach(self)

        self._dragBar = False

        self.setMouseTracking(True)
        #
        # self.monitor.connect(VAR.VERT_BAR_POS_X, self.handle_vbar_position)

        mY = Qwt.QwtPlotMarker()
        mY.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        mY.setLineStyle(Qwt.QwtPlotMarker.HLine)
        mY.setYValue(0.0)
        mY.attach(self)

    def new_plot(self, x, y, i = 0):
        self.curves[i+1][0].setData(x, y)
        self.replot()

    def multi_plot(self, x_arr, y_arr):
        for i in range(len(x_arr)):
            self.curves[i+1][0].setData(x_arr[i], y_arr[i])
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

