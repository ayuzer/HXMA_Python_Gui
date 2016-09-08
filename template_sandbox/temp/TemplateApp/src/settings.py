
IMPORT_DIRS = [
    "windows",
    "utils",
    "/home/epics/src/R3.14.9-SL-5/base/lib/linux-x86_64"
]

APP_NAME                    = 'TemplateApp'

ENABLE_ERROR_DECORATOR      = False
PROMPT_ON_QUIT              = False
USE_SIMULATED_PVS           = True

SETTINGS_FILE_NAME = ".TemplateApp/settings.json"

class KEY(object):
    X_MM_START      = 'x_start'
    X_MM_STOP       = 'x_stop'
    Z_MM_START      = 'z_start'
    Z_MM_STOP       = 'z_stop'
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



