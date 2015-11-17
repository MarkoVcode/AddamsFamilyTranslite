
import sqlite3
import time
import piglow
from Adafruit_MAX9744 import MAX9744

C_1 = 13
C_2 = 14
C_3 = 15
C_4 = 16
C_5 = 5
C_6 = 4
C_7 = 1
C_8 = 2

amp = MAX9744()
amp.set_volume(0)

while True:
	conn=sqlite3.connect('db/settings.db')
	curs=conn.cursor()
	curs.execute("SELECT value FROM af_overrides where paramName='backlightBrightness'")
	setting = curs.fetchone()
	z = setting[0]
	conn.close()
        piglow.led(C_1,z)
        piglow.led(C_2,z)
        piglow.led(C_3,z)
        piglow.led(C_4,z)
        piglow.led(C_5,z)
        piglow.led(C_6,z)
        piglow.led(C_7,z)
        piglow.led(C_8,z)
        piglow.show()
        time.sleep(0.3)

