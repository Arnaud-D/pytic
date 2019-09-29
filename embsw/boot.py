import machine
import pyb
# pyb.country('US')  # ISO 3166-1 Alpha-2 code, eg US, GB, DE, AU
pyb.freq(84000000, 84000000, 21000000, 42000000)
pyb.main('main.py')  # main script to run after this one
pyb.usb_mode('VCP+MSC')  # act as a serial and a storage device
