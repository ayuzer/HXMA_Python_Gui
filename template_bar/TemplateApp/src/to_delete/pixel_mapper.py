import settings

class PixelMapper(object):

    def __init__(self, graphic):
        print "PixelMapper init called"

        self.graphic = graphic

        x_pixels = float(graphic.KEDGE_MONO_PIXEL_X) - float(graphic.MRT_PIXEL_X)
        x_mm = settings.X_MM_MRT - settings.X_MM_KEDGE_MONO

        z_pixels = float(graphic.FLOOR_PIXEL_Z) - float(graphic.WHITE_BEAM_PIXEL_Z)
        z_mm = settings.Z_MM_WHITE_BEAM

        self.x_mm_per_pixel = float(x_mm) / float(x_pixels)
        self.z_mm_per_pixel = float(z_mm) / float(z_pixels)

        self.z_ref_pixel = float(graphic.WHITE_BEAM_PIXEL_Z)
        self.z_ref_mm = float(settings.Z_MM_WHITE_BEAM)

        self.x_ref_pixel = float(graphic.MRT_PIXEL_X)
        self.x_ref_mm = float(settings.X_MM_MRT)

        print "========================================"
        print "self.x_mm_per_pixel", self.x_mm_per_pixel
        print "self.z_mm_per_pixel", self.z_mm_per_pixel
        print "========================================"

    def get_x_pixels(self):
        return self.graphic.X_PIXELS

    def get_z_pixels(self):
        return self.graphic.Z_PIXELS

    def get_x_mm(self, pixel):
        pixels = self.x_ref_pixel - float(pixel)
        mm = self.x_ref_mm + pixels * self.x_mm_per_pixel
        # print "get_x_mm( pixel=%s ) returning %f" % (repr(pixel), mm )
        return mm

    def get_z_mm(self, pixel):
        pixels = self.z_ref_pixel - float(pixel)
        mm = self.z_ref_mm + pixels * self.z_mm_per_pixel
        # print "get_z_mm( pixel=%s ) returning %f" % (repr(pixel), mm )
        return mm

    def get_x_pixel(self, mm):
        mm_diff = self.x_ref_mm - float(mm)
        pixels = mm_diff / self.x_mm_per_pixel
        return int(self.x_ref_pixel + pixels)

    def get_z_pixel(self, mm):
        mm_diff = self.z_ref_mm - float(mm)
        pixels = mm_diff / self.z_mm_per_pixel
        return int(self.z_ref_pixel + pixels)

    def get_x_mm_min(self):
        return self.get_x_mm(self.get_x_pixel_max())

    def get_x_mm_max(self):
        return self.get_x_mm(0)

    def get_z_mm_min(self):
        return self.get_z_mm(self.get_z_pixel_max())

    def get_z_mm_max(self):
        return self.get_z_mm(0)

    def get_z_pixel_max(self):
        return self.graphic.Z_PIXELS - 1

    def get_x_pixel_max(self):
        return self.graphic.X_PIXELS - 1

    def get_z_pixel_min(self):
        return 0

    def get_x_pixel_min(self):
        return 0
