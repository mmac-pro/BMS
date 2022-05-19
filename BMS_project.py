from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
import RPi.GPIO as GPIO
import Freenove_DHT as DHT
import time
import threading
import json
import requests

#define GPIO pins
blueLED = 36
redLED = 38
greenLED = 40
blueBTN = 33
redBTN = 35
greenBTN = 37
DHTPin = 13
sensorPin = 11

PCF8574_address = 0x27 #I2C address of the PCF8574
PCF8574A_address = 0x3F #I2C address of the PCF8574

#setup board,light,and button inputs/outputs
GPIO.setmode(GPIO.BOARD) #sets pin layout
GPIO.setwarnings(False) #disable warning
GPIO.setup(blueBTN,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(redBTN,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(greenBTN,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(blueLED,GPIO.OUT)
GPIO.setup(redLED,GPIO.OUT)
GPIO.setup(greenLED,GPIO.OUT)
GPIO.setup(sensorPin,GPIO.IN)

#set LEDs to begin off
GPIO.output(blueLED,GPIO.LOW)
GPIO.output(redLED,GPIO.LOW)
GPIO.output(greenLED,GPIO.LOW)

#Event listener
GPIO.add_event_detect(blueBTN,GPIO.RISING)
GPIO.add_event_detect(redBTN,GPIO.RISING)
GPIO.add_event_detect(greenBTN,GPIO.RISING)

#global variables
door = 0   #door begins closed
light = 0  #light begins off
hvac = 0   #hvac begins off
weather = 65 #default weather to display
temp = 68     #default room temperature
humid = 69    #most recent reading from CIMIS data
high = 85  #highest temp a user can set
room = 70  #default room temp
low = 65   #lowest room temp a user can set
measure = []   #list to keep track of last 3 temp measurements
D = ["SAFE","OPEN"]  #door state
L = ["OFF","ON"]     #light state
H = ["OFF","AC","HEAT"] #HVAC state

'''data = requests.get =(http://et.water.ca.gov/api/data?appKey=2d619f8e-a1e6-4a83-a72e-82f96e87ee58 &targets= 7 &startDate=2021-06-09 &endDate=2021-06-09 &dataItems=hly-rel-hum)
json_data = json.loads(data.text)'''

#function to turn the LCD on
def LCD_on():
    mcp.output(3,1)  #turn on LCD backlight
    lcd.begin(16,2)  #set number of LCD lines/columns
    lcd.setCursor(0,0) #set cursor position
    time.sleep(1)

#function for motion sensor
def motion():
    global light
    if(GPIO.input(sensorPin) == GPIO.HIGH):
        if(light == 0):
            light = 1
            GPIO.output(greenLED, GPIO.HIGH)
            time.sleep(2)
    else:
        light = 0
        GPIO.output(greenLED,GPIO.LOW)


#DHT function measure temperature
def DHT_temp():
    global temp
    global humid

    dht = DHT.DHT(DHTPin)
    for i in range(0,15):
        chk = dht.readDHT11()
        t = dht.temperature
        if(chk is dht.DHTLIB_OK and t != -999):
            if(len(measure) < 3 and t != -999):
                measure.append(t)
            else:
                measure.remove(measure[0])
            break;
    print(measure)
    time.sleep(1)


#function to monitor temperature
def HVAC_monitor():
    global room,weather,humid,temp,hvac,door

    if(len(measure) == 3):
        temp = sum(measure)/3
        temp = round((temp * (9/5)) + 32)  #convert from C to F
    weather = round(temp + (0.05*humid))

    if(weather == room or weather - room == 3 or room - weather == 3 ):
        hvac = 0
        GPIO.output(blueLED,GPIO.LOW)
        GPIO.output(redLED,GPIO.LOW)
        lcd.message('   HVAC OFF   ')
        time.sleep(3)
        lcd.clear()
    elif(weather > room and weather - room > 3 and door == 0):
        hvac = 1
        lcd.clear()
        GPIO.output(blueLED,GPIO.HIGH)
        GPIO.output(redLED,GPIO.LOW)
        lcd.message('   HVAC AC   ')
        time.sleep(3)
        lcd.clear()
    elif(weather < room  and room - weather > 3 and door == 0):
        hvac = 2
        lcd.clear()
        GPIO.output(redLED,GPIO.HIGH)
        GPIO.output(blueLED,GPIO.LOW)
        lcd.message('   HVAC HEAT  ')
        time.sleep(3)
        lcd.clear()

#function for security system
def security():
    global door,hvac

    if(GPIO.event_detected(greenBTN)):
        #checks if door is open
        if(door == 0):
            door = 1
            hvac = 0                        #set HVAC to off state
            GPIO.output(blueLED,GPIO.LOW)   #turn off AC light
            GPIO.output(redLED,GPIO.LOW)    #turn of HEAT light
            lcd.clear()
            lcd.message('DOOR/WINDOW OPEN'+ '\n')
            lcd.message('HVAC OFF')
            time.sleep(3)
            lcd.clear()
        elif(door == 1):
            door = 0
            lcd.clear()
            lcd.message('DOOR/WINDOW SAFE')
            time.sleep(3)

#function to show main display
def display():
    global weather,room,door,hvac,light
    lcd.clear()
    #increases user/room temperature based on button input
    if(GPIO.event_detected(blueBTN)):
        #check if user has set to lowest temp
        if(room > 65):
            room -= 1
    if(GPIO.event_detected(redBTN)):
        #check if user has set to highest temp
        if(room < 85):
            room += 1
    lcd.message(str(weather) + '/' + str(room)+'     D:'+D[door]+'\n')
    lcd.message('H:'+H[hvac]+'      L:'+L[light])

try:
    mcp = PCF8574_GPIO(PCF8574_address)
except:
    try:
        mcp = PCF8574_GPIO(PCF8574A_address)
    except:
        print('I2C Address Error!')
        exit(1)

#create LCD, passing in MCP GPIO adapter
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp)

while True:
    LCD_on()
    t1 = threading.Thread(target=display)
    t1.daemon = True
    t1.start()
    motion()
    DHT_temp()
    HVAC_monitor()
    security()



