from utils import Constant

from settings import USE_SIMULATED_PVS

# Unfortunately the PV definitions have grown organically over
# time with varying requirements and evolving 'best practices'
# such that there are now multiple methods to switch between
# actual and simulated PVs
if USE_SIMULATED_PVS:
    BASE        = 'breem'
    BASE2       = 'breem'
    BASE3       = 'breem:'
    KES_LATTICE = ''

else:
    BASE        = 'PFIL1605'
    BASE2       = 'BMIT'
    BASE3       = ''
    KES_LATTICE = '.C'

class PV(Constant):
    ID_MONO_IN_CT               = BASE3 + 'CTMono1605-3-I20-01:Z1Z2:inMono'
    ID_MONO_IN_KES              = BASE3 + 'KESvert1605-3-I20-01:StrSel:fbk'
    # ID_MONO_CT1_MTBO            = BASE3 + 'XTAL1605-3-I20-01:MountToBase:offset'
    # ID_MONO_CT2_MTBO            = BASE3 + 'XTAL1605-3-I20-02:MountToBase:offset'
    # ID_MONO_CT1_THETA           = BASE3 + 'SMTR1605-3-I20-10:deg:sp'
    # ID_MONO_CT2_THETA           = BASE3 + 'SMTR1605-3-I20-13:deg:sp'
    ID_MONO_CT1_BRAGG           = BASE3 + 'CTMono1605-3-I20-01:C1:Bragg:curr'
    ID_MONO_CT2_BRAGG           = BASE3 + 'CTMono1605-3-I20-01:C2:Bragg:curr'
    ID_MONO_CT1_LATTICE         = BASE3 + 'XTAL1605-3-I20-01:offset'
    ID_MONO_CT2_LATTICE         = BASE3 + 'XTAL1605-3-I20-02:offset'
    ID_MONO_ENERGY_CT           = BASE3 + 'CTMono1605-3-I20-01:Energy:curr'
    ID_MONO_ENERGY_KES          = BASE3 + 'BL1605-ID2-1:Energy:fbk'
    ID_MONO_KES_TOTAL_OFFSET    = BASE3 + 'KEmono1605-3-I20-01:X:theta_base'
    ID_MONO_KES_LATTICE_ANGLE   = BASE3 + 'BL1605-ID2-1:constants' + KES_LATTICE
    ID_MONO_KES_STAGE_ANGLE     = BASE3 + 'SMTR1605-3-I20-23:dgr:sp'
    ID_MONO_KES_BRAGG_ANGLE     = BASE3 + 'KEmono1605-3-I20-01:bragg:fbk'

class CT_MONO_STATUS(Constant):
    OUT         = 0
    IN          = 1
    UNKNOWN     = 2

class KES_MONO_STATUS(Constant):
    UNKNOWN     = 0
    IN          = 1
    OUT         = 2
    IN_BETWEEN  = 3
    MOVING      = 4

# No need to simulate these PVs at the moment
class RING_PV(Constant):
    CURRENT                     = 'PCT1402-01:mA:fbk'
    ENERGY                      = 'SRStatus:SR:energy'
    WIGGLER_FIELD               = 'WIG1405-01:T:fbk'
    SYSTEM_TIME                 = "WIG1405-01:systemTime"

class BEAMLINE(Constant):
    BM = 'BM'
    ID = 'ID'

class VAR(Constant):
    RING_CURRENT_THEORETICAL    = "var:ring_current_theoretical"
    RING_CURRENT_ACTUAL         = "var:ring_current_actual"
    RING_CURRENT_ACTIVE         = "var:ring_current_active"
    RING_CURRENT_USE_ACTUAL     = "var:ring_current_use_actual"

    WIGGLER_FIELD_THEORETICAL   = "var:wiggler_field_theoretical"
    WIGGLER_FIELD_ACTUAL        = "var:wiggler_field_actual"
    WIGGLER_FIELD_ACTIVE        = "var:wiggler_field_active"
    WIGGLER_FIELD_USE_ACTUAL    = "var:wiggler_field_use_actual"

    OTHER_FILTERS               = 'var:other_filters'
    MASS_ATTEN_THICKNESS        = 'var:mass_atten_thickness'

    BM_PLOT_MOUSE_POS           = 'var:bm_plot_mouse_pos'
    ID_PLOT_MOUSE_POS           = 'var:id_plot_mouse_pos'
    TEST_PLOT_MOUSE_POS         = 'var:test_plot_mouse_pos'
    ATTEN_PLOT_MOUSE_POS        = 'var:atten_plot_mouse_pos'

    PLOT_CUMULATIVE_ID          = 'var:plot_cumulative_id'
    PLOT_CUMULATIVE_BM          = 'var:plot_cumulative_bm'

    WBT_RADIO                   = 'var:wbt_radio'
    WBT_STATUS                  = 'var:wbt_status'
    ID_MONO_ACTUAL              = 'var:id_mono_actual'
    ID_MONO_RADIO               = 'var:id_mono_radio'
    ID_MONO_USE                 = 'var:id_mono_use'
    ID_MONO_CT_THICKNESS_C1     = 'var:id_mono_ct_thickness_c1'
    ID_MONO_CT_THICKNESS_C2     = 'var:id_mono_ct_thickness_c2'
    ID_MONO_KES_THICKNESS       = 'var:id_mono_kes_thickness'
    ID_MONO_ENERGY_CT           = 'var:id_mono_energy_ct'
    ID_MONO_ENERGY_KES          = 'var:id_mono_energy_kes'
    ID_MONO_ENERGY              = 'var:id_mono_energy'

class WBT_STATUS(Constant):
    OUT     = 0
    IN      = 1
    UNKNOWN = 2

class FILTER_BM(Constant):

    P1_1_MAT     = BASE + '-1-B10-01:curr:material'
    P1_1_THK     = BASE + '-1-B10-01:curr:actualThk'
    P1_1_THK_NOM = BASE + '-1-B10-01:curr:thickness'
    P1_1_MAT_1   = BASE + '-1-B10-01:p1:material'
    P1_1_MAT_2   = BASE + '-1-B10-01:p2:material'
    P1_1_MAT_3   = BASE + '-1-B10-01:p3:material'
    P1_1_MAT_4   = BASE + '-1-B10-01:p4:material'
    P1_1_MAT_5   = BASE + '-1-B10-01:p5:material'
    P1_1_THK_1   = BASE + '-1-B10-01:p1:actualThk'
    P1_1_THK_2   = BASE + '-1-B10-01:p2:actualThk'
    P1_1_THK_3   = BASE + '-1-B10-01:p3:actualThk'
    P1_1_THK_4   = BASE + '-1-B10-01:p4:actualThk'
    P1_1_THK_5   = BASE + '-1-B10-01:p5:actualThk'

    P1_2_MAT     = BASE + '-1-B10-02:curr:material'
    P1_2_THK     = BASE + '-1-B10-02:curr:actualThk'
    P1_2_THK_NOM = BASE + '-1-B10-02:curr:thickness'
    P1_2_MAT_1   = BASE + '-1-B10-02:p1:material'
    P1_2_MAT_2   = BASE + '-1-B10-02:p2:material'
    P1_2_MAT_3   = BASE + '-1-B10-02:p3:material'
    P1_2_MAT_4   = BASE + '-1-B10-02:p4:material'
    P1_2_MAT_5   = BASE + '-1-B10-02:p5:material'
    P1_2_THK_1   = BASE + '-1-B10-02:p1:actualThk'
    P1_2_THK_2   = BASE + '-1-B10-02:p2:actualThk'
    P1_2_THK_3   = BASE + '-1-B10-02:p3:actualThk'
    P1_2_THK_4   = BASE + '-1-B10-02:p4:actualThk'
    P1_2_THK_5   = BASE + '-1-B10-02:p5:actualThk'

    P1_3_MAT     = BASE + '-1-B10-03:curr:material'
    P1_3_THK     = BASE + '-1-B10-03:curr:actualThk'
    P1_3_THK_NOM = BASE + '-1-B10-03:curr:thickness'
    P1_3_MAT_1   = BASE + '-1-B10-03:p1:material'
    P1_3_MAT_2   = BASE + '-1-B10-03:p2:material'
    P1_3_MAT_3   = BASE + '-1-B10-03:p3:material'
    P1_3_MAT_4   = BASE + '-1-B10-03:p4:material'
    P1_3_MAT_5   = BASE + '-1-B10-03:p5:material'
    P1_3_THK_1   = BASE + '-1-B10-03:p1:actualThk'
    P1_3_THK_2   = BASE + '-1-B10-03:p2:actualThk'
    P1_3_THK_3   = BASE + '-1-B10-03:p3:actualThk'
    P1_3_THK_4   = BASE + '-1-B10-03:p4:actualThk'
    P1_3_THK_5   = BASE + '-1-B10-03:p5:actualThk'

class FILTER_ID(Constant):

    WBT_ACTUAL   = BASE2 + '-ID:WBT:status'

    P1_1_MAT     = BASE + '-1-I20-01:material'
    P1_1_THK     = BASE + '-1-I20-01:thickness'
    P1_1_OPENED  = BASE + '-1-I20-01:opened'
    P1_1_CLOSED  = BASE + '-1-I20-01:closed'

    P1_2_MAT     = BASE + '-1-I20-02:material'
    P1_2_THK     = BASE + '-1-I20-02:thickness'
    P1_2_OPENED  = BASE + '-1-I20-02:opened'
    P1_2_CLOSED  = BASE + '-1-I20-02:closed'

    P1_3_MAT     = BASE + '-1-I20-03:curr:material'
    P1_3_THK     = BASE + '-1-I20-03:curr:actualThk'
    P1_3_THK_NOM = BASE + '-1-I20-03:curr:thickness'
    P1_3_MAT_1   = BASE + '-1-I20-03:p1:material'
    P1_3_MAT_2   = BASE + '-1-I20-03:p2:material'
    P1_3_MAT_3   = BASE + '-1-I20-03:p3:material'
    P1_3_MAT_4   = BASE + '-1-I20-03:p4:material'
    P1_3_MAT_5   = BASE + '-1-I20-03:p5:material'
    P1_3_THK_1   = BASE + '-1-I20-03:p1:actualThk'
    P1_3_THK_2   = BASE + '-1-I20-03:p2:actualThk'
    P1_3_THK_3   = BASE + '-1-I20-03:p3:actualThk'
    P1_3_THK_4   = BASE + '-1-I20-03:p4:actualThk'
    P1_3_THK_5   = BASE + '-1-I20-03:p5:actualThk'
    P1_4_MAT     = BASE + '-1-I20-04:curr:material'
    P1_4_THK_NOM = BASE + '-1-I20-04:curr:thickness'
    P1_4_THK     = BASE + '-1-I20-04:curr:actualThk'
    P1_4_MAT_1   = BASE + '-1-I20-04:p1:material'
    P1_4_MAT_2   = BASE + '-1-I20-04:p2:material'
    P1_4_MAT_3   = BASE + '-1-I20-04:p3:material'
    P1_4_MAT_4   = BASE + '-1-I20-04:p4:material'
    P1_4_MAT_5   = BASE + '-1-I20-04:p5:material'
    P1_4_THK_1   = BASE + '-1-I20-04:p1:actualThk'
    P1_4_THK_2   = BASE + '-1-I20-04:p2:actualThk'
    P1_4_THK_3   = BASE + '-1-I20-04:p3:actualThk'
    P1_4_THK_4   = BASE + '-1-I20-04:p4:actualThk'
    P1_4_THK_5   = BASE + '-1-I20-04:p5:actualThk'
    P1_5_MAT     = BASE + '-1-I20-05:curr:material'
    P1_5_THK_NOM = BASE + '-1-I20-05:curr:thickness'
    P1_5_THK     = BASE + '-1-I20-05:curr:actualThk'
    P1_5_MAT_1   = BASE + '-1-I20-05:p1:material'
    P1_5_MAT_2   = BASE + '-1-I20-05:p2:material'
    P1_5_MAT_3   = BASE + '-1-I20-05:p3:material'
    P1_5_MAT_4   = BASE + '-1-I20-05:p4:material'
    P1_5_MAT_5   = BASE + '-1-I20-05:p5:material'
    P1_5_THK_1   = BASE + '-1-I20-05:p1:actualThk'
    P1_5_THK_2   = BASE + '-1-I20-05:p2:actualThk'
    P1_5_THK_3   = BASE + '-1-I20-05:p3:actualThk'
    P1_5_THK_4   = BASE + '-1-I20-05:p4:actualThk'
    P1_5_THK_5   = BASE + '-1-I20-05:p5:actualThk'

    P3_1_MAT     = BASE + '-3-I20-01:material'
    P3_1_THK     = BASE + '-3-I20-01:thickness'
    P3_1_OPENED  = BASE + '-3-I20-01:opened'
    P3_1_CLOSED  = BASE + '-3-I20-01:closed'

    P3_2_MAT     = BASE + '-3-I20-02:material'
    P3_2_THK     = BASE + '-3-I20-02:thickness'
    P3_2_OPENED  = BASE + '-3-I20-02:opened'
    P3_2_CLOSED  = BASE + '-3-I20-02:closed'

    P3_3_MAT     = BASE + '-3-I20-03:curr:material'
    P3_3_THK_NOM = BASE + '-3-I20-03:curr:thickness'
    P3_3_THK     = BASE + '-3-I20-03:curr:actualThk'
    P3_3_MAT_1   = BASE + '-3-I20-03:p1:material'
    P3_3_MAT_2   = BASE + '-3-I20-03:p2:material'
    P3_3_MAT_3   = BASE + '-3-I20-03:p3:material'
    P3_3_MAT_4   = BASE + '-3-I20-03:p4:material'
    P3_3_MAT_5   = BASE + '-3-I20-03:p5:material'
    P3_3_THK_1   = BASE + '-3-I20-03:p1:actualThk'
    P3_3_THK_2   = BASE + '-3-I20-03:p2:actualThk'
    P3_3_THK_3   = BASE + '-3-I20-03:p3:actualThk'
    P3_3_THK_4   = BASE + '-3-I20-03:p4:actualThk'
    P3_3_THK_5   = BASE + '-3-I20-03:p5:actualThk'
    P3_4_MAT     = BASE + '-3-I20-04:curr:material'
    P3_4_THK_NOM = BASE + '-3-I20-04:curr:thickness'
    P3_4_THK     = BASE + '-3-I20-04:curr:actualThk'
    P3_4_MAT_1   = BASE + '-3-I20-04:p1:material'
    P3_4_MAT_2   = BASE + '-3-I20-04:p2:material'
    P3_4_MAT_3   = BASE + '-3-I20-04:p3:material'
    P3_4_MAT_4   = BASE + '-3-I20-04:p4:material'
    P3_4_MAT_5   = BASE + '-3-I20-04:p5:material'
    P3_4_THK_1   = BASE + '-3-I20-04:p1:actualThk'
    P3_4_THK_2   = BASE + '-3-I20-04:p2:actualThk'
    P3_4_THK_3   = BASE + '-3-I20-04:p3:actualThk'
    P3_4_THK_4   = BASE + '-3-I20-04:p4:actualThk'
    P3_4_THK_5   = BASE + '-3-I20-04:p5:actualThk'
    P3_5_MAT     = BASE + '-3-I20-05:curr:material'
    P3_5_THK_NOM = BASE + '-3-I20-05:curr:thickness'
    P3_5_THK     = BASE + '-3-I20-05:curr:actualThk'
    P3_5_MAT_1   = BASE + '-3-I20-05:p1:material'
    P3_5_MAT_2   = BASE + '-3-I20-05:p2:material'
    P3_5_MAT_3   = BASE + '-3-I20-05:p3:material'
    P3_5_MAT_4   = BASE + '-3-I20-05:p4:material'
    P3_5_MAT_5   = BASE + '-3-I20-05:p5:material'
    P3_5_THK_1   = BASE + '-3-I20-05:p1:actualThk'
    P3_5_THK_2   = BASE + '-3-I20-05:p2:actualThk'
    P3_5_THK_3   = BASE + '-3-I20-05:p3:actualThk'
    P3_5_THK_4   = BASE + '-3-I20-05:p4:actualThk'
    P3_5_THK_5   = BASE + '-3-I20-05:p5:actualThk'

SIM_PV_PREFIX = "sim:"

class FILTER_SIM(Constant):

    P1_1_MAT_1  = SIM_PV_PREFIX + 'P1_1_MAT_1'
    P1_1_MAT_2  = SIM_PV_PREFIX + 'P1_1_MAT_2'
    P1_1_THK_1  = SIM_PV_PREFIX + 'P1_1_THK_1'
    P1_1_THK_2  = SIM_PV_PREFIX + 'P1_1_THK_2'
    P1_2_MAT_1  = SIM_PV_PREFIX + 'P1_2_MAT_1'
    P1_2_MAT_2  = SIM_PV_PREFIX + 'P1_2_MAT_2'
    P1_2_THK_1  = SIM_PV_PREFIX + 'P1_2_THK_1'
    P1_2_THK_2  = SIM_PV_PREFIX + 'P1_2_THK_2'
    P3_1_MAT_1  = SIM_PV_PREFIX + 'P3_1_MAT_1'
    P3_1_MAT_2  = SIM_PV_PREFIX + 'P3_1_MAT_2'
    P3_1_THK_1  = SIM_PV_PREFIX + 'P3_1_THK_1'
    P3_1_THK_2  = SIM_PV_PREFIX + 'P3_1_THK_2'
    P3_2_MAT_1  = SIM_PV_PREFIX + 'P3_2_MAT_1'
    P3_2_MAT_2  = SIM_PV_PREFIX + 'P3_2_MAT_2'
    P3_2_THK_1  = SIM_PV_PREFIX + 'P3_2_THK_1'
    P3_2_THK_2  = SIM_PV_PREFIX + 'P3_2_THK_2'

