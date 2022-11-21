import argparse
from datetime import datetime
import struct
import sys
import time
import traceback
import json

# Obtained via pip
import pigpio
from nrf24 import *

id_mapper = {
    10: "Bedroom",
    20: "Outside",
    21: "Living room",
    22: "Laundry room" }

measurement_mapper = {
        "I": "id",
        "x": "uptime_s",
        "B": "battvolts_v",
        "T": "temperature_f",
        "P": "pressure_pa" }

pi = pigpio.pi('localhost', 8888)

nrf = NRF24(
        pi,
        ce=25,
        payload_size=0,
        channel=76,
        data_rate=RF24_DATA_RATE.RATE_250KBPS,
        pa_level=RF24_PA.MIN)
nrf.set_address_bytes(5)
nrf.open_writing_pipe('MMMMM') # Never used
nrf.open_reading_pipe(RF24_RX_ADDR.P1, 'KKKKK') # 5-byte address to listen on

while True:
    if nrf.data_ready():
        print("-" * 20)
        slurp = nrf.get_payload()
        databite = {}
        # Unpack the incoming data assuming a 5-byte key/value system:
        #    Byte 0: Unsigned char (ASCII identifier)
        #    Byte 1-4: Little-endian floating point number (measurement)
        for x in range(0, len(slurp), 5):
            (ident, val) = struct.unpack('<Bf', slurp[x:x+5])
            ident = chr(ident)
            databite[ident] = val
            #print("{}: {}".format(ident, val))

        if ((not "I" in databite)
                or (not "x" in databite)
                or (not "B" in databite)
                or (not "T" in databite)):
            print("!!! Bogus dataset from ID {}!!!".format(int(databite["I"]) if "I" in databite else "?UNKNOWN?"))
        else:
            print(json.dumps(databite))


    time.sleep(0.01)
