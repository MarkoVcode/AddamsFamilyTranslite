#!/bin/sh

cd /home/pi/display/controll

java -jar ProjectAddamsFamily.jar -Dlogback.configurationFile=/home/pi/display/controll/config/logback.xml & 2 > /dev/null
/bin/sh BacklightControllerWrapper.sh &  2 > /dev/null
#/bin/sh ExternalLightsWrapper.sh & 2 > /dev/null
#BacklightControllerWrapper.sh &  2 > /dev/null
