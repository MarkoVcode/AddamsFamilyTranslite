import paho.mqtt.client as mqtt #import the client1
import time
import sys
import piglow
import json
import subprocess
from datetime import datetime
from Adafruit_MAX9744 import MAX9744
from lib.sensorLight import sensorLight
from lib.backlightEffects import backlightEffects
from lib.settingsStore import settingsStore

DEVICE_NAME="TRANSLITE-1"
BROKER_ADDRESS="192.168.1.20"
VALID_ON_OFF_VALUES=["ON", "OFF"]

#seconds
DELAY_ON_TELEMETRY_UPDATE = 60
MAX_OFFLINE_TIME = 300
#wait for the last change before writing, so dragging a slider is one write
SAVE_DELAY = 10
#how long to collect our own retained stat messages when the settings file is missing
RESTORE_TIME = 3

#daily music + knocker, local time (hour, minute)
PLAY_AT = (12, 0)
AUDIO_TRACK = "1"
#MAX9744 amplifier range
MAX_VOLUME = 63

#NOOBS SETTINGS partition (/dev/mmcblk0p3), mounted read-only
SETTINGS_MOUNT = "/mnt/settings"
SETTINGS_FILE = "translite/settings.json"

#Main display
C_1 = 13
C_2 = 14
C_3 = 15
C_4 = 16
C_5 = 5
C_6 = 4
C_7 = 18
C_8 = 2
SCREEN_LEDS = [C_1, C_2, C_3, C_4, C_5, C_6, C_7, C_8]

#External LED
#HEADER 3:
E_3 = 6
#HEADER 4:
E_4 = 3
#HEADER 2:
E_2 = 12
#HEADER 1:
E_1 = 11
EXT_LEDS = {"CH1": E_1, "CH2": E_2, "CH3": E_3, "CH4": E_4}

# Every setting has cmnd/TRANSLITE-1/<NAME> and a retained stat/TRANSLITE-1/<NAME>
SWITCHES = ["BACKLIGHT", "SOUND", "EFFECTS",
            "EXT-POWER-CH1", "EXT-POWER-CH2", "EXT-POWER-CH3", "EXT-POWER-CH4"]
#name: (min, max)
NUMBERS = {"BCKL-LEVEL": (10, 200),
           "VOLUME": (0, MAX_VOLUME),
           "EXT-BRIGHT-CH1": (0, 255), "EXT-BRIGHT-CH2": (0, 255),
           "EXT-BRIGHT-CH3": (0, 255), "EXT-BRIGHT-CH4": (0, 255)}

DEFAULT_SETTINGS = {
    "BACKLIGHT": "ON",
    #percent of the light sensor curve
    "BCKL-LEVEL": 100,
    "VOLUME": 60,
    #daily music at PLAY_AT
    "SOUND": "ON",
    #random backlight blinks
    "EFFECTS": "ON",
    "EXT-POWER-CH1": "OFF", "EXT-BRIGHT-CH1": 0,
    "EXT-POWER-CH2": "OFF", "EXT-BRIGHT-CH2": 0,
    "EXT-POWER-CH3": "OFF", "EXT-BRIGHT-CH3": 0,
    "EXT-POWER-CH4": "OFF", "EXT-BRIGHT-CH4": 0,
}

class SensorList:
    def __init__(self):
        self.Temperature1 = None
        self.Temperature2 = None
        self.Light1 = None
        self.Light2 = None
        self.Backlight = None
    def reprJSON(self):
        return dict(Temperature1=self.Temperature1, Temperature2=self.Temperature2, Light1=self.Light1, Light2=self.Light2, Backlight=self.Backlight)

class Sensors:
    def __init__(self):
        self.Time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.Local = SensorList()
    def reprJSON(self):
        return dict(Time=self.Time, Local=self.Local.reprJSON())

class SystemState:
    def __init__(self):
        self.Time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.SysUptime = ""
    def reprJSON(self):
        return dict(Time=self.Time, SysUptime=self.SysUptime)

############
# Same curve as the old BacklightControllerBrightness.py: high reading = dark room = dim
def convertToBrightness(data):
    if data >=  850:
        return 10
    elif data >= 500:
        return 50
    elif data >= 450:
        return 80
    elif data >= 400:
        return 110
    elif data >= 350:
        return 130
    elif data >= 300:
        return 180
    elif data >= 180:
        return 200
    elif data >= 20:
        return 220
    else:
        return 0

############
# Only called from the main loop, so the LEDs are driven from one thread.
# Returns the brightness the main display was set to.
def applyLights(sensorBrightness):
    if settings["BACKLIGHT"] == "ON":
        #BCKL-LEVEL moves the whole curve up or down
        screen = min(255, sensorBrightness * settings["BCKL-LEVEL"] // 100)
    else:
        screen = 0
    for led in SCREEN_LEDS:
        piglow.led(led, screen)
    for channel, led in EXT_LEDS.items():
        if settings["EXT-POWER-" + channel] == "ON":
            piglow.led(led, settings["EXT-BRIGHT-" + channel])
        else:
            piglow.led(led, 0)
    piglow.show()
    return screen

############
def load_properties(path):
    props = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    return props

############
# Plays the track in the background with SoundPlay.py, which also fires the knocker.
def play_sound():
    global soundProcess
    if soundProcess is not None and soundProcess.poll() is None:
        print("sound already playing")
        return False
    #re-read every time, so knock markers can be tuned without a restart
    audio = load_properties("config/audio.properties")
    track = "af.soundplay.%s." + AUDIO_TRACK
    print("playing " + audio[track % "track"] + " at volume " + str(settings["VOLUME"]))
    soundProcess = subprocess.Popen(["/usr/bin/python", "SoundPlay.py",
        "-v", str(settings["VOLUME"]),
        "-i", audio["af.soundtrack.path"] + "/" + audio[track % "track"],
        "-s", audio[track % "start"],
        "-t", audio[track % "stop"],
        "-k", audio[track % "knock"]])
    return True

############
def stop_sound():
    if soundProcess is not None and soundProcess.poll() is None:
        print("stopping sound")
        #SoundPlay.py mutes the amp and releases the knocker on SIGTERM
        soundProcess.terminate()

############
def on_message(client, userdata, message):
    recivedMessage = str(message.payload.decode("utf-8")).strip()
    topicPath = message.topic.split("/")
    print("message received " + message.topic + " = " + recivedMessage + (" (retained)" if message.retain else ""))
    if len(topicPath) != 3:
        return
    if topicPath[0] == "stat":
        #only subscribed while restoring: our own last published state
        if restoring and message.retain and topicPath[2] != "RESULT" and topicPath[2] in settings:
            execute_request(topicPath[2], recivedMessage, message.retain)
    elif execute_request(topicPath[2], recivedMessage, message.retain):
        publish_state()

############
def execute_request(item, value, retained):
    global lastChange
    if item == "PLAY":
        #a retained PLAY would start the music on every reconnect
        if retained:
            print("ignoring retained PLAY")
            return False
        return play_sound()
    elif item in SWITCHES:
        if value not in VALID_ON_OFF_VALUES:
            print("the value is not ON or OFF")
            return False
        settings[item] = value
    elif item in NUMBERS:
        low, high = NUMBERS[item]
        #home assistant may send "60.0"
        settings[item] = max(low, min(high, int(float(value))))
    elif item.startswith("EXT-BRIGHT-CH") and value in VALID_ON_OFF_VALUES:
        #old style: ON/OFF sent to the brightness topic
        settings["EXT-POWER-" + item[-3:]] = value
    else:
        print("unknown item " + item)
        return False

    if item == "SOUND" and value == "OFF":
        stop_sound()
    lastChange = time.time()
    return True

############
# retained, so Home Assistant shows the real state after it or the broker restarts
def publish_state():
    for key, value in settings.items():
        client.publish("stat/" + DEVICE_NAME + "/" + key, str(value), retain=True)
    client.publish("stat/" + DEVICE_NAME + "/RESULT", json.dumps(settings), retain=True)

############
def send_telemetry():
    sensorsData = Sensors()
    sensorsData.Local.Temperature1 = 10
    sensorsData.Local.Temperature2 = 12.3
    sensorsData.Local.Light1 = lightSensor.ext_level
    sensorsData.Local.Light2 = lightSensor.int_level
    sensorsData.Local.Backlight = screen
    deviceState = SystemState()
    client.publish("tele/" + DEVICE_NAME + "/SENSOR", json.dumps(sensorsData.reprJSON()))
    client.publish("tele/" + DEVICE_NAME + "/STATE", json.dumps(deviceState.reprJSON()))

############
# Called on every (re)connect. Subscriptions are lost when the broker drops
# the session, so they must be made here and not just once at startup.
def on_connect(client, userdata, flags, rc):
    global connected, lastConnected
    if rc != 0:
        print("connection refused, rc=" + str(rc))
        return
    print("connected to broker")
    connected = True
    lastConnected = time.time()
    client.publish(LWT_TOPIC, "Online", retain=True)
    if restoring:
        #read our retained state before publishing anything, or we would overwrite it
        print("no settings file - restoring settings from retained mqtt state")
        client.subscribe("stat/" + DEVICE_NAME + "/#")
    else:
        start_commands()

############
def start_commands():
    publish_state()
    #retained commands arrive right after this and override the saved settings
    client.subscribe("cmnd/" + DEVICE_NAME + "/#")
    send_telemetry()

############
def on_disconnect(client, userdata, rc):
    global connected, lastConnected
    connected = False
    lastConnected = time.time()
    print("disconnected from broker, rc=" + str(rc) + " - paho will reconnect")

############
# An exception here would kill paho's network thread while the main loop keeps
# sleeping, leaving a "running" process that never reconnects.
def safe_on_message(client, userdata, message):
    try:
        on_message(client, userdata, message)
    except Exception as e:
        print("error handling message on " + message.topic + ": " + repr(e))

audio = load_properties("config/audio.properties")
DEFAULT_SETTINGS["VOLUME"] = min(int(audio["af.soundplay.volume." + AUDIO_TRACK]), MAX_VOLUME)

store = settingsStore(SETTINGS_MOUNT, SETTINGS_FILE)
settings = store.load(DEFAULT_SETTINGS)
savedSettings = dict(settings)
lastChange = 0
#file missing or broken: take the settings from the broker on the first connect
restoring = not store.loaded
restoreStarted = None

amp = MAX9744()
amp.set_volume(0)
soundProcess = None
lastPlayDay = None

lightSensor = sensorLight()
lightSensor.fetchValues()
lightLevel = float(lightSensor.ext_level)
effects = backlightEffects(SCREEN_LEDS)
screen = 0

LWT_TOPIC = "tele/" + DEVICE_NAME + "/LWT"
connected = False
lastConnected = time.time()

print("creating new instance")
# client id must be unique on the broker, otherwise two clients kick each other off
client = mqtt.Client(DEVICE_NAME)
client.username_pw_set(username="iot-hub", password="***REMOVED***")
client.will_set(LWT_TOPIC, "Offline", retain=True)
client.reconnect_delay_set(min_delay=1, max_delay=30)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = safe_on_message
print("connecting to broker")
# connect_async does not fail when network/broker is not up yet at boot
client.connect_async(BROKER_ADDRESS, keepalive=30)
client.loop_start()

lastTelemetry = time.time()

while True:
    time.sleep(0.1)
    now = time.time()

    lightSensor.fetchValues()
    #smooth the reading so the backlight does not jump between levels
    lightLevel = lightLevel * 0.9 + lightSensor.ext_level * 0.1
    screen = applyLights(convertToBrightness(lightLevel))
    if screen > 0 and settings["EFFECTS"] == "ON":
        if effects.doRandomBlink():
            effects.disturbOn(screen)
        if effects.doRandomEffect():
            effects.execRandomEffect(screen)

    today = datetime.now()
    if (today.hour, today.minute) == PLAY_AT and lastPlayDay != today.date():
        lastPlayDay = today.date()
        if settings["SOUND"] == "ON":
            play_sound()
        else:
            print("daily sound is switched off")

    #whatever happened in SoundPlay.py, never leave the amp on afterwards
    if soundProcess is not None and soundProcess.poll() is not None:
        print("sound finished (exit code " + str(soundProcess.returncode) + "), amplifier muted")
        soundProcess = None
        amp.set_volume(0)

    if restoring and connected:
        if restoreStarted is None:
            restoreStarted = now
        elif now - restoreStarted >= RESTORE_TIME:
            restoring = False
            client.unsubscribe("stat/" + DEVICE_NAME + "/#")
            print("restore finished: " + json.dumps(settings))
            #write the file right away, so the next start does not depend on the broker
            savedSettings = {}
            lastChange = 0
            start_commands()

    if settings != savedSettings and now - lastChange >= SAVE_DELAY:
        if store.save(settings):
            savedSettings = dict(settings)
        else:
            #try again later rather than every 0.1s
            lastChange = now

    if connected and now - lastTelemetry >= DELAY_ON_TELEMETRY_UPDATE:
        lastTelemetry = now
        send_telemetry()
    # last resort: exit and let MQTTWrapper.sh restart us
    if not connected and now - lastConnected >= MAX_OFFLINE_TIME:
        print("no broker connection for " + str(MAX_OFFLINE_TIME) + "s - exiting")
        sys.exit(1)
