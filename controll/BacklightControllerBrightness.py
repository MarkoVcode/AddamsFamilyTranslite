#!/usr/bin/python

import spidev
import os
import sqlite3
import time
import piglow
from Adafruit_MAX9744 import MAX9744
from random import randint

C_1 = 13
C_2 = 14
C_3 = 15
C_4 = 16
C_5 = 5
C_6 = 4
C_7 = 1
C_8 = 2

# Open SPI bus
spi = spidev.SpiDev()
spi.open(0,0)

# Function to read SPI data from MCP3008 chip
# Channel must be an integer 0-7
def ReadChannel(channel):
  adc = spi.xfer2([1,(8+channel)<<4,0])
  data = ((adc[1]&3) << 8) + adc[2]
  return data

# Function to convert data to voltage level,
# rounded to specified number of decimal places.
def ConvertVolts(data,places):
  volts = (data * 3.3) / float(1023)
  volts = round(volts,places)
  return volts

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

def ConvertToBrightness(data):
  conn=sqlite3.connect('db/settings.db')
  curs=conn.cursor()
  curs.execute("SELECT value FROM af_overrides where paramName='backlightBrightness'")
  setting = curs.fetchone()
  z = setting[0]
  if z == 0:
     if data >=  850:
        return 10
     elif data >= 500:
        return 50
     elif data >= 450:
        return 80
     elif data >= 400:
        return 110
     elif data >= 350:
        return 130
     elif data >= 300:
        return 180
     elif data >= 180:
        return 200
     elif data >= 20:
        return 220
     else:
        return 0
  else:
     return z

# Define sensor channels
light_channel = 0
temp_channel  = 1


amp = MAX9744()
amp.set_volume(0)

while True:
	z = ConvertToBrightness(ReadChannel(light_channel))
        piglow.led(C_1,z)
        piglow.led(C_2,z)
        piglow.led(C_3,z)
        piglow.led(C_4,z)
        piglow.led(C_5,z)
        piglow.led(C_6,z)
        piglow.led(C_7,z)
        piglow.led(C_8,z)
        piglow.show()
        time.sleep(0.5)
        if doRandomBlink():
            disturbOn(getRandomLedChannel(),z)
        if doRandomEffect():
            execRandomEffect(z)
