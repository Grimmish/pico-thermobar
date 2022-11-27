# Brief pause to allow computer USB port to properly negotiate with device
import time
time.sleep_ms(400)

from machine import Pin, I2C, SPI, ADC, lightsleep
greenled = Pin(25, Pin.OUT, value=0) 

# These pins are unused, but documented here for completeness
thermobar_extra = [
    Pin(22, Pin.OUT, value=1), # Power
    Pin(19, Pin.IN), # CSB, unused
    Pin(18, Pin.IN)  # SDD, unused
]

import bmp280   # https://github.com/dafvid/micropython-bmp280
import nrf24l01 # https://github.com/micropython/micropython-lib/tree/master/micropython/drivers/radio/nrf24l01
import ustruct as struct

# The "config.txt" file should contain only a 8-bit integer that uniquely will uniquely
# identify this module
with open('config.txt') as uid:
    myID = int(uid.read())

# Another text file that contains only a 8-bit integer
with open('zone.txt') as zoneid:
    zoneID = int(zoneid.read())

battery = ADC(28)
sampleperiod_ms = 10000

nrfcfg = {
    "spi": 1,
    "miso": 12,
    "mosi": 11,
    "sck": 10,
    "csn": 13,
    "ce": 15
}

thermobar = bmp280.BMP280(I2C(id=0, scl=Pin(21), sda=Pin(20), freq=400000))
thermobar.use_case(bmp280.BMP280_CASE_INDOOR)
thermobar.normal_measure()

csn = Pin(nrfcfg["csn"], Pin.OUT, value=1)
ce = Pin(nrfcfg["ce"], Pin.OUT, value=0)
spi = SPI(1, sck=Pin(nrfcfg["sck"]), mosi=Pin(nrfcfg["mosi"]), miso=Pin(nrfcfg["miso"]))

# Same channel as RPi lib default
nrf = nrf24l01.NRF24L01(spi, csn, ce, payload_size=0, channel=76) 
nrf.reg_write(nrf24l01.DYNPD, 1) # Enable dynamic payload construction
nrf.reg_write(0x1D, 0x04) # Enable dynamic payload support in firmware
nrf.open_tx_pipe(b'KKKKK')
nrf.open_rx_pipe(1, b'OOOOO') 
nrf.set_power_speed(nrf24l01.POWER_3, nrf24l01.SPEED_250K)
nrf.reg_write(0x04, 0b10001000) # Retry 8x at 1ms intervals

# Identify if we're running on USB power vs. battery
usbref = Pin(24, Pin.IN)
onUSBpower = usbref.value()

print("Ready to party")
greenled.toggle()

# Encoding formats for pack/unpack on sender/receiver must match!
#    https://docs.python.org/3/library/struct.html
# The format (first arg) explains the nature of each element, in order.
#
# ord() and chr() are handy ways to convert characters to/from 8-bit
# unsigned bytes.
# Example:
#    struct.pack("<BfBf", ord("T"), 68.231, ord("H"), 34.0)

while True:
    payload = {
        "I": myID,
        "Z": zoneID,
        "x": time.ticks_ms() // 1000,
        "B": (battery.read_u16() / 2**16) * 2 * 3.3,
        "T": (thermobar.temperature * 9 / 5) + 32,
        "P": (thermobar.pressure / 100)
    }
    
    packpayload = b''
    for k in payload:
        packpayload += struct.pack('<Bf', ord(k), payload[k])

    #print("Uptime: {:d} s   Battery: {:4.2f} V  Temp: {:5.1f} F   Pressure: {:6.1f} hPa".format(payload["x"], payload["B"], payload["T"], payload["P"]))

    greenled.on()
    try:
        nrf.send(packpayload)
        greenled.off()
    except:
        print("Send failed!")

    # After the first 2 minutes (debugging window), start using low-power
    # mode between cycles
    if time.ticks_ms() > 120000:
        lightsleep(sampleperiod_ms)
    else:
        time.sleep_ms(sampleperiod_ms)
