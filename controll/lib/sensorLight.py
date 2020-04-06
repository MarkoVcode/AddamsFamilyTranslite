#!/usr/bin/python
import spidev
import time
import os

EXTERNAL_LIGHT = 0
INTERNAL_LIGHT = 1

class sensorLight:
  def __init__(self):
    # Open SPI bus
    self.spi = spidev.SpiDev()
    self.spi.open(0,0)

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

  def printValues(self):
    # Read the light sensor data
    ext_level = self.readChannel(EXTERNAL_LIGHT)
    ext_volts = self.convertVolts(ext_level, 2)

    # Read the temperature sensor data
    int_level = self.readChannel(INTERNAL_LIGHT)
    int_volts = self.convertVolts(int_level, 2)

    # Print out results
    print("EXT Light: {} ({}V)".format(ext_level,ext_volts))
    print("INT Light: {} ({}V)".format(int_level,int_volts))

if __name__ == '__main__':
    sensor = sensorLight()
    sensor.printValues()