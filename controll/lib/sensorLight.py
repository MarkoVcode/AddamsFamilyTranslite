#!/usr/bin/python
import spidev
#import time
#import os

#EXTERNAL_LIGHT = 0
#INTERNAL_LIGHT = 1

class sensorLight:

  EXTERNAL_LIGHT = 0
  INTERNAL_LIGHT = 1

  def __init__(self):
    # Open SPI bus
    self.spi = spidev.SpiDev()
    self.spi.open(0,0)
    self.ext_level = 0
    self.int_volts = 0
    self.int_level = 0
    self.int_volts = 0

  # Function to read SPI data from MCP3008 chip
  # Channel must be an integer 0-7
  def readChannel(self, channel):
    adc = self.spi.xfer2([1,(8+channel)<<4,0])
    data = ((adc[1]&3) << 8) + adc[2]
    return data

  # Function to convert data to voltage level,
  # rounded to specified number of decimal places.
  def convertVolts(self, data, places):
    volts = (data * 3.3) / float(1023)
    volts = round(volts,places)
    return volts

  def fetchValues(self):
    # Read the light sensor data
    self.ext_level = self.readChannel(self.EXTERNAL_LIGHT)
    self.ext_volts = self.convertVolts(self.ext_level, 2)

    # Read the temperature sensor data
    self.int_level = self.readChannel(self.INTERNAL_LIGHT)
    self.int_volts = self.convertVolts(self.int_level, 2)

  def printValues(self):
    # Print out results
    print("EXT Light: {} ({}V)".format(self.ext_level,self.ext_volts))
    print("INT Light: {} ({}V)".format(self.int_level,self.int_volts))

if __name__ == '__main__':
    sensor = sensorLight()
    sensor.fetchValues()
    sensor.printValues()
