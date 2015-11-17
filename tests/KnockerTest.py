import RPi.GPIO as GPIO  
import time  
# blinking function  
def blink(pin):  
        GPIO.output(pin,GPIO.HIGH)  
        time.sleep(1)  
        GPIO.output(pin,GPIO.LOW)  
        time.sleep(1)  
        return  
# to use Raspberry Pi board pin numbers  
GPIO.setmode(GPIO.BOARD)  
# set up GPIO output channel  
GPIO.setup(38, GPIO.OUT)  
GPIO.setup(40, GPIO.OUT)
# blink GPIO17 50 times  
for i in range(0,50):  
        blink(38)
#38 - RIGHT
	blink(40)
#40 left
GPIO.cleanup()  
