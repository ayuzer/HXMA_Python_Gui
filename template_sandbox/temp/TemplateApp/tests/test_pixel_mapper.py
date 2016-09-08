import unittest2
import settings

from pixel_mapper import PixelMapper

class TestPixelMapper(unittest2.TestCase):

    def setUp(self):
        print "setup called"
        self.mapper = PixelMapper(settings.GRAPHIC)

    def test_get_x_pixels(self):

        pixels = self.mapper.get_x_pixels()
        print "x_pixels", pixels
        self.assertEqual(settings.GRAPHIC.X_PIXELS, pixels)

    def test_get_z_pixels(self):

        pixels = self.mapper.get_z_pixels()
        print "z_pixels", pixels
        self.assertEqual(settings.GRAPHIC.Z_PIXELS, pixels)




