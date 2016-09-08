from PyQt4 import QtCore, QtGui

class DragTextMixin(object):

    def drag_text_mixin_initialize(self):

        self._mouse_map_press = {}
        self._text_map = {}

        self._select_font = QtGui.QFont('Courier', 12)
        self._select_font.setWeight(QtGui.QFont.Light)
        self._select_style_sheet = "QLabel { background-color : white; color : black; }"
        self._clipboard = None

    def set_clipboard(self, clipboard):
        self._clipboard = clipboard

    def get_clipboard(self):
        return self._clipboard

    def set_drag_text(self, widget, text):

        if self._mouse_map_press.has_key(widget):
            raise ValueError("set_drag_text() already called for %s (%s)" % \
                             (repr(widget), text))

        self._mouse_map_press[widget] = widget.mousePressEvent
        self._text_map[widget] = QtCore.QString(text)

        widget.setAcceptDrops(False)

        widget.mousePressEvent = \
            lambda arg, widget=widget : self._handle_mouse_press(arg, widget)

    def _handle_mouse_press(self, event, widget):
        """
        Pops up specified text using "drag" mechanism, and puts
        text into the clipboard
        """

        # print "GOT MOUSE CLICK FOR ", repr(widget)

        if event.button() != QtCore.Qt.MiddleButton:
            old_func = self._mouse_map_press.get(widget)
            return old_func(event)

        self._show_drag_text(widget)

    def _show_drag_text(self, widget):

        text = self._text_map.get(widget)

        # Put the text into the clipboard
        self._clipboard.clear()
        self._clipboard.setText(text, mode=QtGui.QClipboard.Selection)

        # Create a label for the "drag" display
        label = QtGui.QLabel()
        label.setStyleSheet(self._select_style_sheet)
        label.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Ignored)
        label.setFont(self._select_font)
        label.setText(text)

        # Must use this invocation to get boundingRect to interpret newlines
        rect = label.fontMetrics().boundingRect(0, 0, 1000, 1000, 0, text)

        # Create pixmap and render label onto it
        pixmap = QtGui.QPixmap(rect.width(), rect.height())
        label.render(pixmap)

        drag = QtGui.QDrag(self)
        drag.setPixmap(pixmap)

        # Does not seem to work without mimeData
        mime_data = QtCore.QMimeData()
        drag.setMimeData(mime_data)

        # Start the drag
        drag.exec_(QtCore.Qt.CopyAction|QtCore.Qt.MoveAction,
            QtCore.Qt.CopyAction)



