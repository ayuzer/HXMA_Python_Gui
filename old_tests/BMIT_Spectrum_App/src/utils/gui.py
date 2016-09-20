# System imports
import os

# Library imports
from PyQt4 import uic
from PyQt4 import QtGui
from PyQt4 import Qt

# App imports
from settings import BASE_PATH
from settings import APP_NAME
from settings import ENABLE_ERROR_DECORATOR

ERROR_MESSAGES = []
INFO_MESSAGES = []

class KEY(object):
    RECT    = '__window_rectangle__'
    X       = 'x'
    Y       = 'y'
    WIDTH   = 'w'
    HEIGHT  = 'h'

class UiMixin(object):
    """
    This mixin provides a method that allows the container to load a
    designer (.ui) file with the path pre-computed based on the
    program location
    """

    def load_ui(self, uic_file_name):

        uic_file_name = os.path.join(BASE_PATH, uic_file_name)
        uic.loadUi(uic_file_name, self)

    def get_position(self):

        key = self.__class__.__name__

        try:
            window_settings = self.settings.get(key)
            rect_dict = window_settings.get(KEY.RECT)

            print "SETTING WINDOW %s TO %s" % (key, rect_dict)

            self.setGeometry(
                rect_dict[KEY.X],
                rect_dict[KEY.Y],
                rect_dict[KEY.WIDTH],
                rect_dict[KEY.HEIGHT]
            )

        except Exception, e:
            print "Exception setting window position", str(e)

    def save_position(self):

        key = self.__class__.__name__
        rect = self.geometry()

        rect_dict = {
            KEY.X       : rect.x(),
            KEY.Y       : rect.y(),
            KEY.WIDTH   : rect.width(),
            KEY.HEIGHT  : rect.height(),
        }

        msg = "SAVING WINDOW %s TO %s" % (key, rect_dict)
        print msg

        window_settings = self.settings.get(key, {})
        window_settings[KEY.RECT] = rect_dict
        self.settings[key] = window_settings

def dialog_info(sender = None, title=APP_NAME, msg="message"):

    global INFO_MESSAGES

    if msg in INFO_MESSAGES:
        print "dialog_info() msg already displayed: %d: %s" % \
            (len(INFO_MESSAGES), msg)
        return

    INFO_MESSAGES.append(msg)

    QtGui.QMessageBox.information(sender, title, msg,
        QtGui.QMessageBox.Ok)

    INFO_MESSAGES = [m for m in INFO_MESSAGES if m != msg]

    return True

def dialog_yes_no(sender = None, title=APP_NAME, msg="message"):

    reply = QtGui.QMessageBox.question(sender, title, msg,
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No)

    if reply == QtGui.QMessageBox.Yes:
        return True

    return False

def dialog_error(sender = None, title=APP_NAME, msg="message"):

    global ERROR_MESSAGES

    if msg in ERROR_MESSAGES:
        print "dialog_error() msg already displayed %d: %s:" % \
            (len(ERROR_MESSAGES), msg)

        return

    ERROR_MESSAGES.append(msg)

    QtGui.QMessageBox.critical(sender, title, msg,
        QtGui.QMessageBox.Ok,
        QtGui.QMessageBox.Ok)

    # Remove message from list
    ERROR_MESSAGES = [m for m in ERROR_MESSAGES if m != msg]

def decorator_busy_cursor(func):

    def inner(self, *args, **kwargs):

        cursor = self.cursor()
        # print "cursor:", cursor, "shape:", cursor.shape()

        try:

            # print "decorator ARGS", args
            # print "decorator kwargs", kwargs
            # print "Setting BUSY cursor...", self
            self.setCursor(Qt.Qt.BusyCursor)

            # temp_cursor = self.cursor()
            # print "cursor:", cursor, "shape:", temp_cursor.shape()

            func(self, *args, **kwargs)

        finally:
            self.setCursor(cursor)

    return inner

def decorator_dialog_error(func):

    def inner(*args, **kwargs):

        if ENABLE_ERROR_DECORATOR:
            # print "CALLING WITH ERROR DECORATOR"
            try:
                #if args:
                #    print 'args-->', args
                #if kwargs:
                #    print 'kwargs-->', kwargs

                func(*args, **kwargs)
            except Exception, e:
                msg = "Error: %s" % str(e)
                dialog_error(args[0], msg=msg)
        else:
            # print "%s:  ERROR DECORATOR DISABLED" % func
            func(*args, **kwargs)

    return inner


def format_pv_value(value):

    if isinstance(value, float):
        value = "%.6f" % value
        value = value.strip('0')

        if value.endswith('.'):
            value += '0'

        if value.startswith('.'):
            value = '0' + value

    elif isinstance(value, int):
        value = repr(value)

    return value

