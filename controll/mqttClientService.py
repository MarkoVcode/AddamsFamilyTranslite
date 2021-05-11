import paho.mqtt.client as mqtt #import the client1
import time
import piglow
import json
from datetime import datetime
from lib.sensorLight import sensorLight

DEVICE_NAME="TRANSLITE-1"
BROKER_ADDRESS="192.168.1.20"
ITEMS_AD=[]
ITEMS_PC=["BCKL-BRIGHT", "VOLUME", "EXT-BRIGHT-CH1", "EXT-BRIGHT-CH2", "EXT-BRIGHT-CH3", "EXT-BRIGHT-CH4"]
ITEMS_LOGICAL=["BCKL-AUTOMODE"]
VALID_ON_OFF_VALUES=["ON", "OFF"]

DELAY_ON_TELEMETRY_UPDATE = 600

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
        self.backlState = "OFF"

	self.backlAuto = "OFF"
        self.vol = 0
    
    def setADBrightness(self, item, value):
        value = int(value)
        if item == 'BCKL-BRIGHT':
            self.backl = value
        elif item == 'EXT-BRIGHT-CH1':
            self.ch1 = value
        elif item == 'EXT-BRIGHT-CH2':
            self.ch2 = value
        elif item == 'EXT-BRIGHT-CH3':
            self.ch3 = value
        elif item == 'EXT-BRIGHT-CH4':
            self.ch4 = value

        self.setDeviceStates()
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

        self.setDeviceStates()
        return True


    def setDeviceStates(self):
        if self.backlState == 'ON': 
            self.setScreenBrightness(int(self.backl))
        else:
            self.setScreenBrightness(0)

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

	return True

    def setChannelBrightness(self, channel, brigthness):
        if channel == 'CH1':
            piglow.led(E_1,brigthness)
        elif channel == 'CH2':
            piglow.led(E_2,brigthness)
        elif channel == 'CH3':
            piglow.led(E_3,brigthness)
        elif channel == 'CH4':
            piglow.led(E_4,brigthness)
        piglow.show()


    def setScreenBrightness(self, brigthness):
        piglow.led(C_1,brigthness)
        piglow.led(C_2,brigthness)
        piglow.led(C_3,brigthness)
        piglow.led(C_4,brigthness)
        piglow.led(C_5,brigthness)
        piglow.led(C_6,brigthness)
        piglow.led(C_7,brigthness)
        piglow.led(C_8,brigthness)
        piglow.show()


    def reprJSON(self):
        return dict(CH1=self.ch1, CH2=self.ch2, CH3=self.ch3, CH4=self.ch4, VOL=self.vol, BACKL=self.backl, BACKLAUTO=self.backlAuto)

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
    sensorsData.Local.Light1 = 33222
    sensorsData.Local.Light2 = 321212
    deviceState = SystemState()
    client.publish("tele/" + DEVICE_NAME + "/LWT", "Online")
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
            return True
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
            print("the value is not 0 - 100 pcent")
            return False


deviceStates = DeviceState()

print("creating new instance")
client = mqtt.Client("P1") #create new instance
client.username_pw_set(username="iot-hub", password="i0t-4ub")
client.on_message=on_message #attach function to callback
print("connecting to broker")
client.connect(BROKER_ADDRESS) #connect to broker
client.loop_start() #start the loop

#client.on_connect = on_connect
#client.on_disconnect = on_disconnect

client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH1")
client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH2")
client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH3")
client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH4")
client.subscribe("cmnd/TRANSLITE-1/BCKL-BRIGHT")
client.subscribe("cmnd/TRANSLITE-1/BCKL-AUTOMODE")
client.subscribe("cmnd/TRANSLITE-1/VOLUME")

delayTelemetry = 0

send_telemetry()

while True:
	time.sleep(0.1) # wait
	if  delayTelemetry >= DELAY_ON_TELEMETRY_UPDATE:
		delayTelemetry = 0
		send_telemetry()
	else:
		delayTelemetry = delayTelemetry + 1
#client.loop_stop() #stop the loop
