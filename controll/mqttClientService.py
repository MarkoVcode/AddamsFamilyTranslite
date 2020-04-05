import paho.mqtt.client as mqtt #import the client1
import time

DEVICE_NAME="TRANSLITE-1"
BROKER_ADDRESS="192.168.1.7"
ITEMS_AD=["EXT-BRIGHT-CH1", "EXT-BRIGHT-CH2", "EXT-BRIGHT-CH3", "EXT-BRIGHT-CH4", "BCKL-BRIGHT", "VOLUME"]
ITEMS_LOGICAL=["BCKL-AUTOMODE"]
VALID_ON_OFF_VALUES=["ON", "OFF"]

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
def execute_request(item, value):
    if item in ITEMS_AD:
        print(value)
        if 0 <= int(value) <= 255:
            print("the value is valid AD - execute")
            return True
        else:
            return False
    elif item in ITEMS_LOGICAL:
        if value in VALID_ON_OFF_VALUES:
            print("the value is valid LOGIC - execute")
            return True
        else:
            return False


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

while True:
	time.sleep(0.1) # wait
#client.loop_stop() #stop the loop
