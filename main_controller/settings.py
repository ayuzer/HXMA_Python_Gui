
IMPORT_DIRS = [
    "windows",
    "utils",
    "/home/epics/src/R3.14.9-SL-5/base/lib/linux-x86_64",
    "utils/spec_tools"
]

APP_NAME                    = 'Pressure to Diffract |HexMotor HPC Control using SPEC|'

ENABLE_ERROR_DECORATOR      = False
PROMPT_ON_QUIT              = False
USE_SIMULATED_PVS           = True

SETTINGS_FILE_NAME = ".Press2Diff/settings.json"
SETTINGS_POP_FILE_NAME = ".Press2Diff/settings_pop.json"

class KEY(object):
    COMMAND         = 'cmd'
    KEY             = 'key'
    PV              = 'pv'
    FORMAT          = 'format'
    TEXT            = 'text'
    FONT            = 'font'
    FONT_SIZE       = 'font-size'
    HEIGHT          = 'height'
    WIDTH           = 'width'
    ALIGN           = 'align'
    COLOR           = 'color'
    ITEM            = 'item'
    LINE_WIDTH      = 'line_width'
    LINE_STYLE      = 'line_style'
    QT_LAYER        = 'z_value'



