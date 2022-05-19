import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from config.log_class import *
from config.errorCode import *

'''
    1. 로그인 CommConnect -> 로그인창 출력 -> onEventConnect
'''


class Kiwoom2(QAxWidget):
    def __init__(self):
        super().__init__()

        # event loop
        self.login_event_loop = QEventLoop()
        self.get_ocx_instance()
        self.event_slots()
        self.signal_login_comm_connect()

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)

    def login_slot(self, nErrCode):
        print('login error code ::: %s %s' % (nErrCode, errors(nErrCode)[1]))
        self.login_event_loop.exit()

    def signal_login_comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop.exec_()


class Ui():
    def __init__(self):
        print('UI class ')
        self.app = QApplication(sys.argv)

        self.kiwoom2 = Kiwoom2()
        self.app.exec_()


if __name__ == "__main__":
    Ui()
