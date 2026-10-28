#!/usr/bin/python

import sys, getopt
import os
import signal
import select
import subprocess
import pygame
import time
import RPi.GPIO as GPIO

from Adafruit_MAX9744 import MAX9744

amp = MAX9744()
amp.set_volume(0)

GPIO.setwarnings(False)
# to use Raspberry Pi board pin numbers
GPIO.setmode(GPIO.BOARD)
# set up GPIO output channel
GPIO.setup(38, GPIO.OUT)
GPIO.setup(40, GPIO.OUT)

KNOCKER_LEFT = 40
KNOCKER_RIGHT = 38

#fade out at the stop marker instead of cutting the music off
FADE_OUT_MS = 3000
#Pi analog output level in 1/100 dB. Full level from the Pi and less gain on the
#amplifier keeps the Pi's own noise down (it was -17.25dB with the amp near max)
PI_OUTPUT_LEVEL = 0

MESSAGE = 'test.py -v <volume> -m <musicvolume> -i <wavfile> -s <startmarker> -t <stopmarker> -k <knockeventsmarker>'

controlBuffer = ['']
controlOpen = [True]

# Live changes from mqttClientService.py on stdin, one per line:
# "VOLUME <0-63>" (amplifier) or "MUSIC-VOLUME <0-100>" (this player on the Pi)
def readControl():
   commands = []
   while controlOpen[0] and select.select([sys.stdin], [], [], 0)[0]:
      data = os.read(sys.stdin.fileno(), 1024)
      if data == '':
         controlOpen[0] = False
         break
      controlBuffer[0] += data
   while '\n' in controlBuffer[0]:
      line, controlBuffer[0] = controlBuffer[0].split('\n', 1)
      parts = line.split()
      if len(parts) == 2 and parts[1].isdigit():
         commands.append((parts[0], int(parts[1])))
   return commands

def main(argv):
   inputfile = ''
   start = ''
   stop = ''
   knockMarkers = ''
   volume = ''
   musicVolume = '100'
   try:
      opts, args = getopt.getopt(argv,"hv:m:i:s:t:k:",["volume=","musicvolume=","ifile=","start=","stop=","knock="])
   except getopt.GetoptError:
      print MESSAGE
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print MESSAGE
         sys.exit()
      elif opt in ("-v", "--volume"):
         volume = arg
      elif opt in ("-m", "--musicvolume"):
         musicVolume = arg
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-s", "--start"):
         start = arg
      elif opt in ("-t", "--stop"):
         stop = arg
      elif opt in ("-k", "--knock"):
         knockMarkers = arg

   # called without a file (at boot from MQTTWrapper.sh): just mute the amp
   if inputfile == '':
      return

#   print 'Volume ', volume
#   print 'File ', inputfile
#   print 'Start ', start 
#   print 'Stop ', stop
#   print 'Knock ', knock
   subprocess.call(["amixer", "-q", "cset", "numid=1", str(PI_OUTPUT_LEVEL)])
   # there is no pulseaudio here; going straight to ALSA avoids its errors
   os.environ["SDL_AUDIODRIVER"] = "alsa"
   pygame.mixer.init()
   pygame.mixer.music.load(inputfile)
   pygame.mixer.music.play()
   # music volume on the Pi, 0-100%; the amplifier (VOLUME) is the master
   pygame.mixer.music.set_volume(int(musicVolume) / 100.0)
   vset = True
   pendingKnocks = sorted(int(k) for k in knockMarkers.split("|") if k != '')
   while pygame.mixer.music.get_busy() == True:
       position = pygame.mixer.music.get_pos()
#       print position
       for name, value in readControl():
           if name == "VOLUME":
               volume = value
               # before the start marker the amp stays muted; it gets the new value there
               if not vset:
                   amp.set_volume(int(volume))
           elif name == "MUSIC-VOLUME":
               pygame.mixer.music.set_volume(value / 100.0)
       # the loop never lands exactly on a millisecond, so knock as soon as a marker is passed
       while pendingKnocks and position >= pendingKnocks[0]:
           pendingKnocks.pop(0)
           knock(KNOCKER_LEFT)
       if position  >= int(stop):
#           print "min"
           pygame.mixer.music.fadeout(FADE_OUT_MS)
           time.sleep(FADE_OUT_MS / 1000.0)
           break
       elif position >= int(start) and position < int(stop) and vset:
#           print "max"
           amp.set_volume(int(volume))
           vset = False
       time.sleep(0.005)

def knock(pin):
    GPIO.output(pin,GPIO.HIGH)
    time.sleep(0.065)
    GPIO.output(pin,GPIO.LOW)
    return

def on_sigterm(signum, frame):
    # turns SIGTERM (sound switched off from mqtt) into a normal exit, so the finally below runs
    sys.exit(0)

if __name__ == "__main__":
   signal.signal(signal.SIGTERM, on_sigterm)
   try:
      main(sys.argv[1:])
   finally:
      # however we got here: knocker released, amplifier muted
      GPIO.output(KNOCKER_LEFT, GPIO.LOW)
      GPIO.output(KNOCKER_RIGHT, GPIO.LOW)
      amp.set_volume(0)
      GPIO.cleanup()

