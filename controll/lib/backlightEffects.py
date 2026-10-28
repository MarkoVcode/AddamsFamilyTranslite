#!/usr/bin/python
import time
import piglow
from random import randint

# Ported from BacklightControllerBrightness.py. "channels" is the list of the
# 8 main display LEDs in order C_1..C_8, so pairs from the outside in are
# (0,7), (1,6), (2,5), (3,4).

class backlightEffects:
  def __init__(self, channels):
    self.channels = channels

  # called every 0.1s: blink about every 15s, big effect about every 100s
  def doRandomBlink(self):
    return randint(0,150) == 75

  def doRandomEffect(self):
    return randint(0,1000) == 500

  def execRandomEffect(self, brightness):
    if randint(0,1) == 0:
      self.shutdownEffect(brightness)
    else:
      self.bounceEffect(brightness)

  # single LED flickering like a bad bulb
  def disturbOn(self, brightness):
    channel = self.channels[randint(0,7)]
    for delVal in [0.3,0.1,0.05,0.2,0.3]:
      piglow.led(channel,0)
      piglow.show()
      time.sleep(delVal)
      piglow.led(channel,brightness)
      piglow.show()
      time.sleep(delVal)

  def setPair(self, pair, brightness):
    piglow.led(self.channels[pair],brightness)
    piglow.led(self.channels[7 - pair],brightness)
    piglow.show()

  # lights go out from the outside in, stay dark for 2s, then come back
  def shutdownEffect(self, brightness):
    for pair in [0,1,2]:
      self.setPair(pair, 0)
      time.sleep(0.25)
    self.setPair(3, 0)
    time.sleep(2)
    for pair in [0,1,2,3]:
      self.setPair(pair, brightness)

  # quick wave outside -> in -> outside
  def bounceEffect(self, brightness):
    for pair in [0,1,2]:
      self.setPair(pair, 0)
      time.sleep(0.1)
    self.setPair(3, 0)
    time.sleep(0.01)
    self.setPair(3, brightness)
    time.sleep(0.01)
    for pair in [2,1]:
      self.setPair(pair, brightness)
      time.sleep(0.1)
    self.setPair(0, brightness)
