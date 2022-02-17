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
# table row number
ROW_COUNT = 30  # limit: 30
ROW_COUNT_2 = 3  # limit: 3

V_input = 12.009

# graph x size
mean_plot_x_size = 100  # graph's x size
x_size = 200  # graph's x size

# use global variable!!!!!!!!!!!!!!!
USE_GLOBAL_VARIABLE = False
# USE_GLOBAL_VARIABLE = True

LINE_NUM = 16  # thermal film line

# RES_REF = 33000
# RES_REF = 5000
# RES_REF = 14000
# P_RES_REF = 875

RES_REF = 33000
P_RES_REF = 875

P_ERROR_REF = 0.05  # 5%
P_ERROR_LIMIT = 0.125  # 12.5%
P_PLOT_MIN_MAX = 0.15  # 15%

ERROR_REF = 0.05  # 5%
# ERROR_LIMIT = 0.1     # 10%
ERROR_LIMIT = 0.125  # 12.5%
PLOT_MIN_MAX = 0.15  # 15%

# config for keysight 34461a
display = True  # 34461a display On(True)/Off(False)
DMM_RES_RANGE = 100000  # 34461a range (ohm, not k ohm)
DMM_RESOLUTION = 2
COM_PORT = 'com4'

# READ_DELAY = 0.01
READ_DELAY = 0.005
ENABLE_BLANK_LINE = False
BLANK_DATA_COUNT = 20
# ------------------------------------------------------------------------------

# TEST_DATA = True  # if read data from excel
TEST_DATA = False # if read data from 34461a

# if not TEST_DATA:
#     us = serial.Serial(COM_PORT, 19200)

# AT Command for USB Temperature sensor
ATCZ = b'ATCZ\r\n'
ATCD = b'ATCD\r\n'
ATCMODEL = b'ATCMODEL\r\n'
ATCVER = b'ATCVER\r\n'
ATCC = b'ATCC\r\n'
ATCF = b'ATCF\r\n'
# AT Command for USB Temperature sensor

# P_ERROR_UPPER = P_RES_REF + P_RES_REF * P_ERROR_REF  # + 5%
# P_ERROR_LOWER = P_RES_REF - P_RES_REF * P_ERROR_REF  # - 5%
#
# P_ERROR_LIMIT_UPPER = P_RES_REF + P_RES_REF * P_ERROR_LIMIT  # + 10%
# P_ERROR_LIMIT_LOWER = P_RES_REF - P_RES_REF * P_ERROR_LIMIT  # - 10%
#
# P_PLOT_UPPER = P_RES_REF + P_RES_REF * P_PLOT_MIN_MAX  # + 15%
# P_PLOT_LOWER = P_RES_REF - P_RES_REF * P_PLOT_MIN_MAX  # - 15%
#
# ERROR_UPPER = RES_REF + RES_REF * ERROR_REF  # + 5%
# ERROR_LOWER = RES_REF - RES_REF * ERROR_REF  # - 5%
#
# ERROR_LIMIT_UPPER = RES_REF + RES_REF * ERROR_LIMIT  # + 10%
# ERROR_LIMIT_LOWER = RES_REF - RES_REF * ERROR_LIMIT  # - 10%
#
# PLOT_UPPER = RES_REF + RES_REF * PLOT_MIN_MAX  # + 15%
# PLOT_LOWER = RES_REF - RES_REF * PLOT_MIN_MAX  # - 15%

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

            # self.test_data = pd.read_excel('./data/20211216_170442.xlsx')
            # self.data_count = 580
            # self.data_count_end = 18700

            self.test_data = pd.read_excel('./data/20211223_154032.xlsx')
            self.data_count_start = 11000
            # self.data_count_start = 3400
            self.data_count_end = 17400

            self.data_count = self.data_count_start
        else:
            # self.ks_34461a = keysight_34461a(sys.argv)
            self.ks_34461a = keysight_34461a(DMM_RES_RANGE, display, DMM_RESOLUTION)

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
                if self.data_count > self.data_count_end:  # 5000:
                    self.data_count = self.data_count_start # 1700

                time.sleep(READ_DELAY)
            else:
                read = self.ks_34461a.read()
                read = V_input / read
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

        self.res_ref = self.p_res_ref = self.line_num = 0
        self.p_error_ref = self.p_error_limit = self.p_plot_min_max = 0
        self.error_ref = self.error_limit = self.plot_min_max = 0
        self.p_error_upper = self.p_error_lower = 0
        self.p_error_limit_upper = self.p_error_limit_lower = 0
        self.p_plot_upper = self.p_plot_lower = 0
        self.error_upper = self.error_lower = 0
        self.error_limit_upper = self.error_limit_lower = 0
        self.plot_upper = self.plot_lower = 0

        self.loadParam()
        self.setParam()

        # lcdNum click event connect to function
        self.clickable(self.lcdNum_line_num).connect(lambda: self.input_lcdNum(self.lcdNum_line_num))
        self.clickable(self.lcdNum_r_ref).connect(lambda: self.input_lcdNum(self.lcdNum_r_ref))         # k ohm
        self.clickable(self.lcdNum_p_r_ref).connect(lambda: self.input_lcdNum(self.lcdNum_p_r_ref))
        self.clickable(self.lcdNum_error_ref).connect(lambda: self.input_lcdNum(self.lcdNum_error_ref))
        self.clickable(self.lcdNum_error_limit).connect(lambda: self.input_lcdNum(self.lcdNum_error_limit))
        self.clickable(self.lcdNum_dmm_r_range).connect(lambda: self.input_lcdNum(self.lcdNum_dmm_r_range))
        self.clickable(self.lcdNum_dmm_resolution).connect(lambda: self.input_lcdNum(self.lcdNum_dmm_resolution))
        self.clickable(self.label_mode).connect(self.mode_change)

        self.btn_main.clicked.connect(lambda: self.main_button_function(self.btn_main))
        self.btn_parameter.clicked.connect(lambda: self.main_button_function(self.btn_parameter))
        self.btn_alarm.clicked.connect(lambda: self.main_button_function(self.btn_alarm))
        self.btn_alarm_list.clicked.connect(lambda: self.main_button_function(self.btn_alarm_list))

        self.btn_start.clicked.connect(lambda: self.btn_34461a(self.btn_start))
        self.btn_stop.clicked.connect(lambda: self.btn_34461a(self.btn_stop))
        self.btn_close.clicked.connect(lambda: self.btn_34461a(self.btn_close))

        self.data = np.linspace(-np.pi, np.pi, x_size)
        self.y1_1 = np.zeros(len(self.data))
        self.y1_2 = np.zeros(len(self.data))
        # self.y2_1 = np.sin(self.data)
        self.y2_1 = np.zeros(mean_plot_x_size)
        self.y2_2 = np.zeros(mean_plot_x_size)

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

        # table Widget 3-----------------------------------------------------------------
        self.tableWidget_3.setRowCount(5)
        self.tableWidget_3.setColumnCount(1)
        # self.tableWidget_2.setColumnWidth(0, self.tableWidget.columnWidth()/10)
        self.tableWidget_3.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget_3.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.tableWidget_3.setHorizontalHeaderItem(LINE_NUM, QTableWidgetItem('MEAN'))
        # self.tableWidget_3.setHorizontalHeaderItem(LINE_NUM + 1, QTableWidgetItem('1S. P. RES'))
        # self.tableWidget_3.setHorizontalHeaderItem(LINE_NUM + 2, QTableWidgetItem('2S. P. RES'))

        # Updating Plot
        self.p6 = self.graphWidget_2.addPlot(title="Res")
        self.curve1_1 = self.p6.plot(pen='g')
        self.curve1_2 = self.p6.plot(pen='r')
        self.p6.setGeometry(0, 0, x_size, 5)

        self.p6.setYRange(self.plot_upper, self.plot_lower, padding=0)

        self.drawLine(self.p6, self.error_lower, 'y')
        self.drawLine(self.p6, self.error_upper, 'y')
        self.drawLine(self.p6, self.error_limit_lower, 'r')
        self.drawLine(self.p6, self.error_limit_upper, 'r')

        # self.graphWidget.nextRow()

        self.p7 = self.graphWidget.addPlot(title="Temp.")
        self.curve2_1 = self.p7.plot(pen='y')
        self.curve2_2 = self.p7.plot(pen='r')

        self.p7.setYRange(self.p_plot_upper, self.p_plot_lower, padding=0)

        self.drawLine(self.p7, self.p_error_lower, 'y')
        self.drawLine(self.p7, self.p_error_upper, 'y')
        self.drawLine(self.p7, self.p_error_limit_lower, 'r')
        self.drawLine(self.p7, self.p_error_limit_upper, 'r')

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

        self.prev_data = self.error_limit_upper
        self.data_list = []
        self.blank_count = 0
        self.line_data = []

        self.log_flag = False
        self.sheet_blank_flag = False

        self.prev_1s_p_res = 0

        self.measure_mode = True    # resistance mode

        self.main_button_function(self.btn_main)

    def setParam(self):
        self.res_ref = RES_REF
        self.p_res_ref = P_RES_REF
        self.line_num = LINE_NUM

        self.p_error_ref = P_ERROR_REF
        self.p_error_limit = P_ERROR_LIMIT
        self.p_plot_min_max = P_PLOT_MIN_MAX

        self.error_ref = ERROR_REF
        self.error_limit = ERROR_LIMIT
        self.plot_min_max = PLOT_MIN_MAX

        self.p_error_upper = self.p_res_ref + self.p_res_ref * self.p_error_ref  # + 5%
        self.p_error_lower = self.p_res_ref - self.p_res_ref * self.p_error_ref  # - 5%

        self.p_error_limit_upper = self.p_res_ref + self.p_res_ref * self.p_error_limit  # + 10%
        self.p_error_limit_lower = self.p_res_ref - self.p_res_ref * self.p_error_limit  # - 10%

        self.p_plot_upper = self.p_res_ref + self.p_res_ref * self.p_plot_min_max  # + 15%
        self.p_plot_lower = self.p_res_ref - self.p_res_ref * self.p_plot_min_max  # - 15%

        self.error_upper = self.res_ref + self.res_ref * self.error_ref  # + 5%
        self.error_lower = self.res_ref - self.res_ref * self.error_ref  # - 5%

        self.error_limit_upper = self.res_ref + self.res_ref * self.error_limit  # + 10%
        self.error_limit_lower = self.res_ref - self.res_ref * self.error_limit  # - 10%

        self.plot_upper = self.res_ref + self.res_ref * self.plot_min_max  # + 15%
        self.plot_lower = self.res_ref - self.res_ref * self.plot_min_max  # - 15%

    def loadParam(self):
        global RES_REF, LINE_NUM, P_RES_REF, ERROR_REF, ERROR_LIMIT, P_ERROR_REF, P_ERROR_LIMIT, DMM_RES_RANGE, DMM_RESOLUTION
        if not USE_GLOBAL_VARIABLE:
            try:
                with shelve.open('config') as f:
                    LINE_NUM = int(f['line_num'])
                    RES_REF = int(f['r_ref'])*1000
                    P_RES_REF = int(f['p_r_ref'])
                    ERROR_REF = int(f['error_ref'])/100     # 1st line
                    ERROR_LIMIT = int(f['error_limit'])/100 # 2nd line

                    P_ERROR_REF = ERROR_REF
                    P_ERROR_LIMIT = ERROR_LIMIT

                    DMM_RES_RANGE = int(f['dmm_r_range'])*1000
                    DMM_RESOLUTION = int(f['dmm_resolution'])
            except Exception as e:
                print('exception: ', e)

        self.lcdNum_line_num.display(LINE_NUM)
        self.lcdNum_r_ref.display(RES_REF/1000)
        self.lcdNum_p_r_ref.display(P_RES_REF)
        self.lcdNum_error_ref.display(ERROR_REF*100)
        self.lcdNum_error_limit.display(ERROR_LIMIT*100)
        self.lcdNum_dmm_r_range.display(DMM_RES_RANGE/1000)
        self.lcdNum_dmm_resolution.display(DMM_RESOLUTION)

    def clickable(self, widget):
        class Filter(QObject):
            clicked = pyqtSignal()  # pyside2 사용자는 pyqtSignal() -> Signal()로 변경

            def eventFilter(self, obj, event):

                if obj == widget:
                    if event.type() == QEvent.MouseButtonRelease:
                        if obj.rect().contains(event.pos()):
                            self.clicked.emit()
                            # The developer can opt for .emit(obj) to get the object within the slot.
                            return True
                return False
        filter = Filter(widget)
        widget.installEventFilter(filter)
        return filter.clicked

    def save_var(self, key, value):
        with shelve.open('config') as f:
            f[key] = value

    def mode_change(self):
        item = ('Resistance', 'Current')
        text, ok = QInputDialog.getItem(self, 'MODE', 'select Mode', item, 0, False)
        if ok:
            if text == 'Resistance':
                self.measure_mode = True
            else:
                self.measure_mode = False

            self.label_mode.setText(text)

    def input_lcdNum(self, lcdNum):
        global LINE_NUM, ERROR_REF, ERROR_LIMIT, RES_REF, P_RES_REF, DMM_RES_RANGE, DMM_RESOLUTION
        # item = ('16, '17', '18')
        # text, ok = QInputDialog.getItem(self, 'input', 'select input', item, 0, False)
        # text, ok = QInputDialog.getint(self, 'input', 'input number')
        text, ok = QInputDialog.getInt(self, 'input', 'input number')
        if ok:
            if lcdNum == self.lcdNum_line_num:
                LINE_NUM = text
                self.save_var('line_num', text)
            elif lcdNum == self.lcdNum_r_ref:
                RES_REF = text
                self.save_var('r_ref', text)
            elif lcdNum == self.lcdNum_p_r_ref:
                RES_REF = text
                self.save_var('p_r_ref', text)
            elif lcdNum == self.lcdNum_error_ref:
                ERROR_REF = text
                self.save_var('error_ref', text)
            elif lcdNum == self.lcdNum_error_limit:
                ERROR_LIMIT = text
                self.save_var('error_limit', text)
            elif lcdNum == self.lcdNum_dmm_r_range:
                DMM_RES_RANGE = text
                self.save_var('dmm_r_range', text)
            elif lcdNum == self.lcdNum_dmm_resolution:
                DMM_RESOLUTION = text
                self.save_var('dmm_resolution', text)

            lcdNum.display(text)

    def drawLine(self, plot_name, val, color):
        line = pg.InfiniteLine(angle=0, movable=True, pen=color)
        line.setValue(val)
        plot_name.addItem(line, ignoreBounds=True)

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
        if msg > self.error_limit_upper:
            msg = self.error_limit_upper
        elif msg < self.error_limit_lower:
            msg = self.error_limit_lower

        print('34661A: ', msg)

        # data filter
        if msg != self.error_limit_upper:                # line data received
            self.blank_count = 0
            self.data_list.append(msg)
            self.prev_data = msg

            self.tableWidget_3.removeRow(5 - 1)
            self.tableWidget_3.insertRow(0)
            self.setTableWidgetData(self.data_list[-1:], self.tableWidget_3)
            return

        elif self.prev_data != self.error_limit_upper:   # blank area

            # self.tableWidget_3.removeRow(5 - 1)
            # self.tableWidget_3.insertRow(0)
            # self.setTableWidgetData(np.round(np.divide(self.data_list, 1000), 1), self.tableWidget_3)

            mean_data = np.mean(self.data_list)
            self.data_list = []
            print('mean: ', mean_data)
            self.prev_data = msg
            msg = mean_data
            mean_data = mean_data.round(2)
            self.line_data.append(mean_data)
        elif (self.prev_data == self.error_limit_upper and msg == self.error_limit_upper) and not ENABLE_BLANK_LINE:
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
                print('p res: ', p_r_sum)
                self.lcdNum_1sheet_p_res.display(str(np.round(p_r_sum/1000, 1)))
                two_s_p_res = (self.prev_1s_p_res + p_r_sum) / 2
                self.lcdNum_2sheets_p_res.display(str(np.round(two_s_p_res / 1000, 1)))
                # self.line_data.append(p_r_sum.round(2))
                self.line_data.append(0)
                self.line_data.append(0)
                self.line_data[LINE_NUM + 1] = p_r_sum.round(2)
                self.line_data[LINE_NUM + 2] = two_s_p_res.round(2)
                # self.line_data.append(p_r_sum.round(2))
                # self.line_data.append(two_s_p_res.round(2))
                self.prev_1s_p_res = p_r_sum

                print(self.line_data, ' length: ', len(self.line_data))
                self.tableWidget.removeRow(ROW_COUNT - 1)
                self.tableWidget.insertRow(0)
                self.setTableWidgetData(self.line_data, self.tableWidget)

                self.tableWidget_2.removeRow(ROW_COUNT_2 - 1)
                self.tableWidget_2.insertRow(0)
                self.setTableWidgetData(self.line_data, self.tableWidget_2)

                self.line_data = []
                self.blank_count = 0

                self.mean_value_plot(p_r_sum, two_s_p_res)

        # self.y1_1 = np.roll(self.y1_1, -1)

        # self.y1_1[-1] = msg
        # self.curve1_1.setData(self.y1_1)

        if ptr == 0:
            self.y1_1 = self.y1_2[:]
            self.curve1_1.setData(self.y1_1)
            # self.y1_2 = np.zeros(x_size)
            self.y1_2 = np.zeros(x_size)
            self.y1_2[:] = self.error_limit_upper

        self.y1_2[ptr] = msg
        ptr += 1
        self.curve1_2.setData(self.y1_2)

        if msg != self.error_limit_upper:
            msg = msg / 1000  # convert k ohm
            self.lcdNum_T_PV_CH1.display("{:.2f}".format(msg))

    def setTableWidgetData(self, line_data, tableWidget):
        for idx in range(0, LINE_NUM + 3):
            tableWidget.setItem(0, idx, QTableWidgetItem(str(line_data[idx])))

        # self.tableWidget.setItem(0, LINE_NUM, QTableWidgetItem(str(line_data[-1])))

    def mean_value_plot(self, mean_value, two_sheets_p_res):
        # self.g_plotWidget.plot(hour, temperature)
        # curve = self.graphWidget_2.plot(pen='y')
        self.y2_1 = np.roll(self.y2_1, -1)
        self.y2_1[-1] = mean_value
        self.curve2_1.setData(self.y2_1)

        self.y2_2 = np.roll(self.y2_2, -1)
        self.y2_2[-1] = two_sheets_p_res
        self.curve2_2.setData(self.y2_2)

    def sine_plot(self):
        # self.g_plotWidget.plot(hour, temperature)
        # curve = self.graphWidget_2.plot(pen='y')
        self.y2_1 = np.roll(self.y2_1, -1)
        self.y2_1[-1] = np.sin(self.data[self.counter % x_size])
        self.curve2_1.setData(self.y2_1)

        mean_value = 10 + np.round(self.y2_1[-1], 1) / 10
        if self.counter % 50 == 0:
            self.lcdNum_T_SV_CH1.display("{:.1f}".format(mean_value))
        # print('y2_1: ', mean_value)

        self.counter += 1

    def usb_temp_plot(self):
        us.write(b'ATCD\r\n')
        line = us.readline().decode('utf-8')
        # print(line)

        self.y2_1 = np.roll(self.y2_1, -1)

        temp_data = line.split(' ')[1].split(',')[0]
        temp_data = float(temp_data)
        self.y2_1[-1] = temp_data
        self.curve_2.setData(self.y2_1)

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
