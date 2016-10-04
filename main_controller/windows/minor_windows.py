# Library imports
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

from functools import partial

from core import VAR
from core import Core

from SpecClient.Spec import Spec

from windows.css import CSS_COLOUR

from windows.drag_text_mixin import DragTextMixin

from utils.gui import UiMixin

import settings

class LoadPositions(QtGui.QWidget, DragTextMixin, UiMixin):

    def __init__(self, *args, **kwargs):

        self.monitor = kwargs['monitor']
        del kwargs['monitor']

        center_point = kwargs['center']
        del kwargs['center']

        Motors =  kwargs['motors']
        del kwargs['motors']


        super(LoadPositions, self).__init__(*args, **kwargs)

        self.load_ui("windows/load_positions.ui")

        self.setWindowTitle(settings.APP_NAME)

        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        self.drag_text_mixin_initialize()

        self.core = Core(monitor=self.monitor)

        #self.monitor.start()

        label_list = [self.label_mne1_name,
                      self.label_mne2_name,
                      self.label_mne3_name,
                      self.label_mne4_name,
                      self.label_mne5_name,
                      self.label_mne6_name,
                      ]
        for i in range(len(label_list)):
            Motor_inst = Motors[i]
            if Motor_inst.Enabled:
                label_list[i].setText(Motor_inst.Name)
            else:
                label_list[i].setText('N/A')

        self.comboBox_load_1.activated.connect(partial(self.handle_load_motor, 1, self.comboBox_load_1))
        self.comboBox_load_2.activated.connect(partial(self.handle_load_motor, 2, self.comboBox_load_2))
        self.comboBox_load_3.activated.connect(partial(self.handle_load_motor, 3, self.comboBox_load_3))

        self.pushButton_move1.clicked.connect(partial(self.handle_move, '1'))
        self.pushButton_move2.clicked.connect(partial(self.handle_move, '2'))
        self.pushButton_move3.clicked.connect(partial(self.handle_move, '3'))

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
        
    def handle_load_motor(self, slot, CB):
        pos_list = self.pos_label_list[slot-1]
        # You would the take the current text, compare against array and print in appropriate values
        print CB.currentText()

    def handle_move(self, slot):
        goto_list = self.pos_label_list[slot - 1]
        for i in range(len(self.Motors)):
            Motor_inst = self.Motors[i]
            if Motor_inst.Enabled:
                self.core.move_motor(Motor_inst, moveto=float(goto_list[i].text))
        print "Move Commands have been sent"

    def set_close_callback(self, callback):
        self._close_callback = callback
    
    def pos_track(self):
        curr_pos=[
            self.label_currpos_mne1,
            self.label_currpos_mne2,
            self.label_currpos_mne3,
            self.label_currpos_mne4,
            self.label_currpos_mne5,
            self.label_currpos_mne6,
            ]

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