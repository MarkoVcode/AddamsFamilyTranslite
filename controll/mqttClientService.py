import paho.mqtt.client as mqtt #import the client1
import time
import piglow

DEVICE_NAME="TRANSLITE-1"
BROKER_ADDRESS="192.168.1.7"
ITEMS_AD=["EXT-BRIGHT-CH1", "EXT-BRIGHT-CH2", "EXT-BRIGHT-CH3", "EXT-BRIGHT-CH4", "BCKL-BRIGHT", "VOLUME"]
ITEMS_LOGICAL=["BCKL-AUTOMODE"]
VALID_ON_OFF_VALUES=["ON", "OFF"]

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

############
def on_message(client, userdata, message):
    # process here the request
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
    if topicPath[2] in ITEMS_AD:
        resultMessage="{\"" + topicPath[2] + "\": " + message + "}"
    else:
        resultMessage="{\"" + topicPath[2] + "\": \"" + message + "\"}"
    client.publish("stat/" + DEVICE_NAME + "/RESULT",resultMessage)

############
def send_telemetry():
    client.publish("tele/" + DEVICE_NAME + "/LWT", "Online")

############
def execute_request(item, value):
    if item in ITEMS_AD:
        values = value.split(",")
        value = values[0]
        if 0 <= int(value) <= 255:
            print("the value is valid AD - execute")
            return setADBrightness(item, value)
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

def setADBrightness(item, value):
    value = int(value)
    if item == 'BCKL-BRIGHT':
        setScreenBrightness(value)
    elif item == 'EXT-BRIGHT-CH1':
        setChannelBrightness("CH1", value)
    elif item == 'EXT-BRIGHT-CH2':
        setChannelBrightness("CH2", value)
    elif item == 'EXT-BRIGHT-CH3':
        setChannelBrightness("CH3", value)
    elif item == 'EXT-BRIGHT-CH4':
        setChannelBrightness("CH4", value)
    return True

############
def setScreenBrightness(brigthness):
    piglow.led(C_1,brigthness)
    piglow.led(C_2,brigthness)
    piglow.led(C_3,brigthness)
    piglow.led(C_4,brigthness)
    piglow.led(C_5,brigthness)
    piglow.led(C_6,brigthness)
    piglow.led(C_7,brigthness)
    piglow.led(C_8,brigthness)
    piglow.show()

############
def setChannelBrightness(channel, brigthness):
    if channel == 'CH1':
        piglow.led(E_1,brigthness)
    elif channel == 'CH2':
        piglow.led(E_2,brigthness)
    elif channel == 'CH3':
        piglow.led(E_3,brigthness)
    elif channel == 'CH4':
        piglow.led(E_4,brigthness)
    piglow.show()

print("creating new instance")
client = mqtt.Client("P1") #create new instance
client.on_message=on_message #attach function to callback
print("connecting to broker")
client.connect(BROKER_ADDRESS) #connect to broker
client.loop_start() #start the loop

client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH1")
client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH2")
client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH3")
client.subscribe("cmnd/TRANSLITE-1/EXT-BRIGHT-CH4")
client.subscribe("cmnd/TRANSLITE-1/BCKL-BRIGHT")
client.subscribe("cmnd/TRANSLITE-1/BCKL-AUTOMODE")
client.subscribe("cmnd/TRANSLITE-1/VOLUME")

send_telemetry()

while True:
	time.sleep(0.1) # wait
#client.loop_stop() #stop the loop
