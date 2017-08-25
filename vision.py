import base64
import os
import pyaudio
import wave
import time
import socket
import subprocess
from googleapiclient import discovery
from gtts import gTTS
from picamera import PiCamera
import datetime
from signal import pause
from time import sleep
from pydub import AudioSegment
from subprocess import check_call, Popen
from gpiozero import LED, Button

camera = PiCamera()
camera.resolution = (640, 480)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 1
WAVE_OUTPUT_FILENAME = "output.wav"
timestamp = str(datetime.date.today())
start_command = ""
REMOTE_SERVER = "vision.googleapis.com"
sound = None
button = Button(26, hold_time=2)
led = LED(5)

def device_ready():
    led.on()
    os.system("aplay /home/pi/audio.wav")
    sleep(1)
    if try_network():
        os.system("aplay /home/pi/network.wav")
        sleep(1)
        os.system("aplay /home/pi/ready.wav")
    else:
        os.system("aplay /home/pi/waiting.wav")
        sleep(1)
    led.off()

def try_network():
    try:
        host = socket.gethostbyname(REMOTE_SERVER)
        s = socket.create_connection((host, 80), 2)
        return True
    except:
        os.system("aplay /home/pi/waiting.wav")
        sleep(2)
        return False

def takephoto():
    start_time = time.time()
    camera.capture('/home/pi/image.jpg')
    print("takephoto took %s seconds ---" % (time.time() - start_time))
    if try_network():
	led.on()
        google_vision()
        led.off()

def speak(words):
    start_time = time.time()
    tts = gTTS(text=words, lang='en')
    tts.save("/home/pi/output.mp3")
    sound = subprocess.Popen(["mpg321","-q","/home/pi/output.mp3"])
    print("Speech took %s seconds ---" % (time.time() - start_time))

def google_vision():
    start_time = time.time()
    os.system("aplay /home/pi/thinking.wav")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/vision-3c9712f80773.json"
    service = discovery.build('vision', 'vs1',
                              discoveryServiceUrl="https://vision.googleapis.com/$discovery/rest?version=v1")
    photo_file = "/home/pi/image.jpg"
    with open(photo_file, 'rb') as image:
        image_content = base64.b64encode(image.read())
        service_request = service.images().annotate(
            body={
                'requests': [{
                    'image': {
                        'content': image_content
                    },
                    'features': [{
                        'type': 'LABEL_DETECTION',
                        'maxResults': 1,
                    },
                    ]
                }]
            })
    response = service_request.execute()
    try:
        labels = response['responses'][0]['labelAnnotations']
        for label in labels:
            label_val = label['description']
            print(label_val)
            speak(label_val)
    except KeyError:
        print("N/A labels found")
        speak("Not a hot dog")
    print('\n')
    print('\n= = = = = Completed = = = = =\n')
    print("Google Vision took %s seconds ---" % (time.time() - start_time))

def shutdown():
    led.on()
    os.system("aplay /home/pi/shutdown.wav")
    check_call(['sudo', 'poweroff'])

def main():
    device_ready()
    while True:
        button.when_held = shutdown
        button.when_released = takephoto


main()

