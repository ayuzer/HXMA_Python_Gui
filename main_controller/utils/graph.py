# Library imports
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import Qt
from PyQt4 import Qwt5 as Qwt
#
# from core import VAR
from functools import partial

class Plotter(Qwt.QwtPlot):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs['monitor']
        del kwargs['monitor']

        self.VAR = kwargs['VAR']
        del kwargs['VAR']

        self.id = kwargs['id']
        del kwargs['id']

        Qwt.QwtPlot.__init__(self, *args)

        self.setCanvasBackground(Qt.Qt.white)

        self.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.RightLegend);

        self.curve = self.multi_curve1 = self.multi_curve2 = self.multi_curve3 = None
        scan_curve = [self.curve, 'ongoing scan', True, Qt.Qt.blue]
        multi_curve_1 = [self.multi_curve1, 'w-', True, Qt.Qt.darkCyan]
        multi_curve_2 = [self.multi_curve2, 'wo', True, Qt.Qt.green]
        multi_curve_3 = [self.multi_curve3, 'w+', True, Qt.Qt.magenta]
        curves = {'scan': scan_curve,
                       'neg': multi_curve_1,
                       'nau': multi_curve_2,
                       'pos': multi_curve_3,
                  }
        self.curves =[]
        for key in curves:
            if self.id == key:
                _curves = [curves[key]]
            elif self.id == 'multi':
                _curves = [curves['neg'], curves['nau'], curves['pos'], ]
            else:
                continue
            for curve in _curves:
                curve[0] = Qwt.QwtPlotCurve(curve[1])
                curve[0].setItemAttribute(Qwt.QwtPlotItem.Legend, curve[2])
                curve[0].setPen(curve[3])
                curve[0].attach(self)
                self.curves.append(curve[0])

        #
        # self.curve.setStyle(Qwt.QwtPlotCurve.Sticks)
        self.vbar_curser = Qwt.QwtPlotCurve('Curser')
        self.vbar_curser.setItemAttribute(Qwt.QwtPlotItem.Legend, True)
        self.vbar_curser.setPen(Qt.Qt.red)
        self.vbar_curser.attach(self)

        self.vbar_max = Qwt.QwtPlotCurve('Max')
        self.vbar_max.setItemAttribute(Qwt.QwtPlotItem.Legend, True)
        self.vbar_max.setPen(Qt.Qt.yellow)
        self.vbar_max.attach(self)

        self.vbar_com = Qwt.QwtPlotCurve('COM')
        self.vbar_com.setItemAttribute(Qwt.QwtPlotItem.Legend, True)
        self.vbar_com.setPen(Qt.Qt.blue)
        self.vbar_com.attach(self)

        self._dragBar = False

        self.setMouseTracking(True)

        self.curser_pos_list = {'scan': self.VAR.VERT_BAR_SCAN_POS,
                       'neg': self.VAR.VERT_BAR_NEG_POS,
                       'nau': self.VAR.VERT_BAR_NAU_POS,
                       'pos': self.VAR.VERT_BAR_POS_POS,
                       }

        self.max_pos_list = {'scan': self.VAR.SCAN_MAX_Y_NUM,
                            'neg': self.VAR.CENT_NEG_MAXY,
                            'nau': self.VAR.CENT_NAU_MAXY,
                            'pos': self.VAR.CENT_POS_MAXY,
                            }

        self.com_pos_list = {'scan': self.VAR.SCAN_COM,
                             'neg': self.VAR.CENT_NEG_COM,
                             'nau': self.VAR.CENT_NAU_COM,
                             'pos': self.VAR.CENT_POS_COM,
                             }

        for key in self.curser_pos_list:
            if self.id == key:
                self.pos = self.curser_pos_list[key]
                self.monitor.connect(self.pos, self.handle_vbar_curser)

        for key in self.max_pos_list:
            if self.id == key:
                self.max_pos = self.max_pos_list[key]
                self.monitor.connect(self.max_pos, self.handle_vbar_max)

        for key in self.com_pos_list:
            if self.id == key:
                self.com_pos = self.com_pos_list[key]
                self.monitor.connect(self.com_pos, self.handle_vbar_com)

        
        mY = Qwt.QwtPlotMarker()
        mY.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        mY.setLineStyle(Qwt.QwtPlotMarker.HLine)
        mY.setYValue(0.0)
        mY.attach(self)


    def handle_vbar_curser(self, pv_name):
        value = self.monitor.get_value(pv_name)
        if not value == None:
            self.vertical_bar(value, 'curser')

    def handle_vbar_max(self, pv_name):
        value = self.monitor.get_value(pv_name)
        if not value == None:
            self.vertical_bar(value, 'max')

    def handle_vbar_com(self, pv_name):
        value = self.monitor.get_value(pv_name)
        if not value == None:
            self.vertical_bar(value, 'com')

    def mouseReleaseEvent(self, event):
        print "Mouse release", event.pos()
        self._dragBar = False

    def vertical_bar(self, bar_pos, type):
        if isinstance(bar_pos, list):
            pass
        elif bar_pos == None :
            bar_pos = [0, 1, -1]
        else:
            pos = self.monitor.get_value(self.pos)
            print repr(pos) + type
            if not pos == None:
                pos[0] = bar_pos
                bar_pos = pos
            else:
                bar_pos = [bar_pos, 1, -1]
        x = [bar_pos[0], bar_pos[0]]
        y = [bar_pos[1], bar_pos[2]]
        if type == 'curser':
            self.vbar_curser.setData(x, y)
        elif type == 'max':
            self.vbar_max.setData(x, y)
        elif type == 'com':
            self.vbar_com.setData(x, y)
        self.replot()

    def new_plot(self, x, y):
        self.curves[0].setData(x, y)
        self.handle_vbar_curser(self.pos)
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

    def mouseMoveEvent(self, event):
        # print "MOUSE MOVE", event.pos()
        canvasPos = self.canvas().mapFrom(self, event.pos())
        xFloat = self.invTransform(Qwt.QwtPlot.xBottom, canvasPos.x())
        yFloat = self.invTransform(Qwt.QwtPlot.yLeft, canvasPos.y())

        # print "xFloat", xFloat, "yFloat", yFloat

        if self._dragBar:
            pos =self.monitor.get_value(self.pos)
            self.monitor.update(self.pos, [xFloat, pos[1], pos[2]])

    def mousePressEvent(self, event):
        print "Mouse PRESS", event.pos()

        canvasPos = self.canvas().mapFrom(self, event.pos())
        xFloat = self.invTransform(Qwt.QwtPlot.xBottom, canvasPos.x())
        yFloat = self.invTransform(Qwt.QwtPlot.yLeft, canvasPos.y())

        x1 = self.invTransform(Qwt.QwtPlot.xBottom, 0)
        x2 = self.invTransform(Qwt.QwtPlot.xBottom, 2)

        diff = abs(x1 - x2)
        print "2 pixel diff", diff

        cur_vbar_value = self.monitor.get_value(self.pos)[0]

        if cur_vbar_value > (xFloat - diff) and cur_vbar_value < (xFloat + diff):
            self._dragBar = True

    def terminate(self):
        self.monitor.disconnect(self)




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

