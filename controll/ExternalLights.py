#!/usr/bin/python

import spidev
import os
import sqlite3
import time
import piglow
from random import randint

#HEADER 3:
E_3 = 6
#HEADER 4:
E_4 = 3
#HEADER 1:
E_2 = 1
#HEADER 2:
E_1 = 11

brightE1 = 0
brightE2 = 0
brightE3 = 0
brightE4 = 0

def ConvertToBrightness():
  global brightE1
  global brightE2
  global brightE3
  global brightE4
  retVal = False
  conn=sqlite3.connect('db/settings.db')
  curs=conn.cursor()
  curs.execute("SELECT * FROM af_ebrightvalues")
  for row in curs:
	if(row[1] == 'E1'):
	  if(brightE1 != row[2]):
	    brightE1 = row[2]
	    retVal = True
        if(row[1] == 'E2'):
          if(brightE2 != row[2]):
            brightE2 = row[2]
            retVal = True
        if(row[1] == 'E3'):
          if(brightE3 != row[2]):
            brightE3 = row[2]
            retVal = True
        if(row[1] == 'E4'):
          if(brightE4 != row[2]):
            brightE4 = row[2]
            retVal = True
  conn.close()
  return retVal

while True:
       if(ConvertToBrightness()):
#          print "change"
#	  print brightE1
#	  print brightE2
 #         print brightE3
  #        print brightE4
          piglow.led(E_1,brightE1)
          piglow.led(E_2,brightE2)
          piglow.led(E_3,brightE3)
          piglow.led(E_4,brightE4)
          piglow.show()
       time.sleep(0.3)

