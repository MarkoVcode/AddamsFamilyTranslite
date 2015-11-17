#!/bin/sh

cd /home/pi/display/controll

java -jar ProjectAddamsFamily-all-1.0.jar & 2 > /dev/null
/bin/sh BacklightControllerWrapper.sh &  2 > /dev/null
#BacklightControllerWrapper.sh &  2 > /dev/null
