import os
import pickle
import time
import subprocess as sp
import shlex
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject
from getmac import get_mac_address as gma
from gi.repository import Gst
import cv2
import numpy
from datetime import datetime,timedelta
import threading
from subprocess import call
from django_orm.settings_orm import *
from django_orm.AdminPanel.models import  TytoCamera
import csv

class Camera:


    def __init__(self):

        GObject.threads_init()
        Gst.init(None)
        mac_address= gma()
        self.camera_props=TytoCamera.objects.get(mac_address=mac_address)
        self.device_id=self.camera_props.id
        self.image_arr = None
        self.writeDisk=self.camera_props.write_status
        self.camera_status=self.camera_props.camera_status
        self.stream_status = self.camera_props.stream_status
        self.camera_thread=None
        self.elapsed_time=0
        self.frame_counter=0
        self.video_writer=None
        self.currentFile=None
        self.frame_loss=0
        self.pipeline = Gst.Pipeline("tx2_onboard")
        self.source = Gst.ElementFactory.make("nvarguscamerasrc", "source")
        nvvidconvsrc = Gst.ElementFactory.make("nvvidconv", "convertor")

        tee = Gst.ElementFactory.make('tee', 'tee')

        file_queue = Gst.ElementFactory.make('queue', 'file_queue')
        convert = Gst.ElementFactory.make("videoconvert", "convert")
        self.file_sink = Gst.ElementFactory.make("appsink", "sink")
        self.file_sink.set_property("emit-signals", True)
        srccaps = Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080,format=(string)NV12, framerate=(fraction)15/1")
        sinkcaps = Gst.Caps.from_string("video/x-raw, format=(string)BGR")
        convertcaps = Gst.Caps.from_string("flip-method=0")
        self.file_sink.set_property("caps", sinkcaps)
        self.file_sink.connect("new-sample", self.__new_buffer, self.file_sink)

        stream_queue = Gst.ElementFactory.make('queue', 'stream_queue')
        self.stream_valve=Gst.ElementFactory.make('valve', 'stream_valve')
        self.stream_valve.set_property("drop", True)
        omx_caps = Gst.Caps.from_string("video/x-raw, format=(string)NV12, width=640, height=480, framerate=15/1")
        omx_filter = Gst.ElementFactory.make('capsfilter', 'omx_filter')
        omx_filter.set_property('caps', omx_caps)
        self.omxencode = Gst.ElementFactory.make('omxh264enc', 'omxencode')
        self.stream_sinkcaps = Gst.Caps.from_string("video/x-h264, stream-format=avc, alignment=au")
        self.stream_sink = Gst.ElementFactory.make("kvssink", "stream_sink")
        print("setting kvssink properties")
        self.stream_sink.set_property('stream-name', "tytostream")
        self.stream_sink.set_property('access-key', "AKIA4UMDU54PS4ZPS3CU")
        self.stream_sink.set_property('secret-key', "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")
        self.stream_sink.set_property('aws-region', "eu-central-1")
        self.stream_sink.set_property('storage-size', 512)

        self.pipeline.add(self.source)
        self.pipeline.add(nvvidconvsrc)
        self.pipeline.add(tee)
        self.pipeline.add(file_queue)
        self.pipeline.add(convert)
        self.pipeline.add(self.file_sink)
        self.pipeline.add(stream_queue)
        self.pipeline.add(self.stream_valve)
        self.pipeline.add(self.omxencode)
        self.pipeline.add(self.stream_sink)
        if not self.source.link_filtered(nvvidconvsrc, srccaps):
            print("Elements could not be linked.")
            exit(-1)
        if not nvvidconvsrc.link_filtered(tee, convertcaps):
            print("Elements could not be linked.")
            exit(-1)
        if not Gst.Element.link(tee, file_queue):
            print("Elements could not be linked.")
            exit(-1)
        if not Gst.Element.link(file_queue, convert):
            print("Elements could not be linked.")
            exit(-1)
        if not Gst.Element.link(convert, self.file_sink):
            print("Elements could not be linked.")
            exit(-1)

        if not Gst.Element.link(tee, stream_queue):
            print("Elements could not be linked.tee")
            exit(-1)
        if not Gst.Element.link(stream_queue, self.stream_valve):
            print("Elements could not be linked.tee")
            exit(-1)
        if not Gst.Element.link(self.stream_valve, self.omxencode):
            print("Elements could not be linked.omx_filter")
            exit(-1)
        if not self.omxencode.link_filtered(self.stream_sink, self.stream_sinkcaps):
            print("Elements could not be linked.omxencode")
            exit(-1)

        self.lat=None
        self.lon=None
        self.pre_lat=None
        self.pre_lon=None
        self.session=None

        # if os.path.exists('config.data'):
        self.run_config()

    def run_config(self):
        # if os.path.getsize('config.data') > 0:
        #     with open('config.data', 'rb') as handle:
        #         device_props = pickle.load(handle)
        #         print(device_props)
        #         self.device_id=device_props["id"]
        #         self.camera_status=device_props["camera_status"]
        #         self.writeDisk=device_props["write_status"]
        #         self.stream_status=device_props["stream_status"]
        if self.camera_status:
            self.camera_thread = threading.Thread(target=self.run_pipeline, args=[self.writeDisk])
            self.camera_thread.start()
        if self.stream_status:
            self.start_stream()
        # else:
        #     self.writeDisk=True
        #     self.camera_thread = threading.Thread(target=self.run_pipeline, args=[self.writeDisk])
        #     self.camera_thread.start()

    def __gst_to_opencv(self,sample):

        buf = sample.get_buffer()
        caps = sample.get_caps()
        arr = numpy.ndarray(
            (caps.get_structure(0).get_value('height'),
             caps.get_structure(0).get_value('width'),
             3),
            buffer=buf.extract_dup(0, buf.get_size()),
            dtype=numpy.uint8)
        return arr

    def __new_buffer(self,sink, data):
        sample = sink.emit("pull-sample")
        arr = self.__gst_to_opencv(sample)
        self.image_arr = arr
        return Gst.FlowReturn.OK

    def run_pipeline(self,writeFlag):
        self.resume_pipeline()
        self.camera_status = True
        self.writeDisk=writeFlag
        write_thread = threading.Thread(target=self.write2file)
        write_thread.start()

    def resume_pipeline(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set the pipeline to the playing state.")
            exit(-1)
        self.camera_status = True

    def get_gps(self):

        while True:
            if self.session is not None:
                rep = self.session.next()
                try:
                    if (rep["class"] == "TPV"):
                        #print(str(rep.lat) + "," + str(rep.lon))
                        self.lat = rep.lat
                        self.lon = rep.lon

                except Exception as e:
                    self.pre_lat=self.lat
                    self.pre_lon=self.lon
                    self.lat = None
                    self.lon = None
                    #print("Got exception " + str(e))

    def stop_pipeline(self):
        # Free resources
        self.pipeline.set_state(Gst.State.PAUSED)
        self.camera_status = False
        print("Stopped")

    def write2file(self):


        # Wait until error or EOS
        bus = self.pipeline.get_bus()
        writer=None
        while True:
            now = datetime.now()
            date_time = now.strftime("%d_%m_%Y")
            if os.path.exists("RECORDS/{:s}/".format(date_time)) is False:
                os.makedirs("RECORDS/{:s}/".format(date_time))
            message = bus.timed_pop_filtered(10000, Gst.MessageType.ANY)

            # print "image_arr: ", image_arr
            if self.image_arr is not None and self.writeDisk and self.camera_status and ((self.lat is not None and self.lon is not None) or (self.pre_lat is not None and self.pre_lon is not None)):
                if self.video_writer is None:
                    print("Creating video")
                    video_file = os.path.join("RECORDS/{:s}/".format(date_time), now.strftime("%H_%M_%S") + ".mkv")
                    csv_file=open(video_file.replace(".mkv",".csv"), "w")
                    writer = csv.writer(csv_file, delimiter=';')
                    print(video_file)
                    self.video_writer = cv2.VideoWriter("appsrc ! video/x-raw, format=BGR ! queue ! videoconvert ! video/x-raw,format=BGRx framerate=15/1 ! nvvidconv ! nvv4l2h264enc maxperf-enable=1 ! h264parse ! matroskamux ! filesink location={:s} ".format(video_file), cv2.CAP_GSTREAMER,0, float(15), (1920, 1080))
                    self.currentFile=video_file

                else:
                    if self.lat and self.lon is None:
                        writer.writerow(["{:s},{:s}".format(str(self.pre_lat), str(self.pre_lon))])
                    else:
                        writer.writerow(["{:s},{:s}".format(str(self.lat), str(self.lon))])
                    self.video_writer.write(self.image_arr)
                    self.frame_counter += 1
                    self.frame_loss = 0
                    self.image_arr = None
                    if self.frame_counter*(1/15)>=15*60:

                        self.video_writer.release()
                        self.video_writer=None
                        self.frame_counter=0
                        # compress_thread = threading.Thread(target=self.compress_h265,args=[video_file])
                      # compress_thread.start()
        print("Exit write thread")

            #
            # if self.image_arr is None and self.camera_status:
            #     self.frame_loss+=1
            #     if self.frame_loss > 300:
            #         sudoPassword = '247520'
            #         command = 'service nvargus-daemon restart'
            #         p = os.system('echo %s|sudo -S %s' % (sudoPassword, command))
            #         self.frame_loss=0

            # if message:
            #     if message.type == Gst.MessageType.ERROR:
            #         err, debug = message.parse_error()
            #         print(("Error received from element %s: %s" % (
            #             message.src.get_name(), err)))
            #         print(("Debugging information: %s" % debug))
            #         break
            #     elif message.type == Gst.MessageType.EOS:
            #         print("End-Of-Stream reached.")
            #         break
            #     elif message.type == Gst.MessageType.STATE_CHANGED:
            #         if isinstance(message.src, Gst.Pipeline):
            #             old_state, new_state, pending_state = message.parse_state_changed()
            #             print(("Pipeline state changed from %s to %s." %
            #                    (old_state.value_nick, new_state.value_nick)))
            #     else:
            #         print("Unexpected message received.")

    def stop_stream(self):
        self.stream_valve.set_property("drop", True)
        self.stream_status=False
    def start_stream(self):
        self.stream_valve.set_property("drop", False)
        self.stream_status = True



    def compress_h265(self,file):

        current_directory = os.getcwd()
        mp4Name = file.replace("mkv", "mp4")
        full_path_source = os.path.normpath(os.path.join(current_directory, file))
        full_path_dest = os.path.normpath(os.path.join(current_directory, mp4Name))

        if os.path.exists(mp4Name) is False:
            print("Converting: " + full_path_source)

            call(['ffmpeg', '-i', full_path_source, "-c:v", "libx265", "-vtag", "hvc1", full_path_dest])
            os.remove(file)
            print("Converted to: " + full_path_dest)

        return mp4Name







