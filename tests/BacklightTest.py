#!/usr/bin/python

import spidev
import os
import time
import piglow
from random import randint

C_1 = 13
C_2 = 14
C_3 = 15
C_4 = 16
C_5 = 5
C_6 = 4
C_7 = 18
C_8 = 2

#HEADER 3:
E_3 = 6
#HEADER 4:
E_4 = 3
#HEADER 2:
E_2 = 12
#HEADER 1:
E_1 = 11


def disturbOn(channel,brightness):
  list = [0.3,0.1,0.05,0.2,0.3]
  for delVal in list:
     piglow.led(channel,0)
     piglow.show()
     time.sleep(delVal)
     piglow.led(channel,brightness)
     piglow.show()
     time.sleep(delVal)

def disturbOff(channel,brightness):
  list = [0.3,0.1,0.02,0.02,0.1,0.3]
  for delVal in list:
     piglow.led(channel,brightness)
     piglow.show()
     time.sleep(delVal)
     piglow.led(channel,0)
     piglow.show()
     time.sleep(delVal)

def doRandomBlink():
  no = randint(0,150)
  if no == 75:
     return True
  return False

def doRandomEffect():
  no = randint(0,1000)
  if no == 500:
     return True
  return False

def execRandomEffect(brightness):
  no = randint(0,1)
  if no == 0:
     shutdownEffect(brightness)
     #bounceEffect(brightness)
  elif no == 1:
     bounceEffect(brightness)

def getRandomLedChannel():
  ch = randint(0,7)
  if ch == 0:
     return C_1
  elif ch == 1:
     return C_2
  elif ch == 2:
     return C_3
  elif ch == 3:
     return C_4
  elif ch == 4:
     return C_5
  elif ch == 5:
     return C_6
  elif ch == 6:
     return C_7
  elif ch == 7:
     return C_8
  else:
     return C_1

def shutdownEffect(brigthness):
  piglow.led(C_1,0)
  piglow.led(C_8,0)
  piglow.show()
  time.sleep(0.25)

  piglow.led(C_2,0)
  piglow.led(C_7,0)
  piglow.show()
  time.sleep(0.25)

  piglow.led(C_3,0)
  piglow.led(C_6,0)
  piglow.show()
  time.sleep(0.25)

  piglow.led(C_4,0)
  piglow.led(C_5,0)
  piglow.show()
  time.sleep(2)

  piglow.led(C_1,brigthness)
  piglow.led(C_2,brigthness)
  piglow.led(C_3,brigthness)
  piglow.led(C_4,brigthness)
  piglow.led(C_5,brigthness)
  piglow.led(C_6,brigthness)
  piglow.led(C_7,brigthness)
  piglow.led(C_8,brigthness)
  piglow.show()

def bounceEffect(brightness):
  piglow.led(C_1,0)
  piglow.led(C_8,0)
  piglow.show()
  time.sleep(0.1)

  piglow.led(C_2,0)
  piglow.led(C_7,0)
  piglow.show()
  time.sleep(0.1)

  piglow.led(C_3,0)
  piglow.led(C_6,0)
  piglow.show()
  time.sleep(0.1)

  piglow.led(C_4,0)
  piglow.led(C_5,0)
  piglow.show()
  time.sleep(0.01)

  piglow.led(C_4,brightness)
  piglow.led(C_5,brightness)
  piglow.show()
  time.sleep(0.01)

  piglow.led(C_3,brightness)
  piglow.led(C_6,brightness)
  piglow.show()
  time.sleep(0.1)

  piglow.led(C_2,brightness)
  piglow.led(C_7,brightness)
  piglow.show()
  time.sleep(0.1)

  piglow.led(C_1,brightness)
  piglow.led(C_8,brightness)
  piglow.show()



while True:
        z = 255
#        piglow.led(C_1,z)
 #       piglow.led(C_2,z)
  #      piglow.led(C_3,z)
   #     piglow.led(C_4,z)
      #  piglow.led(C_5,z)
    #    piglow.led(C_6,z)
     #   piglow.led(C_7,z)
      #  piglow.led(C_8,z)
        piglow.led(E_3,z)
        piglow.led(E_4,z)
        piglow.led(E_1,z)
        piglow.led(E_2,z)
        piglow.show()
        time.sleep(0.5)
      #  if doRandomBlink():
      #      disturbOn(getRandomLedChannel(),z)
      #  if doRandomEffect():
      #      execRandomEffect(z)

