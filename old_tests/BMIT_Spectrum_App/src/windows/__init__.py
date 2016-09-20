#------------------------------------------------------------------------------
# GroupBox Style Settings
#
# For some reason, the title font and weight must be specified in the main
# section, NOT the title section


GROUP_BOX_STYLE = \
    "QGroupBox { " \
        "background-color: rgb(231, 231, 231); "\
        "border:1px solid rgb(200, 200, 200); "\
        "border-radius: 3px; "\
        "padding-top: 10 px; "\
        "font-weight: bold; "\
        "font-size: 12px; "\
        "margin-top: 1px; "\
        "padding-top: 17px; "\
        "padding-bottom: 3px; "\
    "}" \
    "QGroupBox::title { "\
        "background-color: transparent; "\
        "subcontrol-position: top left; "\
        "padding: 1px; "\
    "}"
