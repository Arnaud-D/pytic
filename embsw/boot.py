import pyb
import utoken
pyb.main('main.py')
if utoken.exists():
    pyb.usb_mode("MSC")
    utoken.delete()
else:
    pyb.usb_mode("VCP")
