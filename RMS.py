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

x_size = 200

form_class = uic.loadUiType('RMS.ui')[0]

# --------------------------------------------------------------
# [THREAD] RECEIVE from PLC (receive from PLC)
# --------------------------------------------------------------
class THREAD_RECEIVE_Data(QThread):
    intReady = pyqtSignal(float)

    @pyqtSlot()
    def __init__(self):
        super(THREAD_RECEIVE_Data, self).__init__()
        self.ks_34461a = keysight_34461a(sys.argv)

    def run(self):
        while True:
            read = self.ks_34461a.run()
            self.intReady.emit(read)


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

        self.data = np.linspace(-np.pi, np.pi, x_size)
        self.y1 = np.zeros(len(self.data))
        self.y2 = np.sin(self.data)

        # self.plot(self.data, self.y1)

        # Updating Plot
        self.p6 = self.graphWidget.addPlot(title="Res")
        self.curve = self.p6.plot(pen='y')
        self.p6.setGeometry(0, 0, x_size, 5)

        self.p6.setYRange(0, 1000, padding=0)
        # self.p6.setMinimumHeight(1)
        # self.p6.setMaximumHeight(-1)
        # self.data = np.random.normal(size=(10, 1000))
        self.ptr = 0

        self.graphWidget.nextRow()

        self.p7 = self.graphWidget.addPlot(title="Temp.")
        self.curve_2 = self.p7.plot(pen='y')

        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
        # self.timer.timeout.connect(self.update_func_1)
        self.timer.timeout.connect(self.plot)
        self.timer.start()

        self.counter = x_size

        # self.update_func_1()

        self.first_flag = 1

        self.thread_rcv_data = THREAD_RECEIVE_Data()
        self.thread_rcv_data.intReady.connect(self.update_func_2)
        self.thread_rcv_data.start()

    def update_func_2(self, msg):
        msg = msg/2

        if msg > 1000:
            msg = 1000


        print(msg)
        if self.first_flag == 1:
            self.y1 = np.full(len(self.data), msg)
            self.first_flag = 0

        # self.curve.setData(self.data[self.ptr % 10])
        self.y1 = np.roll(self.y1, -1)

        self.y1[-1] = msg

        self.curve.setData(self.y1)

        self.lcdNum_T_PV_CH1.display("{:.1f}".format(msg))

        if self.ptr == 0:
            self.p6.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
        self.ptr += 1

    def plot(self):
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

