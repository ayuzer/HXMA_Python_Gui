# System imports
import math
import random
import time

# Library imports
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

# App imports
from utils import to_rad
import settings
from settings import KEY
from settings import CLICK_REGIONS
from settings import Z_MM_WHITE_BEAM
from settings import GRAPHIC

from pixel_mapper import PixelMapper
from camera_positioner import VAR as CP_VAR
from optics_table import VAR as OT_VAR
from core import VAR as CORE_VAR
from line import LineClip

LINE_DATA = {

    OT_VAR.TABLE_ACTUAL :{
        KEY.COLOR : QtGui.QColor(0, 255, 0),
        KEY.LINE_STYLE : Qt.Qt.DotLine,
        KEY.LINE_WIDTH : 1,
        KEY.QT_LAYER : 10
    },
    OT_VAR.TABLE_PROPOSED :{
        KEY.COLOR : QtGui.QColor(0, 255, 0),
        KEY.LINE_STYLE : Qt.Qt.SolidLine,
        KEY.LINE_WIDTH : 1,
        KEY.QT_LAYER : 11

    },
    OT_VAR.FIS_ACTUAL :{
        KEY.COLOR : QtGui.QColor(0 , 0, 255),
        KEY.LINE_STYLE : Qt.Qt.DotLine,
        KEY.LINE_WIDTH : 1,
        KEY.QT_LAYER : 10

    },
    OT_VAR.FIS_PROPOSED :{
        KEY.COLOR : QtGui.QColor(0, 0, 255),
        KEY.LINE_STYLE : Qt.Qt.SolidLine,
        KEY.LINE_WIDTH : 1,
        KEY.QT_LAYER : 11
    },

    CP_VAR.LASER_ACTUAL : {
        KEY.COLOR : QtGui.QColor(0, 255, 0),
        KEY.LINE_WIDTH : 1,
        KEY.LINE_STYLE : Qt.Qt.DotLine,
        KEY.QT_LAYER : 10
    },
    #CP_VAR.LASER_ACTUAL : {
    #    KEY.COLOR : QtGui.QColor(186, 255, 186),
    #    KEY.LINE_WIDTH : 2,
    #    KEY.LINE_STYLE : Qt.Qt.DotLine
    #},
    CP_VAR.LASER_PROPOSED : {
        KEY.COLOR : QtGui.QColor(0, 205, 0),
        KEY.LINE_WIDTH : 1,
        KEY.LINE_STYLE : Qt.Qt.SolidLine,
        KEY.QT_LAYER : 11
    },
    CP_VAR.DETECTOR_ACTUAL : {
        KEY.COLOR : QtGui.QColor(186, 186, 255),
        KEY.LINE_WIDTH : 1,
        KEY.LINE_STYLE : Qt.Qt.DotLine
    },
    CP_VAR.DETECTOR_PROPOSED : {
        KEY.COLOR : QtGui.QColor(0, 0, 205),
        KEY.LINE_WIDTH : 1,
        KEY.LINE_STYLE : Qt.Qt.SolidLine,
        KEY.QT_LAYER : 11
    },
    CORE_VAR.BEAM_VDISP_ACTUAL : {
        KEY.COLOR : QtGui.QColor(205, 0, 0),
        KEY.LINE_WIDTH : 1,
        KEY.LINE_STYLE : Qt.Qt.DotLine,
        KEY.QT_LAYER : 4
    },
    CORE_VAR.BEAM_VDISP_PROPOSED : {
        KEY.COLOR : QtGui.QColor(205, 0, 0),
        KEY.LINE_WIDTH : 1,
        KEY.LINE_STYLE : Qt.Qt.SolidLine,
        KEY.QT_LAYER : 5
    }
}

class MyScene(QtGui.QGraphicsScene):

    def __init__(self, *args, **kwargs):

        super(MyScene, self).__init__(*args, **kwargs)

        print "MyScene() called"

        # self.dimensions = None
        self.mapper = None

        self._frame = None

        # TODO: seems foolish to have seperate item caches for cam_pos
        # TODO: and beam.  Should really refactor this and make it generic
        self._cam_pos_item = {}
        self._cam_pos_erase_enabled = True

        self._beam_item = {}
        self._beam_erase_enabled = True

        self._cursor_height_item = None

        self.debug_line_list    = []
        self.debug_line_added   = []
        self.random_line_list   = []
        self.grid_line_list     = []
        self.click_region_lines = []
        self.crosshair_lines    = []

        self.color_crosshair    = QtGui.QColor(180, 180, 180)
        self.color_region       = QtGui.QColor(0, 139, 0)
        self.color_grid         = QtGui.QColor(200, 200, 200)
        self.color_white_beam   = QtGui.QColor(255, 200, 200)
        self.color_frame        = QtGui.QColor(0, 0, 0)
        self.color_beam         = QtGui.QColor(205, 0, 0)

        self.style_crosshair = Qt.Qt.DotLine
        self.style_grid = Qt.Qt.DashLine

    def beam_test(self):

        disp = random.randint(-500, 3000)

        redness = 10
        for angle in xrange(-60, 61, 5):
            color = QtGui.QColor(redness, 0, 0)
            redness = redness + 8
            self.beam_draw(settings.BEAM_ORIGIN_X, settings.BEAM_ORIGIN_Z,
                    disp, angle, CORE_VAR.BEAM_VDISP_PROPOSED, color=color)

    def set_dimensions(self, graphic):

        # self.dimensions = dimensions
        self.mapper = PixelMapper(graphic)
        self.debug_line_list = self.debug_lines_init(indent=1)

    def ground_line_draw(self):

        print "Ground line draw ========================="
        print "X MIN:", self.mapper.get_x_mm_min()
        print "X MAX:", self.mapper.get_x_mm_max()

        self.draw_line_mm(
            self.mapper.get_x_mm_min(), 0,
            self.mapper.get_x_mm_max(), 0,
            color=self.color_grid,
            style=Qt.Qt.DashLine)

    def white_beam_draw(self):

        self.draw_line_mm(
            self.mapper.get_x_mm_min(), Z_MM_WHITE_BEAM,
            self.mapper.get_x_mm_max(), Z_MM_WHITE_BEAM,
            color=self.color_white_beam,
            style=Qt.Qt.DashLine, qt_layer=3)

    def cam_pos_erase_enable_set(self, value):
        self._cam_pos_erase_enabled = value

    def beam_erase_enable_set(self, value):
        self._beam_erase_enabled = value

    def cam_pos_erase(self, var_name):

        # print "cam_pos_erase(): _cam_pos_erase_enabled:", self._cam_pos_erase_enabled
        if not self._cam_pos_erase_enabled:
            # print "Camera positioner erase disabled"
            return

        new_list = {}
        for key, data in self._cam_pos_item.iteritems():
            if var_name is None or var_name == data.get(KEY.PV):
                item = data.get(KEY.ITEM)
                # print "removing CP item"
                self.removeItem(item)
            else:
                new_list[key] = data
        self._cam_pos_item = new_list

    def beam_erase(self, var_name):

        # print "beam_erase(): _beam_enabled:", self._cam_pos_erase_enabled
        if not self._beam_erase_enabled:
            # print "Beam erase disabled"
            return

        new_list = {}
        for key, data in self._beam_item.iteritems():
            if var_name is None or var_name == data.get(KEY.PV):
                item = data.get(KEY.ITEM)
                # print "removing BEAM item"
                self.removeItem(item)
            else:
                new_list[key] = data
        self._beam_item = new_list

    def cam_pos_draw(self, start_x, start_z, stop_x, stop_z, var_name):

        #print "want to draw a CP object: %s" % var_name
        #print "height_mm", height_mm
        #print "angle_deg", angle_deg

        try:
            cache_key = "%s_%.3f_%.3f_%.3f_%.3f" % \
                        (var_name, start_x, start_z, stop_x, stop_z)
        except Exception, e:
            msg = "cam_pos_draw(): exception %s for %s" % (str(e), var_name)
            raise ValueError(msg)

        # print "This is the cache key:", cache_key

        data = self._cam_pos_item.get(cache_key)
        if data:
            # print "Have already rendered this item"
            return

        # Erase any existing item(s)
        self.cam_pos_erase(var_name)

        if None in [start_x, start_z, stop_x, stop_z]:
            print "Got None: Cant render %s" % var_name
            return

        data = LINE_DATA.get(var_name)
        color = data.get(KEY.COLOR)
        width = data.get(KEY.LINE_WIDTH)
        style = data.get(KEY.LINE_STYLE)
        qt_layer = data.get(KEY.QT_LAYER, 10)

        item = self.draw_line_mm(start_x, start_z, stop_x, stop_z,
            color=color, width=width, style=style, qt_layer=qt_layer)

        if not item:
            return

        self._cam_pos_item[cache_key] = {KEY.ITEM : item, KEY.PV: var_name}

    def beam_draw(self, origin_x_mm, origin_z_mm, vert_disp_mm,
                  angle_deg, var_name, color=None):

        try:
            cache_key = "%s_%.3f_%.3f_%.3f_%.3f" % \
                        (var_name, origin_x_mm, origin_z_mm, vert_disp_mm, angle_deg)

        except Exception, e:
            msg = "beam_draw(): exception %s for %s" % (str(e), var_name)
            print msg
            cache_key = None

            # raise ValueError(msg)

        # print "This is the cache key:", cache_key

        data = self._beam_item.get(cache_key)
        if data:
            # print "Have already rendered this item"
            return

        # Erase any existing item(s)
        self.beam_erase(var_name)

        if None in [cache_key, origin_x_mm, origin_z_mm, vert_disp_mm, angle_deg]:
            print "Got None: Cant render %s" % var_name
            return

        data = LINE_DATA.get(var_name)

        if color is None:
            color = data.get(KEY.COLOR)

        width = data.get(KEY.LINE_WIDTH)
        style = data.get(KEY.LINE_STYLE)
        qt_layer = data.get(KEY.QT_LAYER, 10)

        start_z = origin_z_mm + float(vert_disp_mm)
        start_x = origin_x_mm
        stop_x = settings.X_MM_BEAM_END
        z_diff = math.tan(to_rad(angle_deg)) * (stop_x - start_x)

        # print "angle: %f adjacent: %f z_diff: %f" % (angle_deg, (stop_x_mm - start_x_mm), z_diff)

        stop_z = start_z + z_diff

        item = self.draw_line_mm(start_x, start_z, stop_x, stop_z,
            color=color, width=width, style=style, qt_layer=qt_layer)

        if not item:
            return

        self._beam_item[cache_key] = {KEY.ITEM : item, KEY.PV: var_name}

    def frame_draw(self):
        """
        If I put a frame on the graphicsView, I cannot figure out how to
        prevent the pixmap from scrolling by one or two pixels.  However
        I can draw a frame on the pixmap and get the same effect without
        the scrolling
        """

        indent = 0

        height = self.mapper.get_z_pixels()
        width = self.mapper.get_x_pixels()

        frame_lines = [
            (indent, 0, indent, height-1                    ), # left
            (0, indent, width-1, indent                     ), # bottom
            (0, height-1-indent, width-1, height-1-indent   ), # top
            (width-1-indent, 0, width-1-indent, height-1    ), # right
        ]

        for item in frame_lines:
            self.draw_line_pixel(
                item[0], item[1], item[2], item[3],
                color=self.color_frame)

    def debug_lines_init(self, indent=0):

        line_item_list = []

        height = self.mapper.get_z_pixels()
        width = self.mapper.get_x_pixels()
        debug_lines = [
            (0, 0, width-1, height-1),
            (0, height-1, width-1, 0),

            (indent, 0, indent, height-1                    ), # left
            (0, indent, width-1, indent                     ), # bottom
            (0, height-1-indent, width-1, height-1-indent   ), # top
            (width-1-indent, 0, width-1-indent, height-1    ), # right
        ]

        for item in debug_lines:
            line = QtCore.QLineF(item[0], item[1], item[2], item[3])
            line_item_list.append(line)

        return line_item_list

    def debug_lines_draw(self):

        for line in self.debug_line_list:
            color = Qt.Qt.red
            pen = Qt.QPen(Qt.Qt.DashLine)
            pen.setColor(color)
            item = self.addLine(line, pen=pen)
            self.debug_line_added.append(item)

    def debug_lines_erase(self):
        for line in self.debug_line_added:
            self.removeItem(line)
        self.debug_line_added = []

    def setup(self):

        pixmap = QtGui.QPixmap()
        pixmap.load(GRAPHIC.FILE_NAME)

        x_pixels = self.mapper.get_x_pixels()
        z_pixels = self.mapper.get_z_pixels()

        size = QtCore.QSize(x_pixels, z_pixels)

        print "======= SIZE --------"
        print size
        print repr(size)

#        self.scaled_pixmap = pixmap.scaled(size, Qt.Qt.KeepAspectRatio,
#            transformMode=QtCore.Qt.SmoothTransformation)
        self.scaled_pixmap = pixmap.scaled(size, Qt.Qt.IgnoreAspectRatio,
            transformMode=QtCore.Qt.SmoothTransformation)

        self.pixmap_item = QtGui.QGraphicsPixmapItem(self.scaled_pixmap)

        #print "=============== PIXMAP ITEM ============="
        #print repr(pixmap_item)
        #print dir(pixmap_item)
        #print pixmap_item.boundingRect()
        #print "========================================="

        self.addItem(self.pixmap_item)
        self.frame_draw()

    def cursor_height_erase(self):
        if self._cursor_height_item:
            self.removeItem(self._cursor_height_item)
            self._cursor_height_item = None

    def cursor_height_render(self, x_pixel, z_pixel, widget):

        self.cursor_height_erase()
        width = 120
        height = 20

        if z_pixel < 1 or z_pixel > (self.mapper.get_z_pixel_max() - height):
            # print "skip render z"
            return

        # if x_pixel < 1 or x_pixel > (self.mapper.get_x_pixel_max() - width):
        #     # print "skip render x", x_pixel, self.mapper.get_x_pixel_max()
        #     return

        widget.setGeometry(x_pixel, z_pixel, width, height)

        try:
            item = self.addWidget(widget)
        except Exception, e:
            print "Got exception adding widget: %s" % str(e)
            item = None

        if item:
            self._cursor_height_item = item
            item.setZValue(200)

    def add_widget(self, widget, x_mm, z_mm, width_pixels, height_pixels):

        x_start_pixel = self.mapper.get_x_pixel(x_mm)
        z_start_pixel = self.mapper.get_z_pixel(z_mm)
        # x_stop_pixel = x_start_pixel + width_pixels
        # z_stop_pixel = z_start_pixel + height_pixels

        widget.setGeometry(x_start_pixel, z_start_pixel,
            width_pixels, height_pixels)

        try:
            proxy = self.addWidget(widget)
        except Exception, e:
            print "Got exception adding widget: %s" % str(e)

        # This puts the widgets on the "top" layer (i.e., above the grid)
        proxy.setZValue(100)

        print "Adding widget to scene", \
            x_start_pixel, z_start_pixel, \
            width_pixels, height_pixels, \
            repr(widget)

        # proxy.setGeometry(x_start_pixel, z_start_pixel,
        #     width_pixels, height_pixels)

        # proxy.setGeometry(QtCore.QRectF(x_start_pixel, z_start_pixel,
        #     width_pixels, height_pixels))

        # widget.setGeometry(x_start_pixel, z_start_pixel,
        #     width_pixels, height_pixels)

        return proxy

    def crosshairs_draw(self, x_pixel, z_pixel):

        x_pixel = float(x_pixel)
        z_pixel = float(z_pixel)

        mapper = self.get_mapper()
        x_pixel_max = mapper.get_x_pixels() - 1
        z_pixel_max = mapper.get_z_pixels() - 1

        self.crosshair_lines.append(self.draw_line_pixel(
            x_pixel, 0, x_pixel, z_pixel_max,
            color=self.color_crosshair,
            style=self.style_crosshair))

        self.crosshair_lines.append(self.draw_line_pixel(
            0, z_pixel, x_pixel_max, z_pixel,
            color=self.color_crosshair,
            style=self.style_crosshair))

    def crosshairs_erase(self):
        for item in self.crosshair_lines:
            self.removeItem(item)

        self.crosshair_lines = []

    def order(self, item_1, item_2):
        f1 = float(item_1)
        f2 = float(item_2)
        if f2 < f1:
            temp = f1
            f1 = f2
            f2 = temp
        return f1, f2

    def click_regions_draw(self):
        for key, data in CLICK_REGIONS.iteritems():
            x1, x2 = self.order(data.get(KEY.X_MM_START), data.get(KEY.X_MM_STOP))
            z1, z2 = self.order(data.get(KEY.Z_MM_START), data.get(KEY.Z_MM_STOP))
            self.click_region_lines.append(self.draw_line_mm(x1, z1, x2, z1, color=self.color_region))
            self.click_region_lines.append(self.draw_line_mm(x1, z1, x1, z2, color=self.color_region))
            self.click_region_lines.append(self.draw_line_mm(x1, z2, x2, z2, color=self.color_region))
            self.click_region_lines.append(self.draw_line_mm(x2, z1, x2, z2, color=self.color_region))

    def click_regions_erase(self):
        for item in self.click_region_lines:
            self.removeItem(item)
        self.click_region_lines = []

    def get_region_pixel(self, x_pixel, z_pixel):

        x_mm = self.mapper.get_x_mm(x_pixel)
        z_mm = self.mapper.get_z_mm(z_pixel)

        return self.get_region(x_mm, z_mm)

    def get_region(self, x_mm, z_mm):
        """
        Returns the first value in the CLICK_REGIONS dict into which the
        specified (x, z) position falls.
        """

        for key, data in CLICK_REGIONS.iteritems():
            x1, x2 = self.order(data.get(KEY.X_MM_START), data.get(KEY.X_MM_STOP))
            z1, z2 = self.order(data.get(KEY.Z_MM_START), data.get(KEY.Z_MM_STOP))

            if x_mm > x1 and x_mm < x2 and z_mm > z1 and z_mm < z2:
                data[KEY.KEY] = key
                return data

    def get_mapper(self):
        return self.mapper

    def grid_draw(self, x_mm, z_mm):

        x_pos = 0
        while True:
            if x_pos >= self.mapper.get_x_mm_max():
                break

            if x_pos > self.mapper.get_x_mm_min():
                item = self.draw_line_mm(
                    x_pos, self.mapper.get_z_mm_min(),
                    x_pos, self.mapper.get_z_mm_max(),
                    color=self.color_grid, style=self.style_grid)
                self.grid_line_list.append(item)
            x_pos += x_mm

        x_pos = -1 * x_mm

        while True:
            if x_pos <= self.mapper.get_x_mm_min():
                break

            if x_pos < self.mapper.get_x_mm_max():
                item = self.draw_line_mm(
                    x_pos, self.mapper.get_z_mm_min(),
                    x_pos, self.mapper.get_z_mm_max(),
                    color=self.color_grid, style=self.style_grid)
                self.grid_line_list.append(item)

            x_pos -= x_mm

        z_pos = 0
        while True:
            if z_pos >= self.mapper.get_z_mm_max():
                break

            if z_pos > self.mapper.get_z_mm_min():
                item = self.draw_line_mm(
                    self.mapper.get_x_mm_min(), z_pos,
                    self.mapper.get_x_mm_max(), z_pos,
                    color=self.color_grid, style=self.style_grid)
                self.grid_line_list.append(item)

            z_pos += z_mm

        z_pos = -1 * z_mm

        while True:
            if z_pos <= self.mapper.get_z_mm_min():
                break

            if z_pos < self.mapper.get_z_mm_max():
                item = self.draw_line_mm(
                    self.mapper.get_x_mm_min(), z_pos,
                    self.mapper.get_x_mm_max(), z_pos,
                    color=self.color_grid, style=self.style_grid)
                self.grid_line_list.append(item)

            z_pos -= z_mm

    def grid_erase(self):
        for item in self.grid_line_list:
            self.removeItem(item)
        self.grid_line_list = []

    def random_lines_draw(self, count):

        for _ in xrange(count):

            x_min = self.mapper.get_x_mm_min()
            x_max = self.mapper.get_x_mm_max()

            z_min = self.mapper.get_z_mm_min()
            z_max = self.mapper.get_z_mm_max()

            x_start = random.randint(int(x_min), int(x_max))
            x_stop = random.randint(int(x_min), int(x_max))

            z_start = random.randint(int(z_min), int(z_max))
            z_stop = random.randint(int(z_min), int(z_max))

            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)

            color = QtGui.QColor(r, g, b)
            item = self.draw_line_mm(x_start, z_start, x_stop, z_stop, color=color)

            self.random_line_list.append(item)

    def random_lines_erase(self):

        for item in self.random_line_list:
            self.removeItem(item)

        self.random_line_list = []

    def draw_line_mm(self, x_mm_start, z_mm_start, x_mm_stop, z_mm_stop,
                  color=Qt.Qt.blue,
                  style=Qt.Qt.SolidLine,
                  width=1,
                  qt_layer=10):

        x_start = self.mapper.get_x_pixel(x_mm_start)
        x_stop  = self.mapper.get_x_pixel(x_mm_stop)
        z_start = self.mapper.get_z_pixel(z_mm_start)
        z_stop  = self.mapper.get_z_pixel(z_mm_stop)

        return self.draw_line_pixel(x_start, z_start,
            x_stop, z_stop, color=color, style=style, width=width, qt_layer=qt_layer)

    def draw_line_pixel(self, x_start, z_start, x_stop, z_stop,
                        color=Qt.Qt.blue,
                        style=Qt.Qt.SolidLine,
                        width=1,
                        qt_layer=10):

        # print "draw_line_pixel() called: ", x_start, z_start, x_stop, z_stop, \
        #     repr(color), repr(style)

        line = LineClip(x_start, z_start, x_stop, z_stop, self.mapper)
        x_start, z_start, x_stop, z_stop = line.clip()

        if x_start is None:
            print "draw_line_pixel(): refusing to render non visible"
            return

        # ----- Sanity check the line clipping
        z_pixel_max = self.mapper.get_z_pixel_max()
        z_pixel_min = self.mapper.get_z_pixel_min()
        x_pixel_max = self.mapper.get_x_pixel_max()
        x_pixel_min = self.mapper.get_x_pixel_min()

        clipped = []
        if z_start > z_pixel_max or z_start < z_pixel_min:
            clipped.append("z_start %d (min: %d max %d)" %
                           (z_start, z_pixel_min, z_pixel_max))
        if z_stop > z_pixel_max or z_stop < z_pixel_min:
            clipped.append("z_stop %d (min: %d max %d)" %
                           (z_stop, z_pixel_min, z_pixel_max))
        if x_start > x_pixel_max or x_start < x_pixel_min:
            clipped.append("x_start %d (min: %d max %d)" %
                           (x_start, x_pixel_min, x_pixel_max))
        if x_stop > x_pixel_max or x_stop < x_pixel_min:
            clipped.append("x_stop %d (min: %d max %d)" %
                           (x_stop, x_pixel_min, x_pixel_max))
        if clipped:
            msg = "Refusing to render a clipped line:"
            msg += '\n'.join(clipped)
            raise ValueError(msg)

        # ----- End of line clip sanity check


        line = QtCore.QLineF(x_start, z_start, x_stop, z_stop)
        pen = Qt.QPen()
        pen.setStyle(style)
        pen.setColor(color)
        pen.setWidth(width)

        item = self.addLine(line, pen=pen)
        item.setZValue(qt_layer)

        return item
