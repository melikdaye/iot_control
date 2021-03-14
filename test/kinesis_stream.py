import subprocess
import sys
command="sudo gst-launch-1.0 nvarguscamerasrc ! 'video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, format=(string)NV12, framerate=15/1' ! nvtee ! nvvidconv flip-method=0  ! 'video/x-raw, format=(string)NV12, width=640, height=480, framerate=15/1' ! omxh264enc  ! video/x-h264, stream-format=avc, alignment=au ! kvssink stream-name=tytostream storage-size=512 access-key=AKIA4UMDU54PS4ZPS3CU  secret-key=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 aws-region=eu-central-1"
kinesis_stream=subprocess.run([command],shell=True)
