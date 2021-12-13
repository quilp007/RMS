#!/usr/bin/env python
# coding=utf8

import os, sys, time, datetime, warnings, signal
from PyQt5.QtCore import QSize, QRect, QObject, pyqtSignal, QThread, pyqtSignal, pyqtSlot, Qt, QEvent, QTimer
from PyQt5.QtWidgets import QApplication, QComboBox, QDialog, QMainWindow, QWidget, QLabel, QTextEdit, QListWidget, QListView
from PyQt5.QtWidgets import QPushButton, QGridLayout, QLCDNumber
from PyQt5 import uic, QtTest, QtGui, QtCore

import numpy as np
import shelve
from keysight_34461a import keysight_34461a
from datetime import datetime
import pandas as pd
import pyqtgraph as pg

import time
import serial

TEST_DATA = True    # if read data from excel
# TEST_DATA = False # if read data from 34461a

if not TEST_DATA:
    us = serial.Serial('com4', 19200)

# AT Command for USB Temperature sensor
ATCZ = b'ATCZ\r\n'
ATCD = b'ATCD\r\n'
ATCMODEL = b'ATCMODEL\r\n'
ATCVER = b'ATCVER\r\n'
ATCC = b'ATCC\r\n'
ATCF = b'ATCF\r\n'
# AT Command for USB Temperature sensor

READ_DELAY = 0.01
ENABLE_BLANK_LINE = False

ERROR_REF = 0.05  # 5%
ERROR_LIMIT = 0.1   # 10%
PLOT_MIN_MAX = 0.15  # 15%

RES_REF = 33000

ERROR_UPPER = RES_REF + RES_REF * ERROR_REF     # + 5%
ERROR_LOWER = RES_REF - RES_REF * ERROR_REF     # - 5%

ERROR_LIMIT_UPPER = RES_REF + RES_REF * ERROR_LIMIT     # + 10%
ERROR_LIMIT_LOWER = RES_REF - RES_REF * ERROR_LIMIT     # - 10%

PLOT_UPPER = RES_REF + RES_REF * PLOT_MIN_MAX   # + 15%
PLOT_LOWER = RES_REF - RES_REF * PLOT_MIN_MAX   # - 15%

x_size = 200

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
            self.test_data = pd.read_excel('./test_data.xlsx')
            self.data_count = 1700
        else:
            self.ks_34461a = keysight_34461a(sys.argv)

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
                if self.data_count > 5000:
                    self.data_count = 1700

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


class qt(QMainWindow, form_class):
    def __init__(self):
        # QMainWindow.__init__(self)
        # uic.loadUiType('qt_test2.ui', self)[0]

        super().__init__()
        self.setupUi(self)
        # self.setWindowFlags(Qt.FramelessWindowHint)

        self.btn_main.clicked.connect(lambda: self.main_button_function(self.btn_main))
        self.btn_parameter.clicked.connect(lambda: self.main_button_function(self.btn_parameter))
        self.btn_alarm.clicked.connect(lambda: self.main_button_function(self.btn_alarm))
        self.btn_alarm_list.clicked.connect(lambda: self.main_button_function(self.btn_alarm_list))
        self.btn_logon.clicked.connect(lambda: self.main_button_function(self.btn_logon))

        self.btn_start.clicked.connect(lambda: self.btn_34461a(self.btn_start))
        self.btn_stop.clicked.connect(lambda: self.btn_34461a(self.btn_stop))
        self.btn_close.clicked.connect(lambda: self.btn_34461a(self.btn_close))

        self.data = np.linspace(-np.pi, np.pi, x_size)
        self.y1 = np.zeros(len(self.data))
        self.y2 = np.sin(self.data)

        # self.plot(self.data, self.y1)

        # Updating Plot
        self.p6 = self.graphWidget.addPlot(title="Res")
        self.curve = self.p6.plot(pen='g')
        self.p6.setGeometry(0, 0, x_size, 5)

        self.p6.setYRange(PLOT_UPPER, PLOT_LOWER, padding=0)
        # self.p6.setMinimumHeight(1)
        # self.p6.setMaximumHeight(-1)
        # self.data = np.random.normal(size=(10, 1000))
        self.ptr = 0

        ERROR_LOWER_line = pg.InfiniteLine(angle=0, movable=True, pen='y')
        ERROR_LOWER_line.setValue(ERROR_LOWER)
        self.p6.addItem(ERROR_LOWER_line, ignoreBounds=True)

        ERROR_UPPER_line = pg.InfiniteLine(angle=0, movable=True, pen='y')
        ERROR_UPPER_line.setValue(ERROR_UPPER)
        self.p6.addItem(ERROR_UPPER_line, ignoreBounds=True)

        ERROR_LIMIT_LOWER_line = pg.InfiniteLine(angle=0, movable=True, pen='r')
        ERROR_LIMIT_LOWER_line.setValue(ERROR_LIMIT_LOWER)
        self.p6.addItem(ERROR_LIMIT_LOWER_line, ignoreBounds=True)

        ERROR_LIMIT_UPPER_line = pg.InfiniteLine(angle=0, movable=True, pen='r')
        ERROR_LIMIT_UPPER_line.setValue(ERROR_LIMIT_UPPER)
        self.p6.addItem(ERROR_LIMIT_UPPER_line, ignoreBounds=True)

        # self.graphWidget.nextRow()

        self.p7 = self.graphWidget_2.addPlot(title="Temp.")
        self.curve_2 = self.p7.plot(pen='y')

        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
        # self.timer.timeout.connect(self.update_func_1)
        if TEST_DATA:
            self.timer.timeout.connect(self.sine_plot)
        else:
            self.timer.timeout.connect(self.usb_temp_plot)

        self.timer.start()

        if TEST_DATA:
            self.counter = x_size

        self.first_flag = 1

        self.thread_rcv_data = THREAD_RECEIVE_Data()
        self.thread_rcv_data.intReady.connect(self.update_func_2)
        self.thread_rcv_data.to_excel.connect(self.to_excel_func)
        self.thread_rcv_data.start()

        self.resist_data = []
        # self.writer = pd.ExcelWriter('./data.xlsx')

        self.prev_data = 0
        self.data_list = []

        self.log_flag = False

    def to_excel_func(self, _time, data):
        tt = [_time, data]
        self.resist_data.append(tt)
        print(tt)

    def update_func_2(self, msg):
        if msg > ERROR_LIMIT_UPPER:
            msg = ERROR_LIMIT_UPPER
        elif msg < ERROR_LIMIT_LOWER:
            msg = ERROR_LIMIT_LOWER

        print(msg)

        if msg != ERROR_LIMIT_UPPER:
            self.data_list.append(msg)
            self.prev_data = msg
            return
        elif self.prev_data != ERROR_LIMIT_UPPER:
            mean_data = np.mean(self.data_list)
            self.data_list = []
            print('mean: ', mean_data)
            self.prev_data = msg
            msg = mean_data
        elif (self.prev_data == ERROR_LIMIT_UPPER and msg == ERROR_LIMIT_UPPER) and not ENABLE_BLANK_LINE:
            return

        if self.first_flag == 1:
            self.y1 = np.full(len(self.data), msg)
            self.first_flag = 0

        # self.curve.setData(self.data[self.ptr % 10])
        self.y1 = np.roll(self.y1, -1)

        self.y1[-1] = msg

        self.curve.setData(self.y1)

        msg = msg / 1000;   # convert k ohm
        self.lcdNum_T_PV_CH1.display("{:.2f}".format(msg))

        if self.ptr == 0:
            self.p6.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
        self.ptr += 1

    def sine_plot(self):
        # self.g_plotWidget.plot(hour, temperature)
        # curve = self.graphWidget_2.plot(pen='y')
        self.y2 = np.roll(self.y2, -1)
        self.y2[-1] = np.sin(self.data[self.counter % x_size])
        self.curve_2.setData(self.y2)

        mean_value = 10 + np.round(self.y2[-1], 1)/10
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

            with pd.ExcelWriter(_time+'.xlsx') as writer:
                df1.to_excel(writer, _time+'.xlsx')

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

