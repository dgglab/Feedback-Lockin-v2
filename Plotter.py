from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

class  CustomWidget(pg.GraphicsWindow):
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    ptr1 = 0
    def __init__(self, parent=None, **kargs):
        pg.GraphicsWindow.__init__(self, **kargs)
        self.setParent(parent)
        #self.setWindowTitle('pyqtgraph example: Scrolling Plots')
        

if __name__ == '__main__':
    w = CustomWidget()
    w.show()
    QtGui.QApplication.instance().exec_()