#!/usr/bin/env python
progname = "motion_track.py"
ver = "version 1.30"

print("%s %s motion tracking using python2 or 3 and OpenCV" % (progname, ver))

import os
mypath=os.path.abspath(__file__) 
baseDir=mypath[0:mypath.rfind("/")+1] 
baseFileName=mypath[mypath.rfind("/")+1:mypath.rfind(".")]
progName = os.path.basename(__file__)
configFilePath = baseDir + "config.py"
from config import *

# import the necessary packages
import logging
import time
import cv2
import RPi.GPIO as GPIO
import math

from picamera.array import PiRGBArray
from picamera import PiCamera
from threading import Thread

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
 
#set GPIO Pins
GPIO_TRIGGER = 7
GPIO_ECHO = 12
 
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

#----------------------------------------------------------------------------------------------- 
def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance
    

if debug:
    '''
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(funcName)-10s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
    '''

    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(funcName)-10s %(message)s',
                    datefmt='%H:%M')

#-----------------------------------------------------------------------------------------------
class PiVideoStream:
    def __init__(self, resolution=(CAMERA_WIDTH, CAMERA_HEIGHT), framerate=CAMERA_FRAMERATE, rotation=0, hflip=False, vflip=False):
        # initialize the camera and stream
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.rotation = rotation
        self.camera.framerate = framerate
        self.camera.hflip = hflip
        self.camera.vflip = vflip
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture,
            format="bgr", use_video_port=True)

        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self.stopped = False

    def start(self):
        # start the thread to read frames from the video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)

            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True

#-----------------------------------------------------------------------------------------------
def show_FPS(start_time,frame_count):
    if debug:
        if frame_count >= FRAME_COUNTER:
            duration = float(time.time() - start_time)
            FPS = float(frame_count / duration)
            logging.info("Processing at %.2f fps last %i frames", FPS, frame_count)
            frame_count = 0
            start_time = time.time()
        else:
            frame_count += 1
    return start_time, frame_count

#-----------------------------------------------------------------------------------------------
def track():
    image1 = vs.read()   # initialize image1 (done once)
    try:
        grayimage1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    except:
        vs.stop()
        print("Problem Connecting To Camera Stream.")
        print("Restarting Camera.  One Moment Please .....")
        time.sleep(4)
        return

    if window_on:
        print("Press q in window Quits")
    else:
        print("Press ctrl-c to Quit")
    print("Start Motion Tracking ....")

    if not debug:
        print("Note: Console Messages Supressed per debug=%s" % debug)

    big_w = int(CAMERA_WIDTH * WINDOW_BIGGER)
    big_h = int(CAMERA_HEIGHT * WINDOW_BIGGER)
    cx, cy, cw, ch = 0, 0, 0, 0   # initialize contour center variables
    frame_count = 0  #initialize for show_fps
    start_time = time.time() #initialize for show_fps

    still_scanning = True
    while still_scanning:
        # initialize variables
        motion_found = False
        biggest_area = MIN_AREA
        image2 = vs.read()  # initialize image2        
        grayimage2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        if show_fps:
            start_time, frame_count = show_FPS(start_time, frame_count)
        # Get differences between the two greyed images
        differenceimage = cv2.absdiff(grayimage1, grayimage2)
        grayimage1 = grayimage2  # save grayimage2 to grayimage1 ready for next image2
        differenceimage = cv2.blur(differenceimage,(BLUR_SIZE,BLUR_SIZE))
        # Get threshold of difference image based on THRESHOLD_SENSITIVITY variable
        retval, thresholdimage = cv2.threshold( differenceimage, THRESHOLD_SENSITIVITY, 255, cv2.THRESH_BINARY )
        try:
            thresholdimage, contours, hierarchy = cv2.findContours( thresholdimage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE )
        except:
            contours, hierarchy = cv2.findContours( thresholdimage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE )

        # Ultrasonic Tracking
        dist = distance()
        dist_inch = int(dist / 2.54)
        
        '''
        if ( 100 < dist < 200):
            dist_inch = int(dist / 2.54)
            dist_str = str(dist_inch)
            print ("Measured Distance = %.0f cm" % dist_int)
            os.system("flite -t 'Warning " + dist_str + " inches'")
        elif (dist <100):
            dist_inch = dist_int / 2.54
            print ("Measured Distance = %.0f cm" % dist_int)
            os.system("flite -t 'Too Close " + dist_str + " inches'")
        '''

        if contours != ():
            total_contours = len(contours)  # Get total number of contours
            for c in contours:              # find contour with biggest area
                found_area = cv2.contourArea(c)  # get area of next contour
                # find the middle of largest bounding rectangle
                if found_area > biggest_area:
                    motion_found = True
                    biggest_area = found_area
                    (x, y, w, h) = cv2.boundingRect(c)
                    cx = int(x + w/2)   # put circle in middle of width
                    cy = int(y + h/6)   # put circle closer to top
                    cw, ch = w, h

            if motion_found:
                # Do Something here with motion data
                if window_on:
                    # show small circle at motion location
                    if SHOW_CIRCLE:
                        cv2.circle(image2,(cx,cy),CIRCLE_SIZE,(0,255,0), LINE_THICKNESS)
                    else:
                        cv2.rectangle(image2,(cx,cy),(x+cw,y+ch),(0,255,0), LINE_THICKNESS)
                if debug:
                    '''
                    logging.info("cx,cy(%3i,%3i) contours:%2i  biggest %ix%i=%i SqPx  dist=%2i inch (%3i cm)" %
                                    (cx ,cy, total_contours, cw, ch, biggest_area, dist_inch, dist))
                    '''
                    logging.info("cx,cy(%3i,%3i) contours:%2i dist=%2i inch (%3i cm)" %
                                    (cx ,cy, total_contours, dist_inch, dist))

        if window_on:
            if diff_window_on:
                cv2.imshow('Difference Image',differenceimage)
            if thresh_window_on:
                cv2.imshow('OpenCV Threshold', thresholdimage)
            if WINDOW_BIGGER > 1:  # Note setting a bigger window will slow the FPS
                image2 = cv2.resize( image2,( big_w, big_h ))
            cv2.imshow('Press q in Window Quits)', image2)

            # Close Window if q pressed while mouse over opencv gui window
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                vs.stop()
                print("End Motion Tracking")
                quit(0)

#-----------------------------------------------------------------------------------------------
if __name__ == '__main__':
    while True:
        try:
            # Save images to an in-program stream
            # Setup video stream on a processor Thread for faster speed
            print("Initializing Pi Camera ....")
            vs = PiVideoStream().start()
            vs.camera.rotation = CAMERA_ROTATION
            vs.camera.hflip = CAMERA_HFLIP
            vs.camera.vflip = CAMERA_VFLIP
            time.sleep(2.0)  # Allow PiCamera to initialize
            track()
        except KeyboardInterrupt:
            vs.stop()
            print("")
            print("+++++++++++++++++++++++++++++++++++")
            print("User Pressed Keyboard ctrl-c")
            print("%s %s - Exiting" % (progname, ver))
            print("+++++++++++++++++++++++++++++++++++")
            print("")
            quit(0)