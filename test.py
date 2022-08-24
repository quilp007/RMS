import serial
import numpy as np

import threading, requests, time

# 0x9C42 -> Object temperature
# TEMP_CMD_READ_TEMP = [0x01, 0x03, 0x9c, 0x42, 0x00, 0x01, 0x0a, 0x4e] # 0x4e0a -> [0x0a, 0x4e]

COM_PORT = '/dev/ttyUSB0'
us = serial.Serial(COM_PORT, 19200, timeout=1000)
print(us)
# tx_get_temp = bytearray(b'\x01\x03\x9c\x42\x00\x01\x0a\x4e')
tx_get_temp = b'\x01\x03\x9c\x42\x00\x01\x0a\x4e'


class THREAD_TX_Data(threading.Thread):
    def __init__(self):
        super(THREAD_TX_Data, self).__init__()


        self.__suspend = False
        self.__exit = False
        self.log_flag = False

    def run(self):
        while True:
            ### Suspend ###
            while self.__suspend:
                time.sleep(0.5)

            us.write(tx_get_temp)
            # print('send data: ', tx_get_temp)

            time.sleep(0.1)

            line = us.read(7)
            data = line[3:5]
            temp = int(data[0]) << 8 | int(data[1])
            print('decimal: ', temp/10)

            time.sleep(0.5)

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


class THREAD_RX_Data(threading.Thread):
    def __init__(self):
        super(THREAD_RX_Data, self).__init__()


        self.__suspend = False
        self.__exit = False
        self.log_flag = False

    def run(self):
        data = []
        state = 0
        while True:
            ### Suspend ###
            while self.__suspend:
                time.sleep(0.5)

            # line = us.readline()
            line = us.read(7)
            data = line[3:5]
            temp = int(data[0]) << 8 | int(data[1])
            print('decimal: ', temp/10)

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


def run():

    thread_send_data = THREAD_TX_Data()
    thread_send_data.start()

    thread_rcv_data = THREAD_RX_Data()
#     thread_rcv_data.start()


if __name__ == "__main__":
    run()

