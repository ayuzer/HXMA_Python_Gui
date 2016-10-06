from core import VAR

from json import JSONEncoder
class MyEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

ERROR_MESSAGES = []

class MOT_KEY(object):
    MOT = '__motors__'
    MOTOR_NAMES = 'motor_name'
    MOTOR_MNES = 'motor_mne'
    MOTOR_ENABLED = 'motor_enabled'

class MotMixin(object):
    """
    This is a mixin which will allow saving and loading of motor props from the main window to a .json file
    """

    def set_motors(self):
        key = self.__class__.__name__

        try:
            motor_settings = self.settings.get(key)
            mot_dict = motor_settings.get(MOT_KEY.MOT)

            print "SETTING MOTOR %s TO %s" % (key, mot_dict)

            mot_props = [mot_dict[MOT_KEY.MOTOR_NAMES], mot_dict[MOT_KEY.MOTOR_MNES], mot_dict[MOT_KEY.MOTOR_ENABLED]]
            return mot_props
        except:
            return False
        
    def save_motors(self, Motors):

        key = self.__class__.__name__
        motor_names=[]
        motor_mne = []
        motor_enabled = []
        for Motor in Motors:
            motor_names.append(str(Motor.Name))
            motor_mne.append(Motor.Mne)
            motor_enabled.append(Motor.Enabled)

        mot_dict = {
            MOT_KEY.MOTOR_NAMES: motor_names,
            MOT_KEY.MOTOR_MNES: motor_mne,
            MOT_KEY.MOTOR_ENABLED: motor_enabled,
        }

        print "SAVING MOTOR %s TO %s" % (key, mot_dict)

        motor_settings = self.settings.get(key, {})
        motor_settings[MOT_KEY.MOT] = mot_dict
        self.settings[key] = motor_settings

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
        
        
class ROCK_KEY(object):
    ROCK = '__rock_props__'
    SAVEDIR = 'save_dir'
    SAVENAME = 'save_name'
    X_INDEX = 'x_index'
    Y_INDEX = 'y_index'
    STARTPOS = 'start_pos'
    STOPPOS = 'stop_pos'
    STEPS = 'steps'
    WAITTIME = 'wait_time'
    CURRMOTOR = 'curr_motor'
    TOTTIME = 'total_time'


class RockMixin(object):
    """
    This is a mixin which will allow saving and loading of rockning props from the main window to a .json file
    """

    def set_rock_props(self):
        key = self.__class__.__name__

        try:
            rock_settings = self.settings.get(key)
            rock_dict = rock_settings.get(ROCK_KEY.ROCK)

            print "SETTING ROCK PROPERTY %s TO %s" % (key, rock_dict)

            self.doubleSpinBox_rock_startpos.setValue(rock_dict[ROCK_KEY.STARTPOS])
            self.doubleSpinBox_rock_stoppos.setValue(rock_dict[ROCK_KEY.STOPPOS])
            self.doubleSpinBox_rock_steps.setValue(rock_dict[ROCK_KEY.STEPS])
            self.doubleSpinBox_rock_waittime.setValue(rock_dict[ROCK_KEY.WAITTIME])
            self.comboBox_rock_data_x.setCurrentIndex(rock_dict[ROCK_KEY.X_INDEX])
            self.comboBox_rock_data_y.setCurrentIndex(rock_dict[ROCK_KEY.Y_INDEX])
            self.lineEdit_rock_select_file.setText(rock_dict[ROCK_KEY.SAVEDIR])
            self.lineEdit_rock_filename.setText(rock_dict[ROCK_KEY.SAVENAME])
            self.comboBox_rock_motor.setCurrentIndex(rock_dict[ROCK_KEY.CURRMOTOR])
            self.doubleSpinBox_rock_time.setValue(rock_dict[ROCK_KEY.TOTTIME])

            return True
        except:
            return False

    def save_rock_props(self):

        key = self.__class__.__name__

        rock_dict = {
            ROCK_KEY.STARTPOS:  self.doubleSpinBox_rock_startpos.value(),
            ROCK_KEY.STOPPOS:   self.doubleSpinBox_rock_stoppos.value(),
            ROCK_KEY.STEPS:     self.doubleSpinBox_rock_steps.value(),
            ROCK_KEY.WAITTIME:  self.doubleSpinBox_rock_waittime.value(),
            ROCK_KEY.X_INDEX:   self.comboBox_rock_data_x.currentIndex(),
            ROCK_KEY.Y_INDEX:   self.comboBox_rock_data_y.currentIndex(),
            ROCK_KEY.SAVEDIR:   str(self.lineEdit_rock_select_file.text()),
            ROCK_KEY.SAVENAME:  str(self.lineEdit_rock_filename.text()),
            ROCK_KEY.CURRMOTOR: self.comboBox_rock_motor.currentIndex(),
            ROCK_KEY.TOTTIME: self.doubleSpinBox_rock_time.value(),
        }

        print "SETTING ROCK PROPERTY %s TO %s" % (key, rock_dict)

        rock_settings = self.settings.get(key, {})
        rock_settings[ROCK_KEY.ROCK] = rock_dict
        self.settings[key] = rock_settings


class POS_KEY(object):
    POS = '__pos_props__'
    SAVEDIR = 'save_dir'
    SAVENAME = 'save_name'
    SAVED_POS = 'saved_pos'

class PosMixin(object):
    """
    This is a mixin which will allow saving and loading of posning props from the main window to a .json file
    """

    def set_pos_props(self):
        key = self.__class__.__name__

        try:
            pos_settings = self.settings.get(key)
            pos_dict = pos_settings.get(POS_KEY.POS)

            print "SETTING POS PROPERTY %s TO %s" % (key, pos_dict)

            self.lineEdit_filedir.setText(pos_dict[POS_KEY.SAVEDIR])
            self.lineEdit_filename.setText(pos_dict[POS_KEY.SAVENAME])
            self.saved_pos = pos_dict[POS_KEY.SAVED_POS]

            return True
        except:
            return False

    def save_pos_props(self):

        key = self.__class__.__name__

        pos_dict = {
            POS_KEY.SAVEDIR:   str(self.lineEdit_filedir.text()),
            POS_KEY.SAVENAME:  str(self.lineEdit_filename.text()),
            POS_KEY.SAVED_POS: self.saved_pos,

        }

        print "SETTING POS PROPERTY %s TO %s" % (key, pos_dict)

        pos_settings = self.settings.get(key, {})
        pos_settings[POS_KEY.POS] = pos_dict
        self.settings[key] = pos_settings


