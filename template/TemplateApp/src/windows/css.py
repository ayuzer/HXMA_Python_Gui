from utils import Constant

class CSS_COLOUR(Constant):

    BLUE        = 'rgb(   0,   0, 224)'
    GREEN       = 'rgb(   0, 170,   0)'
    BLACK       = 'rgb(   0,   0,   0)'
    RED         = 'rgb( 205,   0,   0)'
    GROUP_BOX   = 'rgb( 231, 231, 231)'

CSS_LABEL_BLUE = "QLabel { color: rgb(0, 0, 224); }"

CSS_LABEL_PV_LOST = "QLabel { background-color : black; color : white; }"

CSS_LED = \
   "QLabel { " \
        "background-color: %s; "\
        "border:1px solid rgb(200, 200, 200); "\
        "border-radius: %dpx; "\
    "}"

#------------------------------------------------------------------------------
# GroupBox Style Settings
#
# For some reason, the title font and weight must be specified in the main
# section, NOT the title section

GROUP_BOX_STYLE = \
    "QGroupBox { " \
        "background-color: rgb(231, 231, 231); "\
        "border:1px solid rgb(200, 200, 200); "\
        "border-radius: 5px; "\
        "padding-top: 30 px; "\
        "font-weight: bold; "\
        "font-size: 18px; "\
    "}" \
    "QGroupBox::title { "\
        "background-color: transparent; "\
        "subcontrol-position: top left; "\
        "padding:2 5px; "\
    "}"

GROUP_BOX_STYLE_NO_TITLE = \
    "QGroupBox { " \
        "background-color: rgb(231, 231, 231); "\
        "border:1px solid rgb(200, 200, 200); "\
        "border-radius: 5px; "\
        "padding-top: 5 px; "\
        "font-weight: bold; "\
        "font-size: 18px; "\
    "}" \
    "QGroupBox::title { "\
        "background-color: transparent; "\
        "subcontrol-position: top left; "\
        "padding:2 5px; "\
    "}"
