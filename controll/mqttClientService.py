import paho.mqtt.client as mqtt #import the client1
import time
import sys
import piglow
import json
import subprocess
import os
import signal
import atexit
from datetime import datetime
from Adafruit_MAX9744 import MAX9744
from lib.sensorLight import sensorLight
from lib.backlightEffects import backlightEffects
from lib.settingsStore import settingsStore

DEVICE_NAME="TRANSLITE-1"
#broker address and login, kept out of git (see config/mqtt.properties.example)
MQTT_CONFIG = "config/mqtt.properties"
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

#background radio, stops while the addams music plays
RADIO_URL = "https://stream.ltbr.fm/live"
#seconds between reconnects when the stream drops
RADIO_RETRY = 15
#curl does the https (mpg321 can't), mpg321 -g sets the radio volume on the Pi itself.
#-f: give up on HTTP errors; --speed-*: give up when the stream stalls (normal is ~16kB/s),
#otherwise a connection that stays open without data would keep the radio silent forever.
#Its own logger: if it held our output pipe, MQTTWrapper.sh could not restart us.
RADIO_COMMAND = "(curl -fsSN --connect-timeout 10 --speed-limit 1000 --speed-time 15 '%s' | mpg321 -q -o alsa -g %d -) 2>&1 | logger -t translite-radio"

#NOOBS SETTINGS partition (/dev/mmcblk0p3), mounted read-only
SETTINGS_MOUNT = "/mnt/settings"
SETTINGS_FILE = "translite/settings.json"

#Hard limits for the LEDs. Above this the power supply makes noise (and it
#saves energy). Nothing can set the LEDs higher.
MAX_BACKLIGHT = 154
MAX_EXT_BRIGHTNESS = 154

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
SWITCHES = ["BACKLIGHT", "SOUND", "EFFECTS", "RADIO",
            "EXT-POWER-CH1", "EXT-POWER-CH2", "EXT-POWER-CH3", "EXT-POWER-CH4"]
#name: (min, max)
#BCKL-LEVEL can only dim the curve, never raise it
NUMBERS = {"BCKL-LEVEL": (10, 100),
           "VOLUME": (0, MAX_VOLUME),
           "RADIO-VOLUME": (0, 100),
           "MUSIC-VOLUME": (0, 100),
           "EXT-BRIGHT-CH1": (0, MAX_EXT_BRIGHTNESS), "EXT-BRIGHT-CH2": (0, MAX_EXT_BRIGHTNESS),
           "EXT-BRIGHT-CH3": (0, MAX_EXT_BRIGHTNESS), "EXT-BRIGHT-CH4": (0, MAX_EXT_BRIGHTNESS)}

DEFAULT_SETTINGS = {
    "BACKLIGHT": "ON",
    #percent of the light sensor curve
    "BCKL-LEVEL": 100,
    #master volume: the amplifier, shared by the music and the radio
    "VOLUME": 60,
    #addams music volume on the Pi, percent
    "MUSIC-VOLUME": 100,
    #daily music at PLAY_AT
    "SOUND": "ON",
    #random backlight blinks
    "EFFECTS": "ON",
    "RADIO": "OFF",
    #percent, relative to the addams music (the amplifier VOLUME is shared)
    "RADIO-VOLUME": 30,
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
# (sensor reading, brightness): the old BacklightControllerBrightness.py steps at
# 70%, joined by straight lines so the backlight fades instead of jumping.
# Tops out at MAX_BACKLIGHT. High reading = dark room = dim.
BACKLIGHT_CURVE = [(10, 0), (20, 154), (180, 140), (300, 126), (350, 91),
                   (400, 77), (450, 56), (500, 35), (850, 7)]

def convertToBrightness(data):
    if data <= BACKLIGHT_CURVE[0][0]:
        return BACKLIGHT_CURVE[0][1]
    for (x1, y1), (x2, y2) in zip(BACKLIGHT_CURVE, BACKLIGHT_CURVE[1:]):
        if data <= x2:
            return int(round(y1 + (y2 - y1) * (data - x1) / float(x2 - x1)))
    return BACKLIGHT_CURVE[-1][1]

############
# Only called from the main loop, so the LEDs are driven from one thread.
# Returns the brightness the main display was set to.
def applyLights(sensorBrightness):
    if settings["BACKLIGHT"] == "ON":
        #BCKL-LEVEL dims the whole curve; the cap also covers a bad value from the settings file
        level = min(100, settings["BCKL-LEVEL"])
        screen = min(MAX_BACKLIGHT, sensorBrightness * level // 100)
    else:
        screen = 0
    for led in SCREEN_LEDS:
        piglow.led(led, screen)
    for channel, led in EXT_LEDS.items():
        if settings["EXT-POWER-" + channel] == "ON":
            #capped here too, in case the settings file has a higher value
            piglow.led(led, min(MAX_EXT_BRIGHTNESS, settings["EXT-BRIGHT-" + channel]))
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
def is_running(process):
    return process is not None and process.poll() is None

############
def start_radio():
    global radioProcess, radioGain, lastRadioStart
    radioGain = settings["RADIO-VOLUME"]
    lastRadioStart = time.time()
    #Pi output at full level, same as SoundPlay.py (the saved ALSA state is -17dB)
    subprocess.call(["amixer", "-q", "cset", "numid=1", "0"])
    print("starting radio at radio volume " + str(radioGain))
    #own process group, so stop_radio() can stop curl and mpg321 together
    devnull = open(os.devnull, "w")
    radioProcess = subprocess.Popen(RADIO_COMMAND % (RADIO_URL, radioGain),
                                    shell=True, preexec_fn=os.setsid,
                                    stdout=devnull, stderr=devnull)

############
# Waits until the radio has let go of the audio device.
def stop_radio():
    global radioProcess
    if not is_running(radioProcess):
        radioProcess = None
        return
    print("stopping radio")
    os.killpg(radioProcess.pid, signal.SIGTERM)
    for i in range(20):
        if radioProcess.poll() is not None:
            break
        time.sleep(0.1)
    else:
        os.killpg(radioProcess.pid, signal.SIGKILL)
        radioProcess.wait()
    radioProcess = None

############
# Plays the track in the background with SoundPlay.py, which also fires the knocker.
# Main loop only: the radio is stopped first, the audio output can't play both.
def play_sound():
    global soundProcess, ampLevel
    if is_running(soundProcess):
        print("sound already playing")
        return False
    stop_radio()
    #SoundPlay.py drives the amplifier until it exits
    ampLevel = None
    #re-read every time, so knock markers can be tuned without a restart
    audio = load_properties("config/audio.properties")
    track = "af.soundplay.%s." + AUDIO_TRACK
    print("playing " + audio[track % "track"] + " at volume " + str(settings["VOLUME"]))
    #stdin stays open so volume changes reach the music while it plays
    soundProcess = subprocess.Popen(["/usr/bin/python", "SoundPlay.py",
        "-v", str(settings["VOLUME"]),
        "-m", str(settings["MUSIC-VOLUME"]),
        "-i", audio["af.soundtrack.path"] + "/" + audio[track % "track"],
        "-s", audio[track % "start"],
        "-t", audio[track % "stop"],
        "-k", audio[track % "knock"]], stdin=subprocess.PIPE)
    publish_music()
    return True

############
# live volume change for the music that is playing right now (see SoundPlay.py)
def send_to_music(item, value):
    if is_running(soundProcess):
        try:
            soundProcess.stdin.write(item + " " + str(value) + "\n")
            soundProcess.stdin.flush()
        except IOError as e:
            print("could not send " + item + " to the music: " + repr(e))

############
def stop_sound():
    global musicRequested
    musicRequested = False
    if is_running(soundProcess):
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
    global lastChange, musicRequested
    if item == "PLAY" or (item == "MUSIC" and value == "ON"):
        #a retained PLAY would start the music on every reconnect
        if retained:
            print("ignoring retained " + item)
            return False
        #started by the main loop, which owns the radio and the amplifier
        musicRequested = True
        return False
    elif item == "MUSIC" and value == "OFF":
        stop_sound()
        return False
    elif item in SWITCHES:
        if value not in VALID_ON_OFF_VALUES:
            print("the value is not ON or OFF")
            return False
        settings[item] = value
    elif item in NUMBERS:
        low, high = NUMBERS[item]
        #home assistant may send "60.0"
        settings[item] = max(low, min(high, int(float(value))))
        if item in ("VOLUME", "MUSIC-VOLUME"):
            send_to_music(item, settings[item])
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
    publish_music()

############
# ON while the addams music plays - state of the MUSIC switch in home assistant
def publish_music():
    client.publish("stat/" + DEVICE_NAME + "/MUSIC", "ON" if is_running(soundProcess) else "OFF", retain=True)

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

############
# Exits with a clear message instead of failing later in paho. The pause stops
# MQTTWrapper.sh from restarting us (and filling the log) every few seconds.
def load_mqtt_config():
    try:
        mqttConfig = load_properties(MQTT_CONFIG)
        for key in ["mqtt.broker", "mqtt.username", "mqtt.password"]:
            if not mqttConfig.get(key):
                raise ValueError(key + " is missing")
        return mqttConfig
    except Exception as e:
        print("cannot read " + MQTT_CONFIG + ": " + repr(e) + " - copy config/mqtt.properties.example and fill it in")
        time.sleep(60)
        sys.exit(1)

mqttConfig = load_mqtt_config()
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
#what we last set the amplifier to, None while SoundPlay.py drives it
ampLevel = 0
soundProcess = None
musicRequested = False
lastPlayDay = None
radioProcess = None
radioGain = None
lastRadioStart = 0

#a radio left over from a killed instance would hold the audio device
subprocess.call(["pkill", "-f", RADIO_URL])

############
# Runs on every exit (also errors and the offline exit): no radio or amp left behind.
def shutdown():
    stop_radio()
    amp.set_volume(0)
    print("stopped")

def on_sigterm(signum, frame):
    #turns SIGTERM into a normal exit, so shutdown() runs
    sys.exit(0)

atexit.register(shutdown)
signal.signal(signal.SIGTERM, on_sigterm)

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
client.username_pw_set(username=mqttConfig["mqtt.username"], password=mqttConfig["mqtt.password"])
client.will_set(LWT_TOPIC, "Offline", retain=True)
client.reconnect_delay_set(min_delay=1, max_delay=30)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = safe_on_message
print("connecting to broker")
# connect_async does not fail when network/broker is not up yet at boot
client.connect_async(mqttConfig["mqtt.broker"], keepalive=30)
client.loop_start()

lastTelemetry = time.time()

while True:
    time.sleep(0.1)
    now = time.time()

    lightSensor.fetchValues()
    #smooth the reading so the backlight fades over ~2s instead of jumping
    lightLevel = lightLevel * 0.95 + lightSensor.ext_level * 0.05
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
            musicRequested = True
        else:
            print("daily sound is switched off")

    if musicRequested:
        musicRequested = False
        play_sound()

    if soundProcess is not None and not is_running(soundProcess):
        print("sound finished (exit code " + str(soundProcess.returncode) + ")")
        soundProcess = None
        #SoundPlay.py always mutes the amplifier when it ends
        ampLevel = 0
        publish_music()

    #the radio plays whenever it is on and the addams music is not playing
    if not is_running(soundProcess):
        if settings["RADIO"] == "ON":
            if radioProcess is not None and not is_running(radioProcess):
                print("radio stopped (exit code " + str(radioProcess.returncode) + "), retrying in " + str(RADIO_RETRY) + "s")
                radioProcess = None
            if is_running(radioProcess) and radioGain != settings["RADIO-VOLUME"] and now - lastChange >= 2:
                #radio volume changed: restart with the new gain once the slider has settled
                stop_radio()
                lastRadioStart = 0
            if radioProcess is None and now - lastRadioStart >= RADIO_RETRY:
                start_radio()
        elif radioProcess is not None:
            stop_radio()

        #amplifier on only while the radio plays; never left on after the music
        wantAmp = settings["VOLUME"] if is_running(radioProcess) else 0
        if ampLevel != wantAmp:
            amp.set_volume(wantAmp)
            ampLevel = wantAmp

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
