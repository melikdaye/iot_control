import paho.mqtt.client as paho
import threading
import json
from django_orm.settings_orm import *
from gstreamer_camera import Camera
from uploader import Uploader
from getmac import get_mac_address as gma
from requests import get
from wifi_connect import *
from autossh import startReverseProxy
import os


client = None
autossh = False
camera = Camera(logger)


def wait_for_wifiList(client):
    time.sleep(5)
    client.publish("settings", json.dumps(search_wifi()), retain=False)

# define callbacks
def on_message(client, userdata, message):
    global autossh
    logger.logger.debug("Received message = {:s}".format(str(message.payload.decode("utf-8"))))
    if message.topic == "assign_id":
        id_dict = json.loads(message.payload)
        if id_dict["mac"] == gma():
            camera.device_id = id_dict["id"]
            if autossh is False:
                startReverseProxy(camera.device_id)
                autossh = True

    elif message.topic == "device_command":
        ret_message = None
        command_dict = json.loads(message.payload)
        command = command_dict["command"]
        id = command_dict["id"]
        if camera.device_id == id:
            if command == "start_camera":
                if camera.camera_thread is None:
                    camera.camera_thread = threading.Thread(target=camera.run_pipeline)
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
                camera.start_write()
            elif command == "stop_write":
                camera.stop_write()
            elif command == "get_connections":
                client.publish("settings", json.dumps(search_wifi()), retain=False)
            elif command == "connect_wifi":
                wifi_connect(command_dict["0"]["ssid"], command_dict["0"]["password"])
                threading.Thread(target=wait_for_wifiList,args=[client]).start()
            elif command == "forget_wifi":
                wifi_forget(command_dict["0"]["ssid"])
                threading.Thread(target=wait_for_wifiList,args=[client]).start()
            elif command=="reboot":
                 os.system("sudo reboot")
            device_props = collect_props()
            if ret_message is not None:
                device_props["message"] = ret_message
            try:
                client.publish("whoIam", json.dumps(device_props), retain=False)
            except:
                pass

    elif message.topic == "general":
        if str(message.payload.decode("utf-8")) == "update":
            device_props = collect_props()
            try:
                client.publish("whoIam", json.dumps(device_props), retain=False)
            except:
                pass


def on_publish(client, userdata, result):  # create function for callback
    pass


def collect_props():
    device_props = {}
    device_props["id"] = camera.device_id
    device_props["mac"] = gma()
    try:
        device_props["ip"] = get('https://api.ipify.org').text
    except:
        pass
    device_props["lat"] = camera.lat
    device_props["lon"] = camera.lon
    device_props["camera_status"] = camera.camera_status
    device_props["write_status"] = camera.writeDisk
    device_props["stream_status"] = camera.stream_status

    return device_props


def on_connect(client, userdata, flags, rc):
    logger.logger.info("Device connected to MQTT broker")
    global autossh
    if autossh is False and camera.device_id is not None:
        startReverseProxy(camera.device_id)
        autossh = True
    client.publish("settings", json.dumps(search_wifi()), retain=False)
    gps_signal = threading.Timer(15.0, send_gps, args=[client])
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
            camera.camera_props.gps_timestamp = django.utils.timezone.now()
            camera.camera_props.save()
        client.publish("whoIam", json.dumps(device_props), retain=False)
    except:
        pass
    gps_signal = threading.Timer(15.0, send_gps, args=[client])
    gps_signal.start()


def get_gps():
    gps_thread = threading.Thread(target=camera.get_gps)
    gps_thread.start()


def connect_device():
    client = paho.Client()
    client.on_message = on_message
    client.on_connect = on_connect
    client.username_pw_set(username="ubuntu", password="247520")
    client.connect("monitor.tytovision.com", 8883, 2000)
    client.loop_forever()


get_gps()
time.sleep(5)
uploader = Uploader("tytovision", camera)
connect_device()
