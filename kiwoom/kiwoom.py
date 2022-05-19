import os
import sys
import datetime
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from config.errorCode import *
from PyQt5.QtTest import *
from config.KiwoomType import *
from config.log_class import *


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self.realType = RealType()
        self.logging = Logging()

        # evnet loop 모음
        self.login_event_loop = QEventLoop()
        self.detail_account_info_event_loop = QEventLoop()
        self.calculator_event_loop = QEventLoop()
        # 전체 종목 관리
        self.all_stock_dict = {}
        # 계좌 관련 변수
        self.account_stock_dict = {}
        self.not_account_stock_dict = {}
        self.deposit = 0  # 예수금
        self.use_money = 0  # 실제 투자에 사용할 금액
        self.use_money_percent = 1.0  # 예수금에서 실제 사용할 비율
        self.output_deposit = 0  # 출력 가능 금액
        self.total_profit_loss_rate = 0.0
        self.total_profit_loss_money = 0
        self.total_buy_money = 0

        # 트레이딩 종목 정보 딕셔너리
        self.portfolio_stock_dict = {}
        self.jango_dict = {}
        self.condition_dict = {}
        self.mm_dict = {}

        # 수익률
        self.profit_rate = 7
        self.loss_rate = -5

        # 종목 분석 용
        self.calcul_data = []

        # 스크린 번호 모음
        self.screen_my_info = "2000"  # 계좌 관련한 스크린 번호
        self.screen_calculate_stock = "4000"  # 계산용 스크린 번호
        self.screen_real_stock = "5000"  # 종목별 실시간 할당 스크린번호
        self.screen_meme_stock = "6000"  # 종목별 주문용 스크린번호
        self.screen_start_stop_real = "1000"  # 장 시작 / 종료 실시간 스크린번호

        # 계좌 갯수
        self.account_num = None

        # 초기 세팅 실행 함수
        self.get_ocx_instance()
        self.event_slots()
        self.real_event_slots()
        self.signal_login_comm_connect()
        self.get_account_info()
        self.detail_account_info()
        self.detail_account_mystock()
        QTimer.singleShot(5000, self.not_concluded_account)  # 5초 뒤에 미체결 종목을 가져오기 실행

        QTest.qWait(1000)
        self.read_code()
        self.screen_number_setting()

        QTest.qWait(5000)

        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", self.screen_start_stop_real, '', self.realType.REALTYPE['장시작시간']['장운영구분'], "0")

        # for code in self.portfolio_stock_dict.keys():
        #     screen_num = self.portfolio_stock_dict[code]['스크린번호']
        #     fids = self.realType.REALTYPE['주식체결']['체결시간']
        #     self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_num, code, fids, "1")

        # self.calculator_fnc()  # 종목분석용 임시용으로 적용
        # 조건 검색식
        self.condition_event_slot()
        self.condition_signal()

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.trdata_slot)
        self.OnReceiveMsg.connect(self.msg_slot)

    def real_event_slots(self):
        self.OnReceiveRealData.connect(self.realdata_slot)
        self.OnReceiveChejanData.connect(self.chejan_slot)

    def login_slot(self, errCode):
        self.logging.logger.debug(errors(errCode)[1])
        self.login_event_loop.exit()

    def signal_login_comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop.exec_()

    def get_account_info(self):
        account_list = self.dynamicCall("GetLoginInfo(String)", "ACCLIST")
        print('계좌정보 리스트 값 : %s' % account_list)
        self.account_num = account_list.split(';')[1]
        print('나의 보유계좌 번호 %s ' % self.account_num)

    def detail_account_info(self):
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        print('예수금 요청하는 부분 예수금 : %s' % self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호', '0000')
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(QString, QString)', '조회구분', '2')
        self.dynamicCall('CommRqData(QString, QString, int, String)', '예수금상세현황요청', 'opw00001', "0", self.screen_my_info)
        self.detail_account_info_event_loop.exec_()

    def detail_account_mystock(self, sPrevNext='0'):
        print('계좌평가 잔고내역 요청')
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호', '0000')
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(QString, QString)', '조회구분', '2')
        self.dynamicCall('CommRqData(QString, QString, int, String)', '계좌평가잔고내역요청', 'opw00018', sPrevNext, self.screen_my_info)
        self.detail_account_info_event_loop.exec_()

    def not_concluded_account(self, sPrevNext="0"):
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '체결구분', "1")
        self.dynamicCall('SetInputValue(QString, QString)', '매매구분', "0")
        self.dynamicCall('CommRqData(QString, QString, int, String)', '실시간미체결요청', 'opt10075', sPrevNext, self.screen_my_info)
        self.detail_account_info_event_loop.exec_()

    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        '''
        tr 요청을 받는 슬롯이다.
        :param sScrNo: 스크린 번호
        :param sRQName: 내가 요청했을 때 지은 이름
        :param sTrCode: 요청 id,  tr코드
        :param sRecordName: 사용안함
        :param sPrevNex: 다음 페이지가 있는지
        :return:
        '''
        if sRQName == '예수금상세현황요청':
            deposit = self.dynamicCall("GetCommData(QString, QString, int, String)", sTrCode, sRQName, 0, "예수금")
            self.deposit = int(deposit)
            use_money = float(self.deposit) * self.use_money_percent
            self.use_money = int(use_money)
            # self.use_money = self.use_money / 10

            output_deposit = self.dynamicCall("GetCommData(QString, QString, int, String)", sTrCode, sRQName, 0, "출금가능금액")
            self.output_deposit = int(output_deposit)

            self.logging.logger.debug("출금 가능 금액 : %s" % self.output_deposit)
            self.stop_screen_cancel(self.screen_my_info)

            self.detail_account_info_event_loop.exit()

        if sRQName == '계좌평가잔고내역요청':
            total_buy_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총매입금액")
            self.total_buy_money = int(total_buy_money)
            total_profit_loss_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총평가손익금액")
            self.total_profit_loss_money = int(total_profit_loss_money)
            total_profit_loss_rate = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총수익률(%)")
            self.total_profit_loss_rate = float(total_profit_loss_rate)
            self.logging.logger.debug("계좌평가잔고내역요청 싱글데이터 : %s - %s - %s" % (total_buy_money, total_profit_loss_money, total_profit_loss_rate))
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목번호")
                code = code.strip()[1:]
                code_nm = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명")
                stock_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "보유수량")
                buy_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매입가")
                learn_rate = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "수익률(%)")
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "현재가")
                total_che_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매입금액")
                possible_qty = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매매가능수량")

                self.logging.logger.debug("종목코드: %s - 종목명: %s - 보유수량: %s - 매입가:%s - 수익률: %s - 현재가: %s" % (
                    code, code_nm, stock_quantity, buy_price, learn_rate, current_price))
                if code in self.account_stock_dict.keys():
                    pass
                else:
                    self.account_stock_dict[code] = {}

                code_nm = code_nm.strip()
                stock_quantity = int(stock_quantity.strip())
                buy_price = int(buy_price.strip())
                learn_rate = float(learn_rate.strip())
                current_price = int(current_price.strip())
                total_che_price = int(total_che_price.strip())
                possible_qty = int(possible_qty.strip())

                self.account_stock_dict[code].update({'종목명': code_nm})
                self.account_stock_dict[code].update({'보유수량': stock_quantity})
                self.account_stock_dict[code].update({'매입가': buy_price})
                self.account_stock_dict[code].update({'수익률(%)': learn_rate})
                self.account_stock_dict[code].update({'현재가': current_price})
                self.account_stock_dict[code].update({'매입금액': total_che_price})
                self.account_stock_dict[code].update({'매매가능수량': possible_qty})

            self.logging.logger.debug("sPreNext : %s" % sPrevNext)
            print("계좌에 가지고 있는 종목은 %s " % rows)

            if sPrevNext == '2':
                self.detail_account_mystock(sPrevNext="2")
            else:
                self.detail_account_info_event_loop.exit()

        elif sRQName == "실시간미체결요청":
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목코드")
                code_nm = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명")
                order_no = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문번호")
                order_status = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문상태")
                order_qty = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문수량")
                order_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문가격")
                order_gubun = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문구분")
                not_qty = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "미체결수량")
                ok_qty = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "체결량")

                code = code.strip()
                code_nm = code_nm.strip()
                order_no = int(order_no.strip())
                order_no = int(order_no.strip())
                order_status = order_status.strip()
                order_qty = int(order_qty.strip())
                order_price = int(order_price.strip())
                order_gubun = order_gubun.strip().lstrip('+').lstrip('-')
                not_qty = int(not_qty.strip())
                ok_qty = int(ok_qty.strip())

                if order_no in self.not_account_stock_dict.keys():
                    pass
                else:
                    self.not_account_stock_dict[order_no] = {}

                self.not_account_stock_dict[order_no].update({"종목코드": code})
                self.not_account_stock_dict[order_no].update({"종목명": code_nm})
                self.not_account_stock_dict[order_no].update({"주문번호": order_no})
                self.not_account_stock_dict[order_no].update({"주문상태": order_status})
                self.not_account_stock_dict[order_no].update({"주문수량": order_qty})
                self.not_account_stock_dict[order_no].update({"주문가격": order_price})
                self.not_account_stock_dict[order_no].update({"주문구분": order_gubun})
                self.not_account_stock_dict[order_no].update({"미체결수량": not_qty})
                self.not_account_stock_dict[order_no].update({"체결량": ok_qty})

                print('미체결 종목 : %s' % self.not_account_stock_dict[order_no])
            self.detail_account_info_event_loop.exit()

        elif "주식일봉차트조회" == sRQName:
            code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목코드")
            code = code.strip()
            print('%s 일봉데이터 요청' % code)
            cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            for i in range(cnt):
                data = []
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "현재가")
                value = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "거래량")
                trading_value = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "거래대금")
                date = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "일자")
                start_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "시가")
                high_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "고가")
                low_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "저가")
                # getcommonEx
                data.append("")
                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())
                data.append("")
                self.calcul_data.append(data.copy())

            print(self.calcul_data)

            # 한번 조회하면 600일치까지 일봉데이터를 받을 수 있다.

            if sPrevNext == "2":
                self.day_kiwoom_db(code=code, sPrevNext=sPrevNext)
            else:
                print('총 일수 %s' % len(self.calcul_data))
                pass_success = False

                # 120일 이평선을 그릴 만큼의 데이터가 있는지 체크
                if self.calcul_data is None or len(self.calcul_data) < 120:
                    pass_success = False
                else:
                    # 120일 이상 되면은
                    total_price = 0
                    for value in self.calcul_data[:120]:  # 119일전
                        total_price += int(value[1])
                    moving_average_price = total_price / 120
                    # 오늘자 주가가 120일 이평선에 걸쳐 있는 지 확인
                    bottom_stock_price = False
                    check_price = None
                    if int(self.calcul_data[0][7]) <= moving_average_price <= int(self.calcul_data[0][6]):
                        print('오늘 주가 120 이평선에 걸쳐 있는 것 확인')
                        bottom_stock_price = True
                        check_price = int(self.calcul_data[0][6])
                    prev_price = None
                    if bottom_stock_price:
                        moving_average_price_prev = 0
                        price_top_moving = False
                        idx = 1
                        while True:
                            if len(self.calcul_data[idx:]) < 120:
                                print('120일치가 없음')
                                break

                            total_price = 0
                            for value in self.calcul_data[idx:120 + idx]:
                                total_price += int(value[1])
                            moving_average_price_prev = total_price / 120

                            if moving_average_price_prev <= int(self.calcul_data[idx][6]) and idx <= 20:
                                print("20일 동안 주가가 120일 이평선과 같거나 위에 있으면 조건 통과 못함")
                                price_top_moving = False
                                break
                            elif int(self.calcul_data[idx][7] > moving_average_price_prev and idx > 20):
                                print('120일 이평선 위에 있는 일봉 확인됨')
                                price_top_moving = True
                                prev_price = int(self.calcul_data[idx][7])
                                break

                            idx += 1
                        #     해당부분 이평선이 가장 최근 일자의 이평선 가격보다 낮은지 확인
                        if price_top_moving:
                            if moving_average_price_prev > moving_average_price_prev and check_price > prev_price:
                                print('포착된 이평선의 가격이 오늘자(최근일자) 이평선 가격보다 낮은 것 확인됨')
                                print('포착된 부분의 일봉 저가가 오늘자 일봉의 고가보다 낮은지 확인됨')
                                pass_success = True

                if pass_success:
                    print('조건부 통과됨')
                    code_nm = self.dynamicCall("GetMasterCodeName(QString)", code)
                    f = open('files/condition_stock.txt', 'a', encoding="utf8")
                    f.write('%s\t%s\t%s\n' % (code, code_nm, str(self.calcul_data[0][1]),))
                    f.close()
                elif not pass_success:
                    print('조건부 통과 못함')

                self.calcul_data.clear()

                self.calculator_event_loop.exit()

    def get_code_list_by_market(self, market_code):
        '''
        종목코드들 반환
        :param market_code:
        :return:
        '''
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_code)
        code_list = code_list.split(";")[:-1]
        return code_list

    def calculator_fnc(self):
        code_list = self.get_code_list_by_market("10")
        print('코스닥 갯수 %s' % len(code_list))
        for idx, code in enumerate(code_list):
            # 스크린 번호를 끓는 방법
            self.dynamicCall("DisconnectRealData(QString)", self.screen_calculate_stock)
            print("%s / %s : 코스닥 코드 : %s is updating... " % (idx + 1, len(code_list), code))
            self.day_kiwoom_db(code=code)

    def day_kiwoom_db(self, code=None, date=None, sPrevNext="0"):
        QTest.qWait(360)

        self.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)
        self.dynamicCall('SetInputValue(QString, QString)', '수정주가구분', "1")

        if date is not None:
            self.dynamicCall('SetInputValue(QString, QString)', '기준일자', date)

        self.dynamicCall('CommRqData(QString, QString, int, String)', '주식일봉차트조회', 'opt10081', sPrevNext, self.screen_calculate_stock)
        self.calculator_event_loop.exec_()

    def read_code(self):
        if os.path.exists('files/condition_stock.txt'):
            f = open('files/condition_stock.txt', 'r', encoding='utf8')
            lines = f.readlines()
            for line in lines:
                if line != "":
                    ls = line.split('\t')
                    stock_code = ls[0]
                    stock_name = ls[1]
                    stock_price = int(ls[2].split('\n')[0])
                    stock_price = abs(stock_price)
                    self.portfolio_stock_dict.update({stock_code: {'종목명': stock_name, '현재가': stock_price}})
            f.close()
            print(self.portfolio_stock_dict)

    def merge_dict(self):
        self.all_stock_dict.update({"계좌평가잔고내역": self.account_stock_dict})
        self.all_stock_dict.update({'미체결종목': self.not_account_stock_dict})
        self.all_stock_dict.update({'포트폴리오종목': self.portfolio_stock_dict})

    def screen_number_setting(self):
        screen_overwrite = []
        # 계좌 평가 잔고 내역에 있는 종목들
        for code in self.account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들
        for order_number in self.not_account_stock_dict.keys():
            code = self.not_account_stock_dict[order_number]['종목코드']
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 포트 폴리오에 담겨 있는 종목들
        for code in self.portfolio_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 스크린 번호 할당
        cnt = 0
        for code in screen_overwrite:
            temp_screen = int(self.screen_real_stock)
            meme_screen = int(self.screen_meme_stock)
            if (cnt % 50) == 0:
                temp_screen += 1
                self.screen_real_stock = str(temp_screen)

            if (cnt % 50) == 0:
                meme_screen += 1
                self.screen_meme_stock = str(meme_screen)

            if code in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict[code].update({"스크린번호": str(self.screen_real_stock)})
                self.portfolio_stock_dict[code].update({"주문용스크린번호": str(self.screen_meme_stock)})
            elif code not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update({code: {'스크린번호': str(self.screen_real_stock)}})
                self.portfolio_stock_dict.update({code: {'주문용스크린번호': str(self.screen_meme_stock)}})
            cnt += 1

    def realdata_slot(self, sCode, sRealType, sRealData):
        if sRealType == '장시작시간':
            fid = self.realType.REALTYPE[sRealType]['장운영구분']
            value = self.dynamicCall("GetCommRealData(QString, int)", sCode, fid)
            if value == '0':
                self.logging.logger.debug("장 시작 전")
            elif value == '3':
                self.logging.logger.debug("장 시작")
            elif value == '2':
                self.logging.logger.debug("장 종료, 동시호가로 넘어감")
            elif value == '4':
                self.logging.logger.debug("3시30분 장 종료")
                for code in self.portfolio_stock_dict.keys():
                    self.dynamicCall('SetRealRemove(QString, QString)', self.portfolio_stock_dict[code]['스크린번호'], code)
                QTest.qWait(5000)
                # self.file_delete()
                # self.calculator_fnc()
                sys.exit()

        if sRealType == '주식체결':
            a = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['체결시간'])  # 출력 HHMMSS
            b = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['현재가'])  # 출력 : +(-)2520
            b = abs(int(b))

            c = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['전일대비'])  # 출력 : +(-)2520
            c = abs(int(c))

            d = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['등락율'])  # 출력 : +(-)12.98
            d = float(d)

            e = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['(최우선)매도호가'])  # 출력 : +(-)2520
            e = abs(int(e))

            f = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['(최우선)매수호가'])  # 출력 : +(-)2515
            f = abs(int(f))

            g = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['거래량'])  # 출력 : +240124  매수일때, -2034 매도일 때
            g = abs(int(g))

            h = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['누적거래량'])  # 출력 : 240124
            h = abs(int(h))

            i = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['고가'])  # 출력 : +(-)2530
            i = abs(int(i))

            j = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['시가'])  # 출력 : +(-)2530
            j = abs(int(j))

            k = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['저가'])  # 출력 : +(-)2530
            k = abs(int(k))

            if sCode not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update({sCode: {}})

            self.portfolio_stock_dict[sCode].update({"체결시간": a})
            self.portfolio_stock_dict[sCode].update({"현재가": b})
            self.portfolio_stock_dict[sCode].update({"전일대비": c})
            self.portfolio_stock_dict[sCode].update({"등락율": d})
            self.portfolio_stock_dict[sCode].update({"(최우선)매도호가": e})
            self.portfolio_stock_dict[sCode].update({"(최우선)매수호가": f})
            self.portfolio_stock_dict[sCode].update({"거래량": g})
            self.portfolio_stock_dict[sCode].update({"누적거래량": h})
            self.portfolio_stock_dict[sCode].update({"고가": i})
            self.portfolio_stock_dict[sCode].update({"시가": j})
            self.portfolio_stock_dict[sCode].update({"저가": k})

            # 조건 계좌잔고 평가내역에 있고 오늘 산 잔고에는 없을 경우
            if sCode in self.account_stock_dict.keys() and sCode not in self.jango_dict.keys():
                self.logging.logger.debug("[체결] 종목코드:%s, 체결시간:%s, 현재가:%s 전일대비:%s 등락율:%s" % (sCode, a, str(b), str(c), str(d)))
                asd = self.account_stock_dict[sCode]
                meme_rate = (b - asd['매입가']) / asd['매입가'] * 100
                if asd['매매가능수량'] > 0 and (meme_rate > self.profit_rate or meme_rate < self.loss_rate):
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 2, sCode, asd['매매가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )
                    if order_success == 0:
                        self.logging.logger.debug("[계좌잔고 매도(신규매도)] 종목코드:%s 수량:%s 시장가 계좌번호:%s" % (sCode, str(asd['매매가능수량']), self.account_num))
                        del self.account_stock_dict[sCode]
                    else:
                        self.logging.logger.debug("[계좌잔고 매도(신규매도)] 매도주문 실패 종목코드:%s" % sCode)

            elif sCode in self.jango_dict.keys():
                self.logging.logger.debug("[체결] 종목코드:%s, 체결시간:%s, 현재가:%s 전일대비:%s 등락율:%s" % (sCode, a, str(b), str(c), str(d)))
                jd = self.jango_dict[sCode]
                meme_rate = (b - jd['매입단가']) / jd['매입단가'] * 100
                if jd['주문가능수량'] > 0 and (meme_rate > self.profit_rate or meme_rate < self.loss_rate):
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 2, sCode, jd['주문가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )
                    if order_success == 0:
                        self.logging.logger.debug("[오늘잔고매도(신규매도)] 종목코드:%s 수량:%s 시장가 계좌번호:%s" % (sCode, str(jd['주문가능수량']), self.account_num))
                    else:
                        self.logging.logger.debug("[오늘잔고매도(신규매도)] 매도주문 실패 종목코드:%s" % sCode)

            elif (sCode not in self.jango_dict.keys()) or (sCode not in self.mm_dict.keys()):
                self.logging.logger.debug("매수조건 통과 %s " % sCode)
                self.logging.logger.debug("[체결] 종목코드:%s, 체결시간:%s, 현재가:%s 전일대비:%s 등락율:%s" % (sCode, a, str(b), str(c), str(d)))
                # result = (self.use_money * 0.1 * 0.2) / e
                if e is not None and e > 0:
                    if self.portfolio_stock_dict[sCode].get('buy') is None:
                        result = 1000000 / e
                        qty = int(result)
                        order_success = self.dynamicCall(
                            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                            ["신규매수", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 1, sCode, qty, e, self.realType.SENDTYPE['거래구분']['지정가'], ""]
                        )
                        if order_success == 0:
                            self.portfolio_stock_dict[sCode].update({"buy": "yes"})
                            if sCode not in self.mm_dict.keys():
                                self.mm_dict.update({sCode: {}})
                                self.mm_dict[sCode].update({'매수시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                                self.mm_dict[sCode].update({'매수수량': str(qty)})
                            self.logging.logger.debug("[신규매수] 종목코드:%s 수량:%s 시장가 계좌번호:%s" % (sCode, str(qty), self.account_num))
                        else:
                            self.logging.logger.debug("[신규매수] 신규매수 실패 종목코드:%s" % sCode)

            not_meme_list = list(self.not_account_stock_dict)
            # not_meme_list = self.not_account_stock_dict.copy()
            for order_num in not_meme_list:
                code = self.not_account_stock_dict[order_num]['종목코드']
                meme_price = self.not_account_stock_dict[order_num]['주문가격']
                not_quantity = self.not_account_stock_dict[order_num]['미체결수량']
                order_gubun = self.not_account_stock_dict[order_num]['주문구분']
                if order_gubun == '매수' and not_quantity > 0 and e > meme_price:
                    self.logging.logger.debug("[체결] 종목코드:%s, 체결시간:%s, 현재가:%s 전일대비:%s 등락율:%s" % (sCode, a, str(b), str(c), str(d)))
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["매수취소", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 3, code, 0, 0, self.realType.SENDTYPE['거래구분']['지정가'], order_num]
                    )
                    if order_success == 0:
                        self.logging.logger.debug("[매수취소] 종목코드:%s 미체결수량:%s 지정가 계좌번호:%s" % (sCode, str(not_quantity), self.account_num))
                    else:
                        self.logging.logger.debug("[매수취소] 매수취소 실패 종목코드:%s" % sCode)

                elif not_quantity == 0:
                    self.logging.logger.debug("[체결] 종목코드:%s, 체결시간:%s, 현재가:%s 전일대비:%s 등락율:%s" % (sCode, a, str(b), str(c), str(d)))
                    self.logging.logger.debug("del self.not_account_stock_dict[order_num]")
                    del self.not_account_stock_dict[order_num]

    # 주문 -> 접수 -> 확인 -> 체결 -> 잔고 -> 체결 -> 잔고
    def chejan_slot(self, sGubun, nItemCnt, sFIdList):
        if int(sGubun) == 0:  # 주문 체결
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목명'])
            stock_name = stock_name.strip()

            origin_order_number = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['원주문번호'])  # 출력 : defaluse : "000000"
            order_number = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문번호'])  # 출럭: 0115061 마지막 주문번호

            order_status = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문상태'])  # 출력: 접수, 확인, 체결
            order_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문수량'])  # 출력 : 3
            order_quan = int(order_quan)

            order_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문가격'])  # 출력: 21000
            order_price = int(order_price)

            not_chegual_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['미체결수량'])  # 출력: 15, default: 0
            not_chegual_quan = int(not_chegual_quan)

            order_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문구분'])  # 출력: -매도, +매수
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')

            chegual_time_str = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문/체결시간'])  # 출력: '151028'

            chegual_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['체결가'])  # 출력: 2110  default : ''
            if chegual_price == '':
                chegual_price = 0
            else:
                chegual_price = int(chegual_price)

            chegual_quantity = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['체결량'])  # 출력: 5  default : ''
            if chegual_quantity == '':
                chegual_quantity = 0
            else:
                chegual_quantity = int(chegual_quantity)

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['현재가'])  # 출력: -6000
            current_price = abs(int(current_price))

            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['(최우선)매도호가'])  # 출력: -6010
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['(최우선)매수호가'])  # 출력: -6000
            first_buy_price = abs(int(first_buy_price))

            #  새로 들어온 주문이면 주문번호 할당
            if order_number not in self.not_account_stock_dict.keys():
                self.not_account_stock_dict.update({order_number: {}})

            self.not_account_stock_dict[order_number].update({"종목코드": sCode})
            self.not_account_stock_dict[order_number].update({"주문번호": order_number})
            self.not_account_stock_dict[order_number].update({"종목명": stock_name})
            self.not_account_stock_dict[order_number].update({"주문상태": order_status})
            self.not_account_stock_dict[order_number].update({"주문수량": order_quan})
            self.not_account_stock_dict[order_number].update({"주문가격": order_price})
            self.not_account_stock_dict[order_number].update({"미체결수량": not_chegual_quan})
            self.not_account_stock_dict[order_number].update({"원주문번호": origin_order_number})
            self.not_account_stock_dict[order_number].update({"주문구분": order_gubun})
            self.not_account_stock_dict[order_number].update({"주문/체결시간": chegual_time_str})
            self.not_account_stock_dict[order_number].update({"체결가": chegual_price})
            self.not_account_stock_dict[order_number].update({"체결량": chegual_quantity})
            self.not_account_stock_dict[order_number].update({"현재가": current_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매도호가": first_sell_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매수호가": first_buy_price})

        # 잔고 인 경우
        if int(sGubun) == 1:
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목코드'])[1:]

            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목명'])
            stock_name = stock_name.strip()

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['현재가'])
            current_price = abs(int(current_price))

            stock_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['보유수량'])
            stock_quan = int(stock_quan)

            like_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['주문가능수량'])
            like_quan = int(like_quan)

            buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매입단가'])
            buy_price = abs(int(buy_price))

            total_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['총매입가'])  # 계좌에 있는 종목의 총매입가
            total_buy_price = int(total_buy_price)

            meme_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매도매수구분'])
            meme_gubun = self.realType.REALTYPE['매도수구분'][meme_gubun]

            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            if sCode not in self.jango_dict.keys():
                self.jango_dict.update({sCode: {}})

            self.jango_dict[sCode].update({"현재가": current_price})
            self.jango_dict[sCode].update({"종목코드": sCode})
            self.jango_dict[sCode].update({"종목명": stock_name})
            self.jango_dict[sCode].update({"보유수량": stock_quan})
            self.jango_dict[sCode].update({"주문가능수량": like_quan})
            self.jango_dict[sCode].update({"매입단가": buy_price})
            self.jango_dict[sCode].update({"총매입가": total_buy_price})
            self.jango_dict[sCode].update({"매도매수구분": meme_gubun})
            self.jango_dict[sCode].update({"(최우선)매도호가": first_sell_price})
            self.jango_dict[sCode].update({"(최우선)매수호가": first_buy_price})

            if stock_quan == 0:
                del self.jango_dict[sCode]

    def msg_slot(self, sScrNo, sRQName, sTrCode, msg):
        self.logging.logger.debug("스크린: %s, 요청이름: %s, tr코드: %s --- %s" % (sScrNo, sRQName, sTrCode, msg))

    # 파일 삭제
    def file_delete(self):
        if os.path.isfile('files/condition_stock.txt'):
            os.remove('files/condition_stock.txt')

    def stop_screen_cancel(self, sScrNo=None):
        self.dynamicCall("DisconnectRealData(QString)", sScrNo)  # 스크린번호 연결 끓기

    # 조건 검색식 이벤트 모음
    def condition_event_slot(self):
        self.OnReceiveConditionVer.connect(self.condition_slot)
        self.OnReceiveTrCondition.connect(self.condition_tr_slot)
        self.OnReceiveRealCondition.connect(self.condition_real_slot)

    # 조건식 로딩 하기
    def condition_signal(self):
        self.dynamicCall("GetConditionLoad()")

    # 어떤 조건식이 있는지 확인
    def condition_slot(self, lRet, sMsg):
        self.logging.logger.debug("호출 성공 여부 %s, 호출결과 메시지 %s" % (lRet, sMsg))

        condition_name_list = self.dynamicCall("GetConditionNameList()")
        self.logging.logger.debug("HTS의 조건검색식 이름 가져오기 %s" % condition_name_list)

        condition_name_list = condition_name_list.split(";")[:-1]

        for unit_condition in condition_name_list:
            index = unit_condition.split("^")[0]
            index = int(index)
            condition_name = unit_condition.split("^")[1]
            # self.logging.logger.debug("조건식 분리 번호: %s, 이름: %s" % (index, condition_name))
            if index in [22]:
                ok = self.dynamicCall("SendCondition(QString, QString, int, int)", "0156", condition_name, index, 1)  # 조회요청 + 실시간 조회
                self.logging.logger.debug("조회 성공여부 %s " % ok)

    # 나의 조건식에 해당하는 종목코드 받기
    def condition_tr_slot(self, sScrNo, strCodeList, strConditionName, index, nNext):
        self.logging.logger.debug("화면번호: %s, 종목코드 리스트: %s, 조건식 이름: %s, 조건식 인덱스: %s, 연속조회: %s" % (sScrNo, strCodeList, strConditionName, index, nNext))
        code_list = strCodeList.split(";")[:-1]
        self.logging.logger.debug("코드 종목 \n %s" % code_list)
        for code in code_list:
            if code not in self.condition_dict.keys():
                self.condition_dict.update({code: {}})
                self.condition_dict[code].update({'조건식': strConditionName, '인덱스': index, '검색시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                if code not in self.portfolio_stock_dict.keys():
                    self.portfolio_stock_dict.update({code: {}})
                self.req_real_che(code)

    def condition_real_slot(self, strCode, strType, strConditionName, strConditionIndex):
        self.logging.logger.debug("종목코드: %s, 이벤트종류: %s, 조건식이름: %s, 조건명인덱스: %s" % (strCode, strType, strConditionName, strConditionIndex))
        if strType == "I":
            if strCode not in self.condition_dict.keys():
                self.condition_dict.update({strCode: {}})
                self.condition_dict[strCode].update({'조건식': strConditionName, '인덱스': strConditionIndex, '검색시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                self.req_real_che(strCode)
                self.logging.logger.debug("[조건검색 종목추가] 종목코드: %s, 종목편입: %s" % (strCode, strType))
        elif strType == "D":
            if strCode in self.condition_dict.keys():
                self.condition_dict[strCode].update({'종목이탈시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            self.logging.logger.debug("[조건검색 종목이탈] 종목코드: %s, 종목이탈: %s" % (strCode, strType))

    # 실시간 체결 정보 요청
    def req_real_che(self, code):
        if code not in self.portfolio_stock_dict.keys():
            self.portfolio_stock_dict.update({code: {}})
        self.screen_number_setting()
        if None == self.portfolio_stock_dict[code]['스크린번호']:
            self.portfolio_stock_dict[code].update({"스크린번호": str(self.screen_real_stock)})
        screen_num = self.portfolio_stock_dict[code]['스크린번호']
        fids = self.realType.REALTYPE['주식체결']['체결시간']
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_num, code, fids, "1")
        self.logging.logger.debug("[실시간 체결 정보 요청] 종목코드: %s, 스크린번호: %s, FID: %s" % (code, screen_num, fids))
