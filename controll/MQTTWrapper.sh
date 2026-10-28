#!/bin/sh

# Output goes to syslog (tag "translite"): view with  grep translite /var/log/syslog
# Never write to the terminal that started us - when that ssh session closes,
# print() fails with IOError inside paho's thread and the client goes dead.
exec >/dev/null 2>&1

sudo /usr/bin/python SoundPlay.py
# mqttClientService.py never exits normally - always restart it
while true; do
    /usr/bin/python -u mqttClientService.py 2>&1 | logger -t translite
    logger -t translite "Server 'mqtt client' exited. Respawning.."
    sleep 5
done
