#!/usr/bin/python
import os
import json
import subprocess

# Keeps the settings in a JSON file on a partition that is normally mounted
# read-only. It is remounted read-write only for the moment of a save.

class settingsStore:
  def __init__(self, mountPoint, fileName):
    self.mountPoint = mountPoint
    self.path = os.path.join(mountPoint, fileName)
    #True when the last load() found a readable file
    self.loaded = False

  def load(self, defaults):
    settings = dict(defaults)
    self.loaded = False
    try:
      f = open(self.path)
      settings.update(json.load(f))
      f.close()
      self.loaded = True
      print("settings loaded from " + self.path)
    except Exception as e:
      print("using default settings: " + repr(e))
    return settings

  def save(self, settings):
    if not os.path.ismount(self.mountPoint):
      print("settings not saved: " + self.mountPoint + " is not mounted")
      return False
    if subprocess.call(["mount", "-o", "remount,rw", self.mountPoint]) != 0:
      print("settings not saved: cannot remount " + self.mountPoint)
      return False
    try:
      folder = os.path.dirname(self.path)
      if not os.path.isdir(folder):
        os.makedirs(folder)
      # write to a temp file and rename, so a power cut never leaves half a file
      tmp = self.path + ".tmp"
      f = open(tmp, "w")
      json.dump(settings, f, sort_keys=True, indent=1)
      f.flush()
      os.fsync(f.fileno())
      f.close()
      os.rename(tmp, self.path)
      print("settings saved to " + self.path)
    finally:
      subprocess.call(["sync"])
      subprocess.call(["mount", "-o", "remount,ro", self.mountPoint])
    return True
