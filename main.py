import os
import pickle
import sys
import cv2
import numpy as np
import paho.mqtt.client as paho
import time
import threading
import json
from gstreamer_camera import Camera
from uploader import Uploader
from getmac import get_mac_address as gma
import gps
from requests import get
from datetime import datetime,timedelta
import django
from  wifi_connect import *
# breakpoint()
client=None
sudoPassword = '247520'
command = 'service nvargus-daemon restart'
p = os.system('echo %s|sudo -S %s' % (sudoPassword, command))
camera=Camera()


# define callbacks
def on_message(client, userdata, message):
    print("received message =", str(message.payload.decode("utf-8")))
    if message.topic=="assign_id":
        id_dict=json.loads(message.payload)
        if id_dict["mac"]==gma():
            camera.device_id=id_dict["id"]
            print(camera.device_id)
            # with open('config.data', 'wb') as handle:
            #     pickle.dump(collect_props(), handle, protocol=pickle.HIGHEST_PROTOCOL)

    elif message.topic=="device_command":
        ret_message=None
        command_dict= json.loads(message.payload)
        command=command_dict["command"]
        id=command_dict["id"]
        if camera.device_id==id:
            if command == "start_camera":
                if camera.camera_thread is None:
                    camera.camera_thread = threading.Thread(target=camera.run_pipeline,args=[camera.writeDisk])
                    camera.camera_thread.start()
                else:
                    camera.resume_pipeline()
            elif command == "stop_camera":
                camera.stop_pipeline()
            elif command == "start_stream":
                camera.start_stream()
            elif command == "stop_stream":
                camera.stop_stream()
            elif command == "start_write":
                camera.writeDisk = True
            elif command == "stop_write":
                camera.writeDisk=False
            elif command == "get_connections":
                client.publish("settings", json.dumps(search_wifi()), retain=False)
            elif command == "connect_wifi":
                ret=wifi_connect(command_dict["0"]["ssid"], command_dict["0"]["password"])
                connect_device()
            device_props = collect_props()
            if ret_message is not None:
                device_props["message"]=ret_message
            try:
                client.publish("whoIam", json.dumps(device_props), retain=False)
            except:
                pass
            # with open('config.data', 'wb') as handle:
            #     pickle.dump(collect_props(), handle, protocol=pickle.HIGHEST_PROTOCOL)
    elif message.topic=="general":
        if str(message.payload.decode("utf-8"))=="update":
            device_props = collect_props()
            try:
                client.publish("whoIam", json.dumps(device_props), retain=False)
            except:
                pass


def on_publish(client,userdata,result):             #create function for callback
    print(userdata,"data published \n")
    pass

def collect_props():
    device_props = {}
    device_props["id"]=camera.device_id
    device_props["mac"]=gma()
    try:
        device_props["ip"]= get('https://api.ipify.org').text
    except:
        pass
    device_props["lat"] = camera.lat
    device_props["lon"] = camera.lon
    device_props["camera_status"] = camera.camera_status
    device_props["write_status"] = camera.writeDisk
    device_props["stream_status"]=camera.stream_status


    return device_props

def on_connect(client, userdata, flags, rc):
    print("connected")

    gps_signal = threading.Timer(15.0, send_gps,args=[client])
    gps_signal.start()
    client.subscribe("assign_id")
    client.subscribe("device_command")
    client.subscribe("general")

def send_gps(client):
    device_props = collect_props()
    try:
        if camera.lat and camera.lon is not None:
            camera.camera_props.last_lat = camera.lat
            camera.camera_props.last_lon = camera.lon
            camera.camera_props.gps_timestamp=django.utils.timezone.now()
            camera.camera_props.save()

        client.publish("whoIam", json.dumps(device_props), retain=False)
    except:
        pass
    gps_signal = threading.Timer(15.0, send_gps,args=[client])
    gps_signal.start()

def get_gps():
    sudoPassword = '247520'
    command = 'gpsd /dev/ttyTHS2 -F /var/run/gpsd.sock'
    p = os.system('echo %s|sudo -S %s' % (sudoPassword, command))
    session = gps.gps("localhost", "2947")
    session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
    camera.session=session
    print("GPS is started to receive")
    gps_thread = threading.Thread(target=camera.get_gps)
    gps_thread.start()



##connect_device
def connect_device():
    client = paho.Client()
    client.on_message = on_message
    client.on_connect = on_connect
    client.username_pw_set(username="ubuntu", password="247520")
    client.connect("monitor.tytovision.com", 8883, 2000)

    ##start loop to process received messages
    client.loop_forever()

get_gps()
time.sleep(10)
uploader=Uploader("tytovision",camera)
connect_device()
