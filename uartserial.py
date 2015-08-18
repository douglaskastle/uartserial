from __future__ import print_function    # (at top of module)
import serial
import sys
import socket
import configparser
import binascii
import struct

def bytes2Int(x):
    if 0 == len(x):
        return None

    try: # python2 way
        return int(x.encode("hex"),16)
    except AttributeError: # python3 way
        received = 0
        for i in range(len(x)):
            received = (received << 8) + x[i]
        return received

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class uartCmd():
    def __init__(self, ser=None, rw=0x0, address=0x0, length=0x4, expected=0x0000, data=0x0000):
        if ser == None:
            print("No serial port defined")
            raise Error
        elif not isinstance(ser, serial.Serial):
            print("Not a serial port:")
            print(ser)
            raise Error
        elif not ser.isOpen():
            print("Attempting to use a port that is not open")
            raise Error
        
        self.ser = ser
        self.uart_id = 0x31
        self.uart_id_inv = self.uart_id ^ 0xff
        self.rw = rw
        self.address = address
        self.length = length
        self.expected = expected
        self.data = data
        self.bin_val = None
        self.tx_string = None
        self.return_length = 0x0
        self.echo = True
        self.received = None
        self.check = True
    
    def __str__(self):
        self.pack()
        return self.tx_string
    
    def set(self, rw=None, address=None, length=None, expected=None, data=None):
        if not rw == None:
            self.rw = rw
        if not address == None:
            self.address = address
        if not length == None:
            self.length = length
        else:
            self.length = 4
        if not expected == None:
            self.expected = expected
        if not data == None:
            self.data = data
    
    def pack(self):
        self.uart_id_inv = self.uart_id ^ 0xff
        if self.rw == 0:
            self.return_length = self.length
            self.bin_val = struct.pack('BBBBBBB',
                                        self.uart_id,
                                        self.uart_id_inv,
                                        self.rw,
                                        ((self.address >> 8)  & 0xff), (self.address & 0xff),
                                        ((self.length  >> 8)  & 0xff), (self.length  & 0xff),
                                       )
        else:
            self.return_length = 1
            self.bin_val = struct.pack('BBBBBBBBBBB',
                                        self.uart_id,
                                        self.uart_id_inv,
                                        self.rw,
                                        ((self.address >> 8)  & 0xff),  (self.address & 0xff),
                                        ((self.length  >> 8)  & 0xff),  (self.length  & 0xff),
                                        ((self.data    >> 24) & 0xff), ((self.data >> 16) & 0xff),
                                        ((self.data    >> 8)  & 0xff),  (self.data    & 0xff),
                                       )
        self.tx_string = binascii.hexlify(self.bin_val)
    
    def read(self, **kwargs):
        kwargs['rw'] = 0x0
        self.set(**kwargs)
        if not 'expected' in kwargs.keys():
            self.expected = None
            
        x = self.send_command(self.expected)
        return x

    def write(self, **kwargs):
        kwargs['rw'] = 0x1
        self.set(**kwargs)
        x = self.send_command()

    def tx(self):
        self.pack()
        return(self.bin_val)

    def send_command(self, expected=None):
        self.expected = expected
        if self.rw == 1 and self.expected == None:
            self.expected = 0x32
        
        if not self.ser.isOpen():
            print("Attempting to use a port that is not open")
            raise Error
        
        try:
            self.ser.write(self.tx())
        except:
            self.ser.close()
            print("Check if JTAG is plugged in")
            print("Unexpected Error", sys.exc_info()[0])
            raise
            
        # Check the response, make sure the command
        # was successful
        x = self.ser.read(self.return_length)
        received = None
        if not len(x) == 0:
            #received = int(x.encode("hex"),16)
            received = bytes2Int(x)
        else:
            x = None
        
        if self.echo:
            if self.rw == 0:
                print("Read from", end=" ")
            else:
                print("Write to ", end=" ")
        
            print("0x{0:04x}".format(self.address), end=" ")
            if self.rw == 0 and not self.expected == None:
                print("expected 0x{0:08x}".format(self.expected), end=" ")
            elif self.rw == 1 :
                print("         0x{0:08x}".format(self.data), end=" ")
            elif self.rw == 0 and not received == None and self.expected == None:
                print("         0x{0:08x}".format(received), end=" ")
            print("")
        
        #print(x.encode("hex")
        if not self.expected == None and not x == None:
            if not self.expected == received:
                print("    No Match")
                print("    expected 0x{0:08x}".format(self.expected))
                print("    received 0x{0:08x}".format(received))
#             else:
#                 print("Match"
        
        if x == None:
            print("Unsuccessful Readback!")
        
        self.received = received
        return received

#     config = configparser.ConfigParser()
#     config['DEFAULT'] = {'port': '3',
#                           'baudrate': '9600',
#                           'timeout': '2'}
# 
#     with open(configfile, 'w') as configfile:
#           config.write(configfile)    
    
def openSerial(port=3, baudrate=9600, timeout=2):
    machine = socket.gethostname()
    configfile = machine+'.ini'
    
    default_values = {'port' : port, 'baudrate' : baudrate, 'timeout' : timeout,}
    config = configparser.ConfigParser()
    config.sections()
    config.read(configfile)

    ser = serial.Serial()
    for key in default_values.keys():
        try:
            setattr(ser, key, int(config['DEFAULT'][key]))
        except KeyError:
            setattr(ser, key, int(default_values[key]))

    ser.close()
    
    ser.open()
    return ser
