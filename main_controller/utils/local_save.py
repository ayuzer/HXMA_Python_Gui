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


class CENT_KEY(object):
    CENT = '__cent_props__'
    SAVEDIR = 'save_dir'
    SAVENAME = 'save_name'
    X_INDEX = 'x_index'
    Y_INDEX = 'y_index'
    OMEGA_DEL = 'omega_del'
    OMEGA_NAU = 'omega_nau'
    RELMAX = 'relmax'
    RELMIN = 'relmin'
    CENTER = 'center'
    STEPS = 'steps'
    WAITTIME = 'wait_time'
    SCANMOTOR = 'scan_motor'
    ANGLEMOTOR = 'angle_motor'


class CentMixin(object):
    """
    This is a mixin which will allow saving and loading of scanning props from the main window to a .json file
    """

    def set_cent_props(self):
        key = self.__class__.__name__

        try:
            cent_settings = self.settings.get(key)
            cent_dict = cent_settings.get(CENT_KEY.CENT)

            print "SETTING SCAN PROPERTY %s TO %s" % (key, cent_dict)

            self.doubleSpinBox_cent_relmax.setValue(cent_dict[CENT_KEY.RELMAX])
            self.doubleSpinBox_cent_relmin.setValue(cent_dict[CENT_KEY.RELMIN])
            self.doubleSpinBox_cent_center.setValue(cent_dict[CENT_KEY.CENTER])
            self.doubleSpinBox_cent_angle_pm.setValue(cent_dict[CENT_KEY.OMEGA_DEL])
            self.doubleSpinBox_cent_angle_o.setValue(cent_dict[CENT_KEY.OMEGA_NAU])
            self.doubleSpinBox_cent_steps.setValue(cent_dict[CENT_KEY.STEPS])
            self.doubleSpinBox_cent_waittime.setValue(cent_dict[CENT_KEY.WAITTIME])
            self.comboBox_cent_data_x.setCurrentIndex(cent_dict[CENT_KEY.X_INDEX])
            self.comboBox_cent_data_y.setCurrentIndex(cent_dict[CENT_KEY.Y_INDEX])
            self.lineEdit_cent_select_file.setText(cent_dict[CENT_KEY.SAVEDIR])
            self.lineEdit_cent_filename.setText(cent_dict[CENT_KEY.SAVENAME])
            self.comboBox_cent_motor_scan.setCurrentIndex(cent_dict[CENT_KEY.SCANMOTOR])
            self.comboBox_cent_motor_angle.setCurrentIndex(cent_dict[CENT_KEY.ANGLEMOTOR])

            return True
        except:
            return False

    def save_cent_props(self):

        key = self.__class__.__name__

        cent_dict = {
            CENT_KEY.RELMAX: self.doubleSpinBox_cent_relmax.value(),
            CENT_KEY.RELMIN: self.doubleSpinBox_cent_relmin.value(),
            CENT_KEY.CENTER: self.doubleSpinBox_cent_center.value(),
            CENT_KEY.OMEGA_DEL: self.doubleSpinBox_cent_angle_pm.value(),
            CENT_KEY.OMEGA_NAU: self.doubleSpinBox_cent_angle_o.value(),
            CENT_KEY.STEPS: self.doubleSpinBox_cent_steps.value(),
            CENT_KEY.WAITTIME: self.doubleSpinBox_cent_waittime.value(),
            CENT_KEY.X_INDEX: self.comboBox_cent_data_x.currentIndex(),
            CENT_KEY.Y_INDEX: self.comboBox_cent_data_y.currentIndex(),
            CENT_KEY.SAVEDIR: str(self.lineEdit_cent_select_file.text()),
            CENT_KEY.SAVENAME: str(self.lineEdit_cent_filename.text()),
            CENT_KEY.SCANMOTOR: self.comboBox_cent_motor_scan.currentIndex(),
            CENT_KEY.ANGLEMOTOR: self.comboBox_cent_motor_angle.currentIndex(),
        }

        print "SETTING CENT PROPERTY %s TO %s" % (key, cent_dict)

        cent_settings = self.settings.get(key, {})
        cent_settings[CENT_KEY.CENT] = cent_dict
        self.settings[key] = cent_settings
