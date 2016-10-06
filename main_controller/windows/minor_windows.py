# Library imports
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

from functools import partial

from core import VAR
from core import Core

from SpecClient.Spec import Spec

from windows.css import CSS_COLOUR
from windows.css import CSS_LABEL_PV_LOST

from windows.drag_text_mixin import DragTextMixin

from utils.gui import UiMixin
from utils.gui import dialog_yes_no
from utils.gui import dialog_error

from utils.local_save import PosMixin

import simplejson
import os
import csv

from PyQt4 import QtGui, QtCore

import settings

class LoadPositions(QtGui.QWidget, DragTextMixin, UiMixin, PosMixin):
    # This works well but it is very jenky
    def __init__(self, *args, **kwargs):

        self.monitor = kwargs['monitor']
        del kwargs['monitor']

        center_point = kwargs['center']
        del kwargs['center']

        self.Motors = kwargs['motors']
        del kwargs['motors']

        self.formatter = kwargs['formatter']
        del kwargs['formatter']

        self.saved_pos = kwargs['saved_pos']
        del kwargs['saved_pos']

        super(LoadPositions, self).__init__(*args, **kwargs)

        self.load_ui("windows/load_positions.ui")

        self.setWindowTitle(settings.APP_NAME)

        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        self.drag_text_mixin_initialize()

        self.init_labels()
        self.load_settings()

        self.monitor.start()

        self.core = Core(monitor=self.monitor)

        self.pushButton_filedir_choose.clicked.connect(partial(self.select_file, self.lineEdit_filedir))
        self.lineEdit_filedir.textChanged.connect(
            partial(self.core.update_filepath, self.lineEdit_filedir, 'pos'))
        self.pushButton_table_save.clicked.connect(self.handle_save_table)
        self.core.update_filepath(self.lineEdit_filedir, 'pos')

        label_list = [self.label_mne1_name,
                      self.label_mne2_name,
                      self.label_mne3_name,
                      self.label_mne4_name,
                      self.label_mne5_name,
                      self.label_mne6_name,
                      ]
        for i in range(len(label_list)):
            Motor_inst = self.Motors[i]
            if Motor_inst.Enabled:
                label_list[i].setText(Motor_inst.Name)
            else:
                label_list[i].setText('N/A')
        self.label_list = label_list

        self.pushButton_table_load.clicked.connect(self.load_table)

        self.pushButton_move1.clicked.connect(partial(self.handle_move, 1))
        self.pushButton_move2.clicked.connect(partial(self.handle_move, 2))
        self.pushButton_move3.clicked.connect(partial(self.handle_move, 3))

        self.pushButton_save_curr.clicked.connect(partial(self.handle_save, 'curr'))
        self.pushButton_save_set.clicked.connect(partial(self.handle_save, 'set'))

        self.pos_label_list = [
            [self.label_pos1_mne1,
             self.label_pos1_mne2,
             self.label_pos1_mne3,
             self.label_pos1_mne4,
             self.label_pos1_mne5,
             self.label_pos1_mne6,
             self.label_comment1,
             ],
            [self.label_pos2_mne1,
             self.label_pos2_mne2,
             self.label_pos2_mne3,
             self.label_pos2_mne4,
             self.label_pos2_mne5,
             self.label_pos2_mne6,
             self.label_comment2,
             ],
            [self.label_pos3_mne1,
             self.label_pos3_mne2,
             self.label_pos3_mne3,
             self.label_pos3_mne4,
             self.label_pos3_mne5,
             self.label_pos3_mne6,
             self.label_comment3,
             ]
        ]

        self.set_pos_props()

        self.update_table()

        self.update_CB()

        self.label_list_spin = [
            self.doubleSpinBox_set_mne1,
            self.doubleSpinBox_set_mne2,
            self.doubleSpinBox_set_mne3,
            self.doubleSpinBox_set_mne4,
            self.doubleSpinBox_set_mne5,
            self.doubleSpinBox_set_mne6,
        ]

    def handle_save_table(self):
        self.core.save_table(str(self.lineEdit_filename.text()),
                             self.tableWidget_positions,
                             self.vhead,
                             self.hhead,
                             )

    def handle_move(self, slot):
        goto_list = self.pos_label_list[slot - 1]
        for i in range(len(self.Motors)):
            Motor_inst = self.Motors[i]
            if Motor_inst.Enabled:
                for title in self.label_list:
                    if str(title.text()) is not "N/A":
                        self.core.move_motor(Motor_inst, moveto=float(goto_list[i].text()), movetype='Absolute')
        print "Move Commands have been sent"

    def update_load(self, labels, CB):
        name = str(CB.currentText())
        for pos_name, data, comment in self.saved_pos:
            if name == pos_name:
                labels[-1].setText(comment)
                for mot_name, info in data:
                    for label in self.label_list:
                        if mot_name == str(label.text()):
                            labels[self.label_list.index(label)].setText(str(info))

    def handle_save(self, type):
        i = 0
        if type == 'curr':
            iter = self.pos_track()
            label = str(self.lineEdit_name_curr.text())
            comment = str(self.lineEdit_comment_curr.text())
        elif type == 'set':
            iter = self.label_list_spin
            label =  str(self.lineEdit_name_set.text())
            comment = str(self.lineEdit_comment_set.text())
        save = [label]
        data = []
        for item in iter:
            name = str(self.label_list[i].text())
            if not name == 'N/A':
                if type == 'curr':
                    pos = float(item.text())
                elif type == 'set':
                    pos = item.value()
                data.append([name, pos])
            i = i + 1
        save.append(data)
        save.append(comment)
        print "Saving entry : " +  repr(save)
        self.saved_pos.append(save)
        self._update_callback(self.saved_pos)
        self.update_table()

    def load_table(self):  # opens the csv file and saves it in the format we're using for saving positions
        path = QtGui.QFileDialog.getOpenFileName(
            self, 'Open File', '', 'CSV(*.csv)')
        if not path.isEmpty():
            self.saved_pos = []
            with open(unicode(path), 'rb') as stream:
                for row, rowdata in enumerate(csv.reader(stream)):
                    if row == 0:
                        motors = rowdata
                        continue
                    data = ['', []]
                    for column, coldata in enumerate(rowdata):
                        if column == 0:
                            data[0] = coldata
                        elif motors[column] == "Comment":
                            data.append(coldata)
                            break
                        try:
                            data[1].append([motors[column], float(coldata)])
                        except ValueError:
                            pass
                    self.saved_pos.append(data)
            self.update_table()

    def update_CB(self):
        mix_list = []
        CBs = [ self.comboBox_load_1, self.comboBox_load_2, self.comboBox_load_3]
        for i in range(len(self.pos_label_list)):
            mix_list.append([CBs[i], self.pos_label_list[i]])

        for CB, labels in mix_list:
            CB.currentIndexChanged.connect(partial(self.update_load, labels, CB))

    def update_table(self):
        table = self.tableWidget_positions
        names = []
        motors = []
        table.clear()
        row_count = 0
        for i in range(len(motors)):
            table.insertColumn(i)
        for o, p, q in self.saved_pos:
            for l, m in p:
                if l not in motors:
                    motors.append(l)
        for name, data, comment in self.saved_pos:
            if row_count == table.rowCount():
                table.insertRow(row_count)
            names.append(name)
            row = [None]*len(motors)
            for motor, pos in data:
                if motor in motors:
                    row[motors.index(motor)] = pos  # if we already have an entry we insert into that column
                else:
                    motors.append(motor)
                    table.insertColumn(len(motors))
                    row.append(pos)
            row.append(comment)
            if table.columnCount() < len(row):
                for j in range(table.columnCount(), len(row)):
                    table.insertColumn(j)
            for i in range(len(row)):
                if row[i] == None:
                    entry = "None"
                else:
                    entry = str(row[i])
                table.setItem(row_count, i, QtGui.QTableWidgetItem(entry))
            row_count = row_count + 1
        table.setVerticalHeaderLabels(names)
        self.hhead = names
        motors.append("Comment")
        table.setHorizontalHeaderLabels(motors)
        self.vhead = list(motors)
        motors.pop()
        for CB in [self.comboBox_load_1, self.comboBox_load_2, self.comboBox_load_3]:
            i = CB.currentIndex()
            CB.clear()
            for name in names:
                CB.addItem(name)
            CB.setCurrentIndex(i)

    def update_callback(self, callback):
        self._update_callback = callback

    def set_close_callback(self, callback):
        self._close_callback = callback

    def closeEvent(self, event):

        print "Popup.closeEvent() called"

        if not dialog_yes_no(sender=self, msg='Confirm Close?', title="Setup"):
            event.ignore()
            return

        self.monitor.disconnect(self)

        self.save_pos_props()

        self.save_settings()

        if self._close_callback:
            self._close_callback(self)

        super(LoadPositions, self).closeEvent(event)

    def pos_track(self):
        curr_pos=[
            self.label_currpos_mne1,
            self.label_currpos_mne2,
            self.label_currpos_mne3,
            self.label_currpos_mne4,
            self.label_currpos_mne5,
            self.label_currpos_mne6,
            ]
        return curr_pos

    def init_labels(self):
        css_normal = "QLabel { background-color : %s; color : %s; }" % \
                     (CSS_COLOUR.GROUP_BOX, CSS_COLOUR.BLUE)
        label_map = {
            VAR.MOTOR_1_POS:        (self.label_currpos_mne1, '{:,.3f}', 12, True),
            VAR.MOTOR_2_POS:        (self.label_currpos_mne2, '{:,.3f}', 12, True),
            VAR.MOTOR_3_POS:        (self.label_currpos_mne3, '{:,.3f}', 12, True),
            VAR.MOTOR_4_POS:        (self.label_currpos_mne4, '{:,.3f}', 12, True),
            VAR.MOTOR_5_POS:        (self.label_currpos_mne5, '{:,.3f}', 12, True),
            VAR.MOTOR_6_POS:        (self.label_currpos_mne6, '{:,.3f}', 12, True),
        }
        for pv_name, data in label_map.iteritems():
            # self.monitor.add(pv_name)

            widget = data[0]
            font = QtGui.QFont('Courier', data[2])
            widget.setFont(font)
            widget.setText(QtCore.QString(''))

            self.set_drag_text(widget, pv_name)

            try:
                if data[3]:
                    font.setWeight(QtGui.QFont.Bold)
            except:
                pass

            self.formatter.add(pv_name, widget, format=data[1],
                               css_normal=css_normal,
                               css_lost=CSS_LABEL_PV_LOST)

            self.monitor.connect(pv_name, self.handle_label)

    def handle_label(self, pv_name):
        self.formatter.format(pv_name)

    def select_file(self, line_edit):
        line_edit.setText(QtGui.QFileDialog.getExistingDirectory(None, 'Select a folder to save data :', os.getcwd(), QtGui.QFileDialog.ShowDirsOnly))

    def load_settings(self):
        f = None

        try:
            home = os.path.expanduser("~")
            filename = os.path.join(home, settings.SETTINGS_POP_FILE_NAME)
            f = open(filename, 'r')

            print "Loading settings from '%s'" % filename

            self.settings = simplejson.load(f)

            print "These are the settings loaded:"
            print self.settings

        except Exception, e:
            print "Error loading settings file %s: %s" % (filename, str(e))
            self.settings = {}

        finally:
            try:
                if f:
                    f.close()
            except Exception, e:
                print "Error closing settings file %s: %s" % (filename, str(e))

    def save_settings(self):
        f = None

        try:

            home = os.path.expanduser("~")
            filename = os.path.join(home, settings.SETTINGS_POP_FILE_NAME)
            directory = os.path.dirname(os.path.realpath(filename))

            print "saving settings to settings file '%s'" % filename

            if not os.path.exists(directory):
                os.makedirs(directory)

            f = open(filename, 'w+')
            simplejson.dump(self.settings, f, indent=4, sort_keys=True)

        except Exception, e:
            print "Error saving user settings file %s: %s" % (filename, str(e))

        finally:
            if f:
                f.close()

class SetMotorSlot(QtGui.QWidget, DragTextMixin, UiMixin):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs['monitor']
        del kwargs['monitor']

        center_point = kwargs['center']
        del kwargs['center']

        self.Motors =  kwargs['motors']
        del kwargs['motors']

        super(SetMotorSlot, self).__init__(*args, **kwargs)

        self.load_ui("windows/motor_slotting.ui")

        self.setWindowTitle(settings.APP_NAME)

        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        self.drag_text_mixin_initialize()

        self.core = Core(monitor=self.monitor)

        self.drag_text_mixin_initialize()

        self.comboboxes=[
            self.comboBox_motor_slot_1,
            self.comboBox_motor_slot_2,
            self.comboBox_motor_slot_3,
            self.comboBox_motor_slot_4,
            self.comboBox_motor_slot_5,
            self.comboBox_motor_slot_6,
        ]
        self.checkboxes = [
            self.checkBox_motor_slot_1,
            self.checkBox_motor_slot_2,
            self.checkBox_motor_slot_3,
            self.checkBox_motor_slot_4,
            self.checkBox_motor_slot_5,
            self.checkBox_motor_slot_6,
        ]

        self.fill_CB(self.comboboxes)

        self.pushButton_apply.clicked.connect(self.handle_pushButton_apply)

        for i in range(len(self.comboboxes)):
            self.comboboxes[i].currentIndexChanged.connect(partial(self.handle_CB_ref, i+1))

    def set_close_callback(self, callback):
        self._close_callback = callback

    def fill_CB(self, CBs):
        self.core.Spec_sess.connectToSpec(self.monitor.get_value(VAR.SERVER_ADDRESS))
        motor_names = Spec.getMotorsNames(self.core.Spec_sess)
        motor_mnes = Spec.getMotorsMne(self.core.Spec_sess)
        self.motor_props=[motor_names,motor_mnes]
        for combo in CBs:
            combo.clear()
            for i in range(len(self.motor_props[0])):
                combo.addItem(self.motor_props[0][i])

    def handle_CB_ref(self, num):
        print num

    def handle_pushButton_apply(self): # Setting the chosen name to be a motor
        for i in range(len(self.Motors)):
            name = self.comboboxes[i].currentText()
            for j in range(len(self.motor_props[0])):
                if self.motor_props[0][j] == name:
                    mne = self.motor_props[1][j]
                    break
            self.Motors[i]=self.Motors[i]._replace(Name=name,
                                                   Mne=mne,
                                                   Enabled=self.checkboxes[i].isChecked()
                                                   )
        self._apply_callback(self.Motors)
        self.close()

    def apply_callback(self, callback):
        self._apply_callback = callback

    def handle_pushButton_cancel(self):
        self.close()

class SetServer(QtGui.QWidget, DragTextMixin, UiMixin):
    def __init__(self, *args, **kwargs):

        self.monitor = kwargs['monitor']
        del kwargs['monitor']

        center_point = kwargs['center']
        del kwargs['center']

        self.host = kwargs['host']
        del kwargs['host']

        self.port= kwargs['port']
        del kwargs['port']

        super(SetServer, self).__init__(*args, **kwargs)

        self.load_ui("windows/set_server.ui")

        self.setWindowTitle(settings.APP_NAME)

        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        self.drag_text_mixin_initialize()

        self.pushButton_apply.clicked.connect(self.handle_pushButton_apply)

        self.lineEdit_host.setText(self.host)
        self.lineEdit_port.setText(self.port)

    def handle_pushButton_apply(self):
        self._apply_callback(str(self.lineEdit_host.text()), str(self.lineEdit_port.text()))
        self.close()

    def apply_callback(self, callback):
        self._apply_callback = callback

    def handle_pushButton_cancel(self):
        self.close()

    def set_close_callback(self, callback):
        self._close_callback = callback