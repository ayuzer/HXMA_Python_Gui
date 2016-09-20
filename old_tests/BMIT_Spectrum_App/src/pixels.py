
from PIL import Image
import binascii


def start():

    intensity = 0

    data = []

    for i in xrange(128):
        for j in xrange(128):

            s = format(intensity, "02x")
            data.extend([s, s, s])

        intensity += 1
        if intensity == 255:
             intensity = 0

    data = ''.join(data)
    data = binascii.unhexlify(data)

    image = Image.frombuffer("RGB", (128, 128), data)
    image.show()

if __name__ == "__main__":
    """
    Program entry point
    """

    start()
