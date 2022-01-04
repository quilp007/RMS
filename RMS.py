#!/usr/bin/env python
# coding=utf8

import os, sys, time, datetime, warnings, signal
from PyQt5.QtCore import QSize, QRect, QObject, pyqtSignal, QThread, pyqtSignal, pyqtSlot, Qt, QEvent, QTimer
from PyQt5.QtWidgets import QApplication, QComboBox, QDialog, QMainWindow, QWidget, QLabel, QTextEdit, QListWidget, \
    QListView
from PyQt5.QtWidgets import QPushButton, QGridLayout, QLCDNumber
from PyQt5.QtWidgets import *
from PyQt5 import uic, QtTest, QtGui, QtCore

import numpy as np
import shelve
from keysight_34461a import keysight_34461a
from datetime import datetime
import pandas as pd
import pyqtgraph as pg

import time
import serial

# ------------------------------------------------------------------------------
# config -----------------------------------------------------------------------
# ------------------------------------------------------------------------------

# RES_REF = 33000
RES_REF = 5000
P_RES_REF = 310

LINE_NUM = 16  # thermal film line
ROW_COUNT = 30  # limit: 30
ROW_COUNT_2 = 3  # limit: 3

P_ERROR_REF = 0.05  # 5%
P_ERROR_LIMIT = 0.125  # 12.5%
P_PLOT_MIN_MAX = 0.15  # 15%

ERROR_REF = 0.05  # 5%
# ERROR_LIMIT = 0.1     # 10%
ERROR_LIMIT = 0.125  # 12.5%
PLOT_MIN_MAX = 0.15  # 15%

mean_plot_x_size = 100  # graph's x size
x_size = 200  # graph's x size

# config for keysight 34461a
display = True  # 34461a display On(True)/Off(False)
res_range = 100000  # 34461a range (ohm, not k ohm)
COM_PORT = 'com4'

# READ_DELAY = 0.01
READ_DELAY = 0.005
ENABLE_BLANK_LINE = False
BLANK_DATA_COUNT = 20
# ------------------------------------------------------------------------------

TEST_DATA = True  # if read data from excel
# TEST_DATA = False # if read data from 34461a

if not TEST_DATA:
    us = serial.Serial(COM_PORT, 19200)

# AT Command for USB Temperature sensor
ATCZ = b'ATCZ\r\n'
ATCD = b'ATCD\r\n'
ATCMODEL = b'ATCMODEL\r\n'
ATCVER = b'ATCVER\r\n'
ATCC = b'ATCC\r\n'
ATCF = b'ATCF\r\n'
# AT Command for USB Temperature sensor

P_ERROR_UPPER = P_RES_REF + P_RES_REF * P_ERROR_REF  # + 5%
P_ERROR_LOWER = P_RES_REF - P_RES_REF * P_ERROR_REF  # - 5%

P_ERROR_LIMIT_UPPER = P_RES_REF + P_RES_REF * P_ERROR_LIMIT  # + 10%
P_ERROR_LIMIT_LOWER = P_RES_REF - P_RES_REF * P_ERROR_LIMIT  # - 10%

P_PLOT_UPPER = P_RES_REF + P_RES_REF * P_PLOT_MIN_MAX  # + 15%
P_PLOT_LOWER = P_RES_REF - P_RES_REF * P_PLOT_MIN_MAX  # - 15%


ERROR_UPPER = RES_REF + RES_REF * ERROR_REF  # + 5%
ERROR_LOWER = RES_REF - RES_REF * ERROR_REF  # - 5%

ERROR_LIMIT_UPPER = RES_REF + RES_REF * ERROR_LIMIT  # + 10%
ERROR_LIMIT_LOWER = RES_REF - RES_REF * ERROR_LIMIT  # - 10%

PLOT_UPPER = RES_REF + RES_REF * PLOT_MIN_MAX  # + 15%
PLOT_LOWER = RES_REF - RES_REF * PLOT_MIN_MAX  # - 15%

form_class = uic.loadUiType('RMS.ui')[0]


# --------------------------------------------------------------
# [THREAD] RECEIVE from PLC (receive from PLC)
# --------------------------------------------------------------
class THREAD_RECEIVE_Data(QThread):
    intReady = pyqtSignal(float)
    to_excel = pyqtSignal(str, float)

    @pyqtSlot()
    def __init__(self):
        super(THREAD_RECEIVE_Data, self).__init__()
        self.time_format = '%Y%m%d_%H%M%S'

        if TEST_DATA:
            # self.test_data = pd.read_excel('./test_data.xlsx')
            # self.data_count = 1700
            self.test_data = pd.read_excel('./20211216_170442.xlsx')
            self.data_count = 580
        else:
            # self.ks_34461a = keysight_34461a(sys.argv)
            self.ks_34461a = keysight_34461a(res_range, display)

        self.__suspend = False
        self.__exit = False
        self.log_flag = False

    def run(self):
        while True:
            ### Suspend ###
            while self.__suspend:
                time.sleep(0.5)

            _time = datetime.now()
            _time = _time.strftime(self.time_format)

            if TEST_DATA:
                read = self.test_data[1][self.data_count]
                self.data_count += 1
                if self.data_count > 18700:  # 5000:
                    self.data_count = 580  # 1700

                time.sleep(READ_DELAY)
            else:
                read = self.ks_34461a.read()

            # read = RES_REF
            print(_time, ': ', read)

            # read = self.ks_34461a.run()
            self.intReady.emit(read)

            if self.log_flag:
                self.to_excel.emit(_time, read)

            ### Exit ###
            if self.__exit:
                break

    def mySuspend(self):
        self.__suspend = True

    def myResume(self):
        self.__suspend = False

    def myExit(self):
        self.__exit = True

    def close(self):
        self.mySuspend()
        time.sleep(0.1)
        self.ks_34461a.close()


ptr = 0
state = 0


class qt(QMainWindow, form_class):
    def __init__(self):
        # QMainWindow.__init__(self)
        # uic.loadUiType('qt_test2.ui', self)[0]

        super().__init__()
        self.setupUi(self)
        # self.setWindowFlags(Qt.FramelessWindowHint)

        # self.loadParam()
        # self.lcdNum_line_num.valueChanged.connect(lambda: self.setParam(self.lcdNum_line_num))

        self.btn_main.clicked.connect(lambda: self.main_button_function(self.btn_main))
        self.btn_parameter.clicked.connect(lambda: self.main_button_function(self.btn_parameter))
        self.btn_alarm.clicked.connect(lambda: self.main_button_function(self.btn_alarm))
        self.btn_alarm_list.clicked.connect(lambda: self.main_button_function(self.btn_alarm_list))
        # self.btn_logon.clicked.connect(lambda: self.main_button_function(self.btn_logon))

        self.btn_start.clicked.connect(lambda: self.btn_34461a(self.btn_start))
        self.btn_stop.clicked.connect(lambda: self.btn_34461a(self.btn_stop))
        self.btn_close.clicked.connect(lambda: self.btn_34461a(self.btn_close))

        self.data = np.linspace(-np.pi, np.pi, x_size)
        self.y1_1 = np.zeros(len(self.data))
        self.y1_2 = np.zeros(len(self.data))
        # self.y2 = np.sin(self.data)
        self.y2 = np.zeros(mean_plot_x_size)

        # self.plot(self.data, self.y1_1)

        # table Widget ------------------------------------------------------------------
        self.tableWidget.setRowCount(ROW_COUNT)
        self.tableWidget.setColumnCount(LINE_NUM + 3)  # MEAN, parallel resistance
        # self.tableWidget.setColumnWidth(0, self.tableWidget.columnWidth()/10)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.setHorizontalHeaderItem(LINE_NUM, QTableWidgetItem('MEAN'))
        self.tableWidget.setHorizontalHeaderItem(LINE_NUM + 1, QTableWidgetItem('1S. P. RES'))
        self.tableWidget.setHorizontalHeaderItem(LINE_NUM + 2, QTableWidgetItem('2S. P. RES'))

        # table Widget 2-----------------------------------------------------------------
        self.tableWidget_2.setRowCount(ROW_COUNT_2)
        self.tableWidget_2.setColumnCount(LINE_NUM + 3)  # MEAN, parallel resistance
        # self.tableWidget_2.setColumnWidth(0, self.tableWidget.columnWidth()/10)
        self.tableWidget_2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget_2.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget_2.setHorizontalHeaderItem(LINE_NUM, QTableWidgetItem('MEAN'))
        self.tableWidget_2.setHorizontalHeaderItem(LINE_NUM + 1, QTableWidgetItem('1S. P. RES'))
        self.tableWidget_2.setHorizontalHeaderItem(LINE_NUM + 2, QTableWidgetItem('2S. P. RES'))

        # Updating Plot
        self.p6 = self.graphWidget_2.addPlot(title="Res")
        self.curve1_1 = self.p6.plot(pen='g')
        self.curve1_2 = self.p6.plot(pen='r')
        self.p6.setGeometry(0, 0, x_size, 5)

        self.p6.setYRange(PLOT_UPPER, PLOT_LOWER, padding=0)

        self.drawLine(self.p6, ERROR_LOWER, 'y')
        self.drawLine(self.p6, ERROR_UPPER, 'y')
        self.drawLine(self.p6, ERROR_LIMIT_LOWER, 'r')
        self.drawLine(self.p6, ERROR_LIMIT_UPPER, 'r')

        # self.graphWidget.nextRow()

        self.p7 = self.graphWidget.addPlot(title="Temp.")
        self.curve2 = self.p7.plot(pen='y')

        self.p7.setYRange(P_PLOT_UPPER, P_PLOT_LOWER, padding=0)

        self.drawLine(self.p7, P_ERROR_LOWER, 'y')
        self.drawLine(self.p7, P_ERROR_UPPER, 'y')
        self.drawLine(self.p7, P_ERROR_LIMIT_LOWER, 'r')
        self.drawLine(self.p7, P_ERROR_LIMIT_UPPER, 'r')

        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
        # self.timer.timeout.connect(self.update_func_1)

        # if TEST_DATA:
        #     self.timer.timeout.connect(self.mean_value_plot)
        #     # self.timer.timeout.connect(self.sine_plot)
        # else:
        #     self.timer.timeout.connect(self.usb_temp_plot)

        self.timer.start()

        if TEST_DATA:
            self.counter = x_size

        self.first_flag = 1

        self.thread_rcv_data = THREAD_RECEIVE_Data()
        self.thread_rcv_data.intReady.connect(self.update_func_1)
        self.thread_rcv_data.to_excel.connect(self.to_excel_func)
        self.thread_rcv_data.start()

        self.resist_data = []
        # self.writer = pd.ExcelWriter('./data.xlsx')

        self.prev_data = ERROR_LIMIT_UPPER
        self.data_list = []
        self.blank_count = 0
        self.line_data = []

        self.log_flag = False
        self.sheet_blank_flag = False

        self.prev_1s_p_res = 0

        self.main_button_function(self.btn_main)

    def drawLine(self, plot_name, val, color):
        line = pg.InfiniteLine(angle=0, movable=True, pen=color)
        line.setValue(val)
        plot_name.addItem(line, ignoreBounds=True)

    def loadParam(self):
        global LINE_NUM
        with shelve.open('config') as f:
            try:
                LINE_NUM = f['LINE_NUM']
                self.lcdNum_line_num.display(LINE_NUM)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()

    def stParam(self, lcdNum):
        with shelve.open('config') as f:
            if lcdNum == self.lcdNum_line_num:
                f['LINE_NUM'] = self.lcdNum_line_num.value()

    def to_excel_func(self, _time, data):
        tt = [_time, data]
        self.resist_data.append(tt)
        print(tt)

    def update_func_1(self, msg):
        global ptr
        if msg > ERROR_LIMIT_UPPER:
            msg = ERROR_LIMIT_UPPER
        elif msg < ERROR_LIMIT_LOWER:
            msg = ERROR_LIMIT_LOWER

        print('34661A: ', msg)

        # data filter
        if msg != ERROR_LIMIT_UPPER:                # line data received
            self.blank_count = 0
            self.data_list.append(msg)
            self.prev_data = msg
            return
        elif self.prev_data != ERROR_LIMIT_UPPER:   # blank area
            mean_data = np.mean(self.data_list)
            self.data_list = []
            print('mean: ', mean_data)
            self.prev_data = msg
            msg = mean_data
            mean_data = mean_data.round(2)
            self.line_data.append(mean_data)
        elif (self.prev_data == ERROR_LIMIT_UPPER and msg == ERROR_LIMIT_UPPER) and not ENABLE_BLANK_LINE:
            self.blank_count += 1
            # if self.blank_count > 20:
            if self.blank_count > BLANK_DATA_COUNT:
                ptr = 0
                p_r_sum = 0
                mean_value = np.nanmean(self.line_data).round(2)
                # self.line_data.append(np.nanmean(self.line_data).round(2))
                self.line_data.append(mean_value)
                self.lcdNum_line_res.display(str(np.round(mean_value/1000, 1)))

                # parallel resist
                for idx in range(LINE_NUM):
                    p_r_sum += (1 / self.line_data[idx])

                p_r_sum = (1 / p_r_sum)
                self.lcdNum_1sheet_p_res.display(str(np.round(p_r_sum/1000, 1)))
                two_s_p_res = (self.prev_1s_p_res + p_r_sum) /2
                # self.line_data.append(p_r_sum.round(2))
                self.line_data[LINE_NUM + 1] = p_r_sum.round(2)
                self.line_data[LINE_NUM + 2] = two_s_p_res.round(2)

                print(self.line_data, ' length: ', len(self.line_data))
                self.tableWidget.removeRow(ROW_COUNT - 1)
                self.tableWidget.insertRow(0)
                self.setTableWidgetData(self.line_data, self.tableWidget)

                self.tableWidget_2.removeRow(ROW_COUNT_2 - 1)
                self.tableWidget_2.insertRow(0)
                self.setTableWidgetData(self.line_data, self.tableWidget_2)

                self.line_data = []
                self.blank_count = 0

                self.mean_value_plot(p_r_sum)

        # self.y1_1 = np.roll(self.y1_1, -1)

        # self.y1_1[-1] = msg
        # self.curve1_1.setData(self.y1_1)

        if ptr == 0:
            self.y1_1 = self.y1_2[:]
            self.curve1_1.setData(self.y1_1)
            # self.y1_2 = np.zeros(x_size)
            self.y1_2 = np.zeros(x_size)
            self.y1_2[:] = ERROR_LIMIT_UPPER

        self.y1_2[ptr] = msg
        ptr += 1
        self.curve1_2.setData(self.y1_2)

        if msg != ERROR_LIMIT_UPPER:
            msg = msg / 1000  # convert k ohm
            self.lcdNum_T_PV_CH1.display("{:.2f}".format(msg))

    def setTableWidgetData(self, line_data, tableWidget):
        for idx in range(0, LINE_NUM + 2):
            tableWidget.setItem(0, idx, QTableWidgetItem(str(line_data[idx])))

        # self.tableWidget.setItem(0, LINE_NUM, QTableWidgetItem(str(line_data[-1])))

    def mean_value_plot(self, mean_value):
        # self.g_plotWidget.plot(hour, temperature)
        # curve = self.graphWidget_2.plot(pen='y')
        self.y2 = np.roll(self.y2, -1)
        self.y2[-1] = mean_value
        self.curve2.setData(self.y2)

    def sine_plot(self):
        # self.g_plotWidget.plot(hour, temperature)
        # curve = self.graphWidget_2.plot(pen='y')
        self.y2 = np.roll(self.y2, -1)
        self.y2[-1] = np.sin(self.data[self.counter % x_size])
        self.curve2.setData(self.y2)

        mean_value = 10 + np.round(self.y2[-1], 1) / 10
        if self.counter % 50 == 0:
            self.lcdNum_T_SV_CH1.display("{:.1f}".format(mean_value))
        # print('y2: ', mean_value)

        self.counter += 1

    def usb_temp_plot(self):
        us.write(b'ATCD\r\n')
        line = us.readline().decode('utf-8')
        # print(line)

        self.y2 = np.roll(self.y2, -1)

        temp_data = line.split(' ')[1].split(',')[0]
        temp_data = float(temp_data)
        self.y2[-1] = temp_data
        self.curve_2.setData(self.y2)

        self.lcdNum_T_SV_CH1.display("{:.1f}".format(temp_data))

    def btn_34461a(self, button):
        if button == self.btn_start:
            self.thread_rcv_data.myResume()
            self.thread_rcv_data.log_flag = True
        elif button == self.btn_stop:
            self.thread_rcv_data.log_flag = False
            # self.thread_rcv_data.mySuspend()
            df1 = pd.DataFrame(self.resist_data)
            _time = datetime.now()
            _time = _time.strftime(self.thread_rcv_data.time_format)

            with pd.ExcelWriter(_time + '.xlsx') as writer:
                df1.to_excel(writer, _time + '.xlsx')

            self.resist_data = []

        elif button == self.btn_close:
            self.thread_rcv_data.close()

    # button setting for MAIN PAGE CHANGE
    def main_button_function(self, button):
        global gLogon

        self.btn_main.setStyleSheet("background-color: #dedede; border: 0px")
        self.btn_parameter.setStyleSheet("background-color: #dedede; border: 0px")
        self.btn_alarm.setStyleSheet("background-color: #dedede; border: 0px")
        self.btn_alarm_list.setStyleSheet("background-color: #dedede; border: 0px")

        if button == self.btn_main:
            self.stackedWidget.setCurrentWidget(self.sw_MAIN)
            self.btn_main.setStyleSheet("background-color: lime; border: 0px")
        elif button == self.btn_parameter:
            self.stackedWidget.setCurrentWidget(self.sw_PARAMETER)
            self.btn_parameter.setStyleSheet("background-color: lime; border: 0px")
        elif button == self.btn_alarm:
            self.stackedWidget.setCurrentWidget(self.sw_ALARM)
            self.btn_alarm.setStyleSheet("background-color: lime; border: 0px")
        elif button == self.btn_alarm_list:
            self.stackedWidget.setCurrentWidget(self.sw_ALARM_LIST)
            self.btn_alarm_list.setStyleSheet("background-color: lime; border: 0px")
        # elif button == self.btn_logon:
        #     if gLogon == True:
        #         # self.Logoff_func()
        #     else:
        #         # self.stackedWidget.setCurrentWidget(self.sw_LOGON)


def run():
    app = QApplication(sys.argv)
    widget = qt()
    widget.show()
    # widget.update_func_1()

    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
