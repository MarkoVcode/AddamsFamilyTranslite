import paho.mqtt.client as mqtt #import the client1
import time
import sys
import piglow
import json
import subprocess
from datetime import datetime
from lib.sensorLight import sensorLight
from lib.backlightEffects import backlightEffects

DEVICE_NAME="TRANSLITE-1"
BROKER_ADDRESS="192.168.1.20"
ITEMS_AD=[]
ITEMS_PC=["BCKL-BRIGHT", "VOLUME", "EXT-BRIGHT-CH1", "EXT-BRIGHT-CH2", "EXT-BRIGHT-CH3", "EXT-BRIGHT-CH4"]
ITEMS_LOGICAL=["BCKL-AUTOMODE"]
ITEMS_TRIGGER=["PLAY"]
VALID_ON_OFF_VALUES=["ON", "OFF"]

#seconds
DELAY_ON_TELEMETRY_UPDATE = 60
MAX_OFFLINE_TIME = 300

#daily music + knocker, local time (hour, minute)
PLAY_AT = (12, 0)
AUDIO_TRACK = "1"
#MAX9744 amplifier range
MAX_VOLUME = 63

#Main display 
C_1 = 13
C_2 = 14
C_3 = 15
C_4 = 16
C_5 = 5
C_6 = 4
C_7 = 18
C_8 = 2

#External LED
#HEADER 3:
E_3 = 6
#HEADER 4:
E_4 = 3
#HEADER 2:
E_2 = 12
#HEADER 1:
E_1 = 11

class SensorList:
    def __init__(self):
        self.Temperature1 = None
        self.Temperature2 = None
        self.Light1 = None
        self.Light2 = None
    def reprJSON(self):
        return dict(Temperature1=self.Temperature1, Temperature2=self.Temperature2, Light1=self.Light1, Light2=self.Light2)   

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

class DeviceState:
    def __init__(self):
        self.ch1 = 0
        self.ch1State = "OFF"
        self.ch2 = 0
        self.ch2State = "OFF"
        self.ch3 = 0
        self.ch3State = "OFF"
        self.ch4 = 0
        self.ch4State = "OFF"
        self.backl = 0
        #backlight is on and follows the light sensor until told otherwise
        self.backlState = "ON"
        self.backlAuto = "ON"
        self.vol = 0

    def setADBrightness(self, item, value):
        value = int(value)
        if item == 'BCKL-BRIGHT':
            #a brightness from mqtt overrides the light sensor
            self.backl = value
            self.backlAuto = "OFF"
        elif item == 'VOLUME':
            self.vol = min(value, MAX_VOLUME)
        elif item == 'EXT-BRIGHT-CH1':
            self.ch1 = value
        elif item == 'EXT-BRIGHT-CH2':
            self.ch2 = value
        elif item == 'EXT-BRIGHT-CH3':
            self.ch3 = value
        elif item == 'EXT-BRIGHT-CH4':
            self.ch4 = value
        return True

    def setADOnOff(self, item, value):
        if item == 'BCKL-BRIGHT':
            self.backlState = value
        elif item == 'EXT-BRIGHT-CH1':
            self.ch1State = value
        elif item == 'EXT-BRIGHT-CH2':
            self.ch2State = value
        elif item == 'EXT-BRIGHT-CH3':
            self.ch3State = value
        elif item == 'EXT-BRIGHT-CH4':
            self.ch4State = value
        return True

    def setAutoMode(self, value):
        self.backlAuto = value
        return True

    # only called from the main loop, so the LEDs are driven from one thread.
    # Returns the brightness the main display was set to.
    def setDeviceStates(self, sensorBrightness):
        if self.backlState != 'ON':
            screen = 0
        elif self.backlAuto == 'ON':
            screen = sensorBrightness
        else:
            screen = int(self.backl)
        self.setScreenBrightness(screen)

        if self.ch1State == 'ON':       
            self.setChannelBrightness("CH1", int(self.ch1))
        else:
            self.setChannelBrightness("CH1", 0)
       
        if self.ch2State == 'ON':
            self.setChannelBrightness("CH2", int(self.ch2))
        else:
            self.setChannelBrightness("CH2", 0)
     
        if self.ch3State == 'ON':
            self.setChannelBrightness("CH3", int(self.ch3))
        else:
            self.setChannelBrightness("CH3", 0)

        if self.ch4State == 'ON':
            self.setChannelBrightness("CH4", int(self.ch4))
        else:
            self.setChannelBrightness("CH4", 0)

        piglow.show()
        return screen

    def setChannelBrightness(self, channel, brigthness):
        if channel == 'CH1':
            piglow.led(E_1,brigthness)
        elif channel == 'CH2':
            piglow.led(E_2,brigthness)
        elif channel == 'CH3':
            piglow.led(E_3,brigthness)
        elif channel == 'CH4':
            piglow.led(E_4,brigthness)


    def setScreenBrightness(self, brigthness):
        piglow.led(C_1,brigthness)
        piglow.led(C_2,brigthness)
        piglow.led(C_3,brigthness)
        piglow.led(C_4,brigthness)
        piglow.led(C_5,brigthness)
        piglow.led(C_6,brigthness)
        piglow.led(C_7,brigthness)
        piglow.led(C_8,brigthness)


    def reprJSON(self):
        return dict(CH1=self.ch1, CH2=self.ch2, CH3=self.ch3, CH4=self.ch4, VOL=self.vol, BACKL=self.backl, BACKLAUTO=self.backlAuto)

############
# Same mapping as the old BacklightControllerBrightness.py: high reading = dark room = dim
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
    track = "af.soundplay.%s." + AUDIO_TRACK
    print("playing " + audio[track % "track"] + " at volume " + str(deviceStates.vol))
    soundProcess = subprocess.Popen(["/usr/bin/python", "SoundPlay.py",
        "-v", str(deviceStates.vol),
        "-i", audio["af.soundtrack.path"] + "/" + audio[track % "track"],
        "-s", audio[track % "start"],
        "-t", audio[track % "stop"],
        "-k", audio[track % "knock"]])
    return True

############
def on_message(client, userdata, message):
    recivedMessage = str(message.payload.decode("utf-8"))
    topicPath = message.topic.split("/")
    print("message received " ,recivedMessage)
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    if (execute_request(topicPath[2], recivedMessage)):
        send_confirmation(topicPath, message.topic, recivedMessage)

############
def send_confirmation(topicPath, topic, message):
    statTopic = topic.replace("cmnd", "stat")
    client.publish(statTopic,message)
    resultMessage = json.dumps(deviceStates.reprJSON())
    client.publish("stat/" + DEVICE_NAME + "/RESULT",resultMessage)

############
def send_telemetry():
    sensorsData = Sensors()
    sensorsData.Local.Temperature1 = 10
    sensorsData.Local.Temperature2 = 12.3
    sensorsData.Local.Light1 = lightSensor.ext_level
    sensorsData.Local.Light2 = lightSensor.int_level
    deviceState = SystemState()
    client.publish("tele/" + DEVICE_NAME + "/SENSOR", json.dumps(sensorsData.reprJSON()))
    client.publish("tele/" + DEVICE_NAME + "/STATE", json.dumps(deviceState.reprJSON()))
#create JSON here with sensors and timestamps:

############
def execute_request(item, value):
    if item in ITEMS_AD:
        values = value.split(",")
        value = values[0]
        if 0 <= int(value) <= 255:
            print("the value is valid AD - execute")
            return deviceStates.setADBrightness(item, value)
        else:
            print("the value is not between 0 and 255")
            return False
    elif item in ITEMS_LOGICAL:
        if value in VALID_ON_OFF_VALUES:
            print("the value is valid LOGIC - execute")
            return deviceStates.setAutoMode(value)
        else:
            print("the value is not ON or OFF")
            return False
    elif item in ITEMS_PC:
        if value == "ON" or value == "OFF":
            print("the value is valid ON/OFF - execute")
            return deviceStates.setADOnOff(item, value)
        elif 0 <= int(value) <= 255:
            print("the value is valid AD - execute")
            return deviceStates.setADBrightness(item, value)
        else:
            print("the value is not 0 - 255")
            return False
    elif item in ITEMS_TRIGGER:
        return play_sound()


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
    client.subscribe("cmnd/" + DEVICE_NAME + "/#")
    client.publish(LWT_TOPIC, "Online", retain=True)
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

deviceStates = DeviceState()
lightSensor = sensorLight()
lightSensor.fetchValues()
lightLevel = float(lightSensor.ext_level)
effects = backlightEffects([C_1, C_2, C_3, C_4, C_5, C_6, C_7, C_8])

audio = load_properties("config/audio.properties")
#volume until mqtt sets one
deviceStates.vol = min(int(audio["af.soundplay.volume." + AUDIO_TRACK]), MAX_VOLUME)
soundProcess = None
lastPlayDay = None

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
    screen = deviceStates.setDeviceStates(convertToBrightness(lightLevel))
    if screen > 0:
        if effects.doRandomBlink():
            effects.disturbOn(screen)
        if effects.doRandomEffect():
            effects.execRandomEffect(screen)

    today = datetime.now()
    if (today.hour, today.minute) == PLAY_AT and lastPlayDay != today.date():
        lastPlayDay = today.date()
        play_sound()

    if connected and now - lastTelemetry >= DELAY_ON_TELEMETRY_UPDATE:
        lastTelemetry = now
        send_telemetry()
    # last resort: exit and let MQTTWrapper.sh restart us
    if not connected and now - lastConnected >= MAX_OFFLINE_TIME:
        print("no broker connection for " + str(MAX_OFFLINE_TIME) + "s - exiting")
        sys.exit(1)
