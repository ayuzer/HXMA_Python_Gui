#******************************************************************************
#
#  @(#)DataArrayInfo.py	2.1  02/14/16 CSS
#
#  "splot" Release 2
#
#  Copyright (c) 2013,2014,2015,2016
#  by Certified Scientific Software.
#  All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software ("splot") and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  Neither the name of the copyright holder nor the names of its contributors
#  may be used to endorse or promote products derived from this software
#  without specific prior written permission.
#
#     * The software is provided "as is", without warranty of any   *
#     * kind, express or implied, including but not limited to the  *
#     * warranties of merchantability, fitness for a particular     *
#     * purpose and noninfringement.  In no event shall the authors *
#     * or copyright holders be liable for any claim, damages or    *
#     * other liability, whether in an action of contract, tort     *
#     * or otherwise, arising from, out of or in connection with    *
#     * the software or the use of other dealings in the software.  *
#
#******************************************************************************

class DataArrayInfo(object):

    def __init__(self, initvals=None):
         self.rows, self.cols, self.arrtype, self.flags = (None,)*4
  
         if initvals and len(initvals) == 4:
             self.rows, self.cols, self.arrtype, self.flags = initvals

    def isMca(self):
        if (self.flags & 0x20):
            return True

        return False

    def isImage(self):
        if (self.flags & 0x20):
            return True

        return False

 
def main():
    import sys
    import datashm
 
    try:
        specname = sys.argv[1]
        arrname = sys.argv[2]
    except:
        print("Wrong usage: %s spec arrname" % sys.argv[0])
        sys.exit(0)

    arrinfo = DataArrayInfo( datashm.getarrayinfo(specname, arrname)  )
    print("Is Image -> %s" %  arrinfo.isImage())

if __name__ == '__main__':
    main()

   
     
