#poly_watch - poly watches to detect motion
from picamera.array import PiRGBArray
from picamera import PiCamera
from utils import send_email, TempImage
import argparse
import warnings
import datetime
import json
import time
import cv2

# load some config
conf = json.load(open(args["conf"]))

# init the camera
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# allow the camera to 'warmup' then init the average frame
# init last uploaded and frame motion counter
print "[INFO] poly_watch warming up ... "
time.sleep(conf["camera_warmup_time"]
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0
print('[INFO] poly_watch started !!')

# capture farmes from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    #grab the raw NumPy array of the image and init timestamp and text
    frame = f.array
    timestamp = datetime.datetime.now()
    text = "Unoccupied"

    #Computer Vision!
    # resize the frame, convert to grayscale, and blur
    gray = cv2.cvColor(frame, cv.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, tuple(conf['blur_size']), 0)

    #if the avg frame is None, init
    if avg is None:
        print("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    #accumulate the weighted average between the current frame and
    #previous frames, then computer the diff between the current
    #fram and running average
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
    cv2.accumulateWeighted(gray, avg, 0.5)

    #tune the picutre for processing
    # thresholding deff frame for filling holes and noise
    #find contours of moving regions
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cd2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    im2 ,cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    #loop over teh contours
    for c in cnts:
        #if countour is too small ignor
        if cv2.contourArea(c) < conf["min_area"]:
            continue

        #computer the bounding box, draw it
        (x,y,w,h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (o, 255, 0), 2)
        text = "Occupied"

    #draw text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Status: {}".format(text), (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255),2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0,0,255), 1)

    #LOGIC
    #check to see if room is occupied, then action
    if text == "Occupied":
        #save the frame
        cv2.imwrite("/tmp/poly_watch_{}.jpg".format(motionCounter), frame);

        #moderate uploads
        if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
            #increment counter
            motionCounter += 1;

            #check on the counter
            if motionCounter >= int(conf["min_motion_frames"]):
                #send email
                # when set up
                print("[INFO] send an Alert Email")
                #or post message on bus
                #update last upload, rest counter
                lastUploaded = timestamp
                motionCounter = 0

    #otherwise nothing seen
    else:
        motionCounter = 0

