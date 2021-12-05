import sys

import pyvisa as visa
import time
from datetime import datetime

# start of untitled


class keysight_34461a:
    def __init__(self, param):
        _state = False
        _range = 10000
        _resolution = 0.2

        # VISA_ADDRESS = 'TCPIP::A-34461A-00000.local::inst0::INSTR'
        _VISA_ADDRESS = 'USB0::0x2A8D::0x1401::MY60020026::0::INSTR'

        self.rm = visa.ResourceManager()
        self.v34461A = self.rm.open_resource(_VISA_ADDRESS)
        self.v34461A.write(':CONFigure:RESistance %G,%G' % (_range, _resolution))
        self.v34461A.write(':DISPlay:STATe %d' % (_state))

        self.time_format = '%Y%m%d_%H%M%S'

        self.work = True

    def run(self):
        while self.work:
            _time = datetime.now()
            _time = _time.strftime(self.time_format)
            temp_values = self.v34461A.query_ascii_values(':READ?')
            read = temp_values[0]
            print(_time, ': ', read)

            return read

        self.v34461A.close()
        self.rm.close()


# if __name__ == "__main__":
#     ks_34461a = keysight_34461a(sys.argv)
#     ks_34461a.run()
