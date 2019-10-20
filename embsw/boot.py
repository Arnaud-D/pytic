import pyb
import token
pyb.main('main.py')
if token.exists():
    pyb.usb_mode("MSC")
    token.delete()
else:
    pyb.usb_mode("VCP")
