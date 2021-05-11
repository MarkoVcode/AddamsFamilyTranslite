#!/bin/sh

sudo /usr/bin/python SoundPlay.py
until /usr/bin/python mqttClientService.py; do
    echo "Server 'mqtt client' crashed with exit code $?.  Respawning.." >&2
    sleep 1
done
