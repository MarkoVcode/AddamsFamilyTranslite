#!/bin/sh


until /usr/bin/python BacklightControllerBrightness.py; do
    echo "Server 'myserver' crashed with exit code $?.  Respawning.." >&2
    sleep 1
done

