import pyb
import utoken
pyb.main('main.py')
if utoken.exists():  # Start in transfer mode
    pyb.usb_mode("MSC")
    utoken.delete()  # Next start will be in logger mode
else:  # Start in logger mode
    pyb.usb_mode("VCP")
