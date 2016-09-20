import sys
import time

from PyQt4.QtGui import QApplication

from monitor import EpicsMonitor

BMIT_PVS = [

    #'PFIL1605-1-I20-01:material',
    #'PFIL1605-1-I20-01:thickness',
    'PFIL1605-1-I20-01:closed',
    'PFIL1605-1-I20-01:opened',

    #'PFIL1605-1-I20-02:material',
    #'PFIL1605-1-I20-02:thickness',
    'PFIL1605-1-I20-02:closed',
    'PFIL1605-1-I20-02:opened',

    #'PFIL1605-1-I20-03:curr:material',
    #'PFIL1605-1-I20-03:curr:thickness',
    #'PFIL1605-1-I20-03:curr:actualThk',
    #
    #'PFIL1605-1-I20-03:p1:material',
    #'PFIL1605-1-I20-03:p2:material',
    #'PFIL1605-1-I20-03:p3:material',
    #'PFIL1605-1-I20-03:p4:material',
    #'PFIL1605-1-I20-03:p5:material',
    #
    #'PFIL1605-1-I20-03:p1:actualThk',
    #'PFIL1605-1-I20-03:p2:actualThk',
    #'PFIL1605-1-I20-03:p3:actualThk',
    #'PFIL1605-1-I20-03:p4:actualThk',
    #'PFIL1605-1-I20-03:p5:actualThk',
    #
    #'PFIL1605-1-I20-04:curr:material',
    #'PFIL1605-1-I20-04:curr:thickness',
    #'PFIL1605-1-I20-04:curr:actualThk',
    #
    #'PFIL1605-1-I20-04:p1:material',
    #'PFIL1605-1-I20-04:p2:material',
    #'PFIL1605-1-I20-04:p3:material',
    #'PFIL1605-1-I20-04:p4:material',
    #'PFIL1605-1-I20-04:p5:material',
    #
    #'PFIL1605-1-I20-04:p1:actualThk',
    #'PFIL1605-1-I20-04:p2:actualThk',
    #'PFIL1605-1-I20-04:p3:actualThk',
    #'PFIL1605-1-I20-04:p4:actualThk',
    #'PFIL1605-1-I20-04:p5:actualThk',
    #
    #'PFIL1605-1-I20-05:curr:material',
    #'PFIL1605-1-I20-05:curr:thickness',
    #'PFIL1605-1-I20-05:curr:actualThk',
    #
    #'PFIL1605-1-I20-05:p1:material',
    #'PFIL1605-1-I20-05:p2:material',
    #'PFIL1605-1-I20-05:p3:material',
    #'PFIL1605-1-I20-05:p4:material',
    #'PFIL1605-1-I20-05:p5:material',
    #
    #'PFIL1605-1-I20-05:p1:actualThk',
    #'PFIL1605-1-I20-05:p2:actualThk',
    #'PFIL1605-1-I20-05:p3:actualThk',
    #'PFIL1605-1-I20-05:p4:actualThk',
    #'PFIL1605-1-I20-05:p5:actualThk',
    #
    #'PFIL1605-3-I20-01:material',
    #'PFIL1605-3-I20-01:thickness',
    'PFIL1605-3-I20-01:closed',
    'PFIL1605-3-I20-01:opened',

    #'PFIL1605-3-I20-02:material',
    #'PFIL1605-3-I20-02:thickness',
    'PFIL1605-3-I20-02:closed',
    'PFIL1605-3-I20-02:opened',

    #'PFIL1605-3-I20-03:curr:material',
    #'PFIL1605-3-I20-03:curr:thickness',
    #'PFIL1605-3-I20-03:curr:actualThk',
    #
    #'PFIL1605-3-I20-03:p1:material',
    #'PFIL1605-3-I20-03:p2:material',
    #'PFIL1605-3-I20-03:p3:material',
    #'PFIL1605-3-I20-03:p4:material',
    #'PFIL1605-3-I20-03:p5:material',
    #
    #'PFIL1605-3-I20-03:p1:actualThk',
    #'PFIL1605-3-I20-03:p2:actualThk',
    #'PFIL1605-3-I20-03:p3:actualThk',
    #'PFIL1605-3-I20-03:p4:actualThk',
    #'PFIL1605-3-I20-03:p5:actualThk',
    #
    #'PFIL1605-3-I20-04:curr:material',
    #'PFIL1605-3-I20-04:curr:thickness',
    #'PFIL1605-3-I20-04:curr:actualThk',
    #
    #'PFIL1605-3-I20-04:p1:material',
    #'PFIL1605-3-I20-04:p2:material',
    #'PFIL1605-3-I20-04:p3:material',
    #'PFIL1605-3-I20-04:p4:material',
    #'PFIL1605-3-I20-04:p5:material',
    #
    #'PFIL1605-3-I20-04:p1:actualThk',
    #'PFIL1605-3-I20-04:p2:actualThk',
    #'PFIL1605-3-I20-04:p3:actualThk',
    #'PFIL1605-3-I20-04:p4:actualThk',
    #'PFIL1605-3-I20-04:p5:actualThk',
    #
    #'PFIL1605-3-I20-05:curr:material',
    #'PFIL1605-3-I20-05:curr:thickness',
    #'PFIL1605-3-I20-05:curr:actualThk',
    #
    #'PFIL1605-3-I20-05:p1:material',
    #'PFIL1605-3-I20-05:p2:material',
    #'PFIL1605-3-I20-05:p3:material',
    #'PFIL1605-3-I20-05:p4:material',
    #'PFIL1605-3-I20-05:p5:material',
    #
    #'PFIL1605-3-I20-05:p1:actualThk',
    #'PFIL1605-3-I20-05:p2:actualThk',
    #'PFIL1605-3-I20-05:p3:actualThk',
    #'PFIL1605-3-I20-05:p4:actualThk',
    #'PFIL1605-3-I20-05:p5:actualThk',

    #--------------------------------
    # BM (05B1-1) Beamline Filter PVs
    #--------------------------------

    #'PFIL1605-1-B10-01:curr:material',
    #'PFIL1605-1-B10-01:curr:thickness',
    #'PFIL1605-1-B10-01:curr:actualThk',
    #'PFIL1605-1-B10-01:p1:material',
    #'PFIL1605-1-B10-01:p2:material',
    #'PFIL1605-1-B10-01:p3:material',
    #'PFIL1605-1-B10-01:p4:material',
    #'PFIL1605-1-B10-01:p5:material',
    #'PFIL1605-1-B10-01:p1:actualThk',
    #'PFIL1605-1-B10-01:p2:actualThk',
    #'PFIL1605-1-B10-01:p3:actualThk',
    #'PFIL1605-1-B10-01:p4:actualThk',
    #'PFIL1605-1-B10-01:p5:actualThk',
    #
    #'PFIL1605-1-B10-02:curr:material',
    #'PFIL1605-1-B10-02:curr:thickness',
    #'PFIL1605-1-B10-02:curr:actualThk',
    #'PFIL1605-1-B10-02:p1:material',
    #'PFIL1605-1-B10-02:p2:material',
    #'PFIL1605-1-B10-02:p3:material',
    #'PFIL1605-1-B10-02:p4:material',
    #'PFIL1605-1-B10-02:p5:material',
    #'PFIL1605-1-B10-02:p1:actualThk',
    #'PFIL1605-1-B10-02:p2:actualThk',
    #'PFIL1605-1-B10-02:p3:actualThk',
    #'PFIL1605-1-B10-02:p4:actualThk',
    #'PFIL1605-1-B10-02:p5:actualThk',
    #
    #'PFIL1605-1-B10-03:curr:material',
    #'PFIL1605-1-B10-03:curr:thickness',
    #'PFIL1605-1-B10-03:curr:actualThk',
    #'PFIL1605-1-B10-03:p1:material',
    #'PFIL1605-1-B10-03:p2:material',
    #'PFIL1605-1-B10-03:p3:material',
    #'PFIL1605-1-B10-03:p4:material',
    #'PFIL1605-1-B10-03:p5:material',
    #'PFIL1605-1-B10-03:p1:actualThk',
    #'PFIL1605-1-B10-03:p2:actualThk',
    #'PFIL1605-1-B10-03:p3:actualThk',
    #'PFIL1605-1-B10-03:p4:actualThk',
    #'PFIL1605-1-B10-03:p5:actualThk',
]

if __name__ == "__main__":
    """
    Program entry point
    """
    app = QApplication(sys.argv)

    monitor = EpicsMonitor()

    print BMIT_PVS

    for pv in BMIT_PVS:
        monitor.add(pv)

    monitor.start()

    time.sleep(1)

    for pv in BMIT_PVS:
        value = monitor.get_data(pv)
        # print "%s ---> '%s'" % (pv, value)
        ftype = value.get('ftype')
        #print "name: %s ftype: %d" % (pv, ftype)

        # v = monitor.get_value(pv)
        # print "%s -> %s" % (pv, v)
        # continue

        if ftype == 6:
            t1 = 'ai'
            t2 = 'INP'
        elif ftype == 0:
            t1 = 'stringin'
            t2 = 'VAL'
        elif ftype == 3:    # I am just guessing that ftype 3 == bi
            t1 = 'bi'
            t2 = 'INP'

        n = pv.replace('PFIL1605', 'breem')

        # I don't think I am properly formatting these records (esp the
        # binary ones), but it seems to be enough to simulate the PVs
        # in my app for testing

        print 'record(%s, "%s")' % (t1, n)
        print '{'
        print '    field(DESC, "%s")' % 'simulated'
        print '    field(%s, "%s")' % cd (t2, value.get('char_value'))
        print '}'

