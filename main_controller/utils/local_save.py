from core import VAR

from json import JSONEncoder
class MyEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

ERROR_MESSAGES = []

class SERV_KEY(object):
    SERV = '__server_address__'
    HOST = 'host'
    PORT = 'port'


class ServMixin(object):
    """
    This is a mixin which will allow saving and loading of server props from the main window to a .json file
    """

    def set_server_address(self):
        key = self.__class__.__name__

        try:
            server_settings = self.settings.get(key)
            serv_dict = server_settings.get(SERV_KEY.SERV)

            print "SETTING SERVER ADDRESS %s TO %s" % (key, serv_dict)

            self.monitor.update(VAR.SERVER_HOST, serv_dict[SERV_KEY.HOST])
            self.monitor.update(VAR.SERVER_PORT, serv_dict[SERV_KEY.PORT])
            self.monitor.update(VAR.SERVER_ADDRESS, ''.join((serv_dict[SERV_KEY.HOST], ':', serv_dict[SERV_KEY.PORT])))
            return True
        except:
            return False

    def save_server_address(self):

        key = self.__class__.__name__

        serv_dict = {
            SERV_KEY.HOST: self.monitor.get_value(VAR.SERVER_HOST),
            SERV_KEY.PORT: self.monitor.get_value(VAR.SERVER_PORT),
        }

        print "SAVING SERVER ADDRESS %s TO %s" % (key, serv_dict)

        server_settings = self.settings.get(key, {})
        server_settings[SERV_KEY.SERV] = serv_dict
        self.settings[key] = server_settings

class SCAN_KEY(object):
    SCAN = '__scan_props__'
    SAVEDIR = 'save_dir'
    SAVENAME = 'save_name'
    X_INDEX = 'x_index'
    Y_INDEX = 'y_index'
    STARTPOS = 'start_pos'
    STOPPOS = 'stop_pos'
    STEPS = 'steps'
    WAITTIME = 'wait_time'
    CURRMOTOR = 'curr_motor'

class ScanMixin(object):
    """
    This is a mixin which will allow saving and loading of scanning props from the main window to a .json file
    """

    def set_scan_props(self):
        key = self.__class__.__name__

        try:
            scan_settings = self.settings.get(key)
            scan_dict = scan_settings.get(SCAN_KEY.SCAN)

            print "SETTING SCAN PROPERTY %s TO %s" % (key, scan_dict)

            self.doubleSpinBox_scan_startpos.setValue(scan_dict[SCAN_KEY.STARTPOS])
            self.doubleSpinBox_scan_stoppos.setValue(scan_dict[SCAN_KEY.STOPPOS])
            self.doubleSpinBox_scan_steps.setValue(scan_dict[SCAN_KEY.STEPS])
            self.doubleSpinBox_scan_waittime.setValue(scan_dict[SCAN_KEY.WAITTIME])
            self.comboBox_scan_data_x.setCurrentIndex(scan_dict[SCAN_KEY.X_INDEX])
            self.comboBox_scan_data_y.setCurrentIndex(scan_dict[SCAN_KEY.Y_INDEX])
            self.lineEdit_scan_select_file.setText(scan_dict[SCAN_KEY.SAVEDIR])
            self.lineEdit_scan_filename.setText(scan_dict[SCAN_KEY.SAVENAME])
            self.comboBox_scan_motor.setCurrentIndex(scan_dict[SCAN_KEY.CURRMOTOR])

            return True
        except:
            return False

    def save_scan_props(self):

        key = self.__class__.__name__

        scan_dict = {
            SCAN_KEY.STARTPOS:  self.doubleSpinBox_scan_startpos.value(),
            SCAN_KEY.STOPPOS:   self.doubleSpinBox_scan_stoppos.value(),
            SCAN_KEY.STEPS:     self.doubleSpinBox_scan_steps.value(),
            SCAN_KEY.WAITTIME:  self.doubleSpinBox_scan_waittime.value(),
            SCAN_KEY.X_INDEX:   self.comboBox_scan_data_x.currentIndex(),
            SCAN_KEY.Y_INDEX:   self.comboBox_scan_data_y.currentIndex(),
            SCAN_KEY.SAVEDIR:   str(self.lineEdit_scan_select_file.text()),
            SCAN_KEY.SAVENAME:  str(self.lineEdit_scan_filename.text()),
            SCAN_KEY.CURRMOTOR: self.comboBox_scan_motor.currentIndex(),
        }

        print "SETTING SCAN PROPERTY %s TO %s" % (key, scan_dict)

        scan_settings = self.settings.get(key, {})
        scan_settings[SCAN_KEY.SCAN] = scan_dict
        self.settings[key] = scan_settings