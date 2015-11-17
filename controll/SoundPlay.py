#!/usr/bin/python

import sys, getopt
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

MESSAGE = 'test.py -v <volume> -i <wavfile> -s <startmarker> -t <stopmarker> -k <knockeventsmarker>'

def main(argv):
   inputfile = ''
   start = ''
   stop = ''
   knock = ''
   volume = ''
   try:
      opts, args = getopt.getopt(argv,"hv:i:s:t:k:",["volume=","ifile=","start=","stop=","knock="])
   except getopt.GetoptError:
      print MESSAGE
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print MESSAGE
         sys.exit()
      elif opt in ("-v", "--volume"):
         volume = arg
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-s", "--start"):
         start = arg
      elif opt in ("-t", "--stop"):
         stop = arg
      elif opt in ("-k", "--knock"):
         knock = arg

#   print 'Volume ', volume
#   print 'File ', inputfile
#   print 'Start ', start 
#   print 'Stop ', stop
#   print 'Knock ', knock
   pygame.mixer.init()
   pygame.mixer.music.load(inputfile)
   pygame.mixer.music.play()
   vset = True
   while pygame.mixer.music.get_busy() == True:
       position = pygame.mixer.music.get_pos()
#       print position
       checkForKnock(knock, position)
       if position  >= int(stop):
#           print "min"
           amp.set_volume(0)
           sys.exit()
       elif position >= int(start) and position < int(stop) and vset:
#           print "max"
           amp.set_volume(int(volume))
           vset = False
       continue
   GPIO.cleanup()

def checkForKnock(knocks, currentPos):
    knocksList = knocks.split("|")
    for sknock in knocksList:
       if int(sknock) == currentPos:
          knock(KNOCKER_LEFT)

def knock(pin):
    GPIO.output(pin,GPIO.HIGH)
    time.sleep(0.065)
    GPIO.output(pin,GPIO.LOW)
    return

if __name__ == "__main__":
   main(sys.argv[1:])

