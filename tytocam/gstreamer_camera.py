import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject
from getmac import get_mac_address as gma
from gi.repository import Gst
from datetime import datetime
import threading
from subprocess import call
from django_orm.AdminPanel.models import TytoCamera
import csv
from gps import *
import gc
from aws_credentials import *

class Camera:

    def __init__(self,logger):

        GObject.threads_init()
        Gst.init(None)
        mac_address = gma()
        self.gps = GPS(logger)
        try:
            self.camera_props = TytoCamera.objects.get(mac_address=mac_address)
            self.device_id = self.camera_props.id
            self.writeDisk = self.camera_props.write_status
            self.camera_status = self.camera_props.camera_status
            self.stream_status = self.camera_props.stream_status
        except TytoCamera.DoesNotExist:
            self.device_id = None
            self.writeDisk = False
            self.camera_status = True
            self.stream_status = False
        self.image_arr = None
        self.camera_thread = None
        self.elapsed_time = 0
        self.frame_counter = 0
        self.video_writer = None
        self.currentFile = None
        self.ignoreFile = None
        self.csvWriter = None
        self.frame_loss = 0
        self.max_video_duration=15
        self.record_fps=15
        self.preWriteStatus = self.writeDisk

        self.pipeline = Gst.Pipeline()
        source = Gst.ElementFactory.make("rpicamsrc", "source")

        source.set_property("video-stabilisation", True)
        source.set_property("annotation-mode", "custom-text")
        source.set_property("roi-x",0.1)
        source.set_property("roi-y",0.2)
        source.set_property("roi-w",0.8)
        source.set_property("roi-h",0.8)

        videoConvert = Gst.ElementFactory.make("videoconvert", "video_convert")
        srcCaps = Gst.Caps.from_string(
            "video/x-raw,width=(int){:s}, height=(int){:s}, framerate=(fraction){:s}/1".format(str(1920),
                                                                                               str(1080),
                                                                                               str(self.record_fps)))

        tee = Gst.ElementFactory.make('tee', 'tee')

        fileQueue = Gst.ElementFactory.make('queue', 'file_queue')
        fileQueue.set_property("leaky", 2)
        self.fileValve = Gst.ElementFactory.make('valve', 'file_valve')
        self.fileValve.set_property("drop", False)
        omxEncode = Gst.ElementFactory.make('omxh264enc', 'omxencode')
        h264Parser = Gst.ElementFactory.make('h264parse', 'h264parser')
        muxer = Gst.ElementFactory.make('matroskamux', 'file_muxer')
        muxer.set_property("offset-to-zero", True)
        infileSink = Gst.ElementFactory.make('filesink', 'infile_sink')
        infileSink.set_property("async", True)
        self.fileSink = Gst.ElementFactory.make('splitmuxsink', 'file_sink')
        self.fileSink.set_property('async-handling', True)

        self.fileSink.set_property("max-size-time", 1000000000 * 60 * self.max_video_duration)

        self.fileSink.set_property("muxer", muxer)
        self.fileSink.set_property("sink", infileSink)
        self.fileSink.connect("format-location", self.__format_location_callback)

        streamQueue = Gst.ElementFactory.make('queue', 'stream_queue')
        streamQueue.set_property("leaky", 2)
        self.streamValve = Gst.ElementFactory.make('valve', 'stream_valve')
        self.streamValve.set_property("drop", not self.stream_status)
        streamScale = Gst.ElementFactory.make('videoscale', 'stream_scale')
        streamCaps = Gst.Caps.from_string("video/x-raw, width=640, height=400")

        streamOmxEncode = Gst.ElementFactory.make('omxh264enc', 'stream_omxencode')
        streamSinkCaps = Gst.Caps.from_string("video/x-h264, stream-format=avc, alignment=au")
        streamH264Parser = Gst.ElementFactory.make('h264parse', 'stream_h264parser')
        streamSink = Gst.ElementFactory.make("kvssink", "stream_sink")
        print("setting kvssink properties")
        streamSink.set_property('stream-name', KINESIS_STREAM_NAME)
        streamSink.set_property('access-key', AWS_ACCESS_KEY_ID)
        streamSink.set_property('secret-key', AWS_SECRET_ACCESS_KEY)
        streamSink.set_property('aws-region', AWS_S3_REGION_NAME)
        streamSink.set_property('storage-size', 512)

        fakeQueue = Gst.ElementFactory.make('queue', 'fake_queue')
        fakeQueue.set_property("leaky", 2)
        self.fakeValve = Gst.ElementFactory.make('valve', 'fake_valve')
        self.fakeValve.set_property("drop", not self.writeDisk)
        fakeSink = Gst.ElementFactory.make('fakesink', 'fake_sink')
        fakeSink.set_property("signal-handoffs", True)
        fakeSink.connect("handoff", self.__new_buffer, fakeSink)
        fakeSink.set_property("async", False)

        self.pipeline.add(source)
        self.pipeline.add(videoConvert)

        self.pipeline.add(tee)

        self.pipeline.add(streamQueue)
        self.pipeline.add(self.streamValve)
        self.pipeline.add(streamScale)
        self.pipeline.add(streamOmxEncode)
        self.pipeline.add(streamH264Parser)
        self.pipeline.add(streamSink)

        self.pipeline.add(fileQueue)
        self.pipeline.add(self.fileValve)
        self.pipeline.add(omxEncode)
        self.pipeline.add(h264Parser)
        self.pipeline.add(self.fileSink)

        self.pipeline.add(fakeQueue)
        self.pipeline.add(self.fakeValve)
        self.pipeline.add(fakeSink)

        if not Gst.Element.link(source, videoConvert):
            print("Tee could not be linked.")
            exit(-1)
        if not videoConvert.link_filtered(tee, srcCaps):
            print("Tee could not be linked.")
            exit(-1)
        if not Gst.Element.link(tee, fileQueue):
            print("file_queue could not be linked.")
            exit(-1)
        if not Gst.Element.link(fileQueue, self.fileValve):
            print("file_queue could not be linked.")
            exit(-1)
        if not self.fileValve.link_filtered(omxEncode, None):
            print("convert could not be linked.")
            exit(-1)

        if not Gst.Element.link(omxEncode, h264Parser):
            print("stream_queue could not be linked.tee")
            exit(-1)
        if not Gst.Element.link(h264Parser, self.fileSink):
            print("stream_valve could not be linked.tee")
            exit(-1)

        if not Gst.Element.link(tee, streamQueue):
            print("stream_queue could not be linked.tee")
            exit(-1)
        if not Gst.Element.link(streamQueue, streamScale):
            print("stream_valve could not be linked.tee")
            exit(-1)

        if not streamScale.link_filtered(self.streamValve, streamCaps):
            print("stream_sinkcaps could not be linked.omxencode")

        if not Gst.Element.link(self.streamValve, streamOmxEncode):
            print("stream_valve could not be linked.tee")
            exit(-1)
        if not Gst.Element.link(streamOmxEncode, streamH264Parser):
            print("stream_valve could not be linked.tee")
            exit(-1)
        if not streamH264Parser.link_filtered(streamSink, streamSinkCaps):
            print("stream_sinkcaps could not be linked.omxencode")

        if not Gst.Element.link(tee, fakeQueue):
            print("stream_queue could not be linked.tee")
            exit(-1)
        if not Gst.Element.link(fakeQueue, self.fakeValve):
            print("stream_queue could not be linked.tee")
            exit(-1)
        if not Gst.Element.link(self.fakeValve, fakeSink):
            print("stream_valve could not be linked.tee")
            exit(-1)

        self.lat = None
        self.lon = None
        self.pre_lat = None
        self.pre_lon = None
        self.session = None
        self.file_parent_path = os.path.dirname(os.path.realpath(__file__))
        self.run_config()

    def run_config(self):

        if self.camera_status:
            self.camera_thread = threading.Thread(target=self.run_pipeline)
            self.camera_thread.start()

    def __format_location_callback(self, splitmux, fragment_id):

        if (self.writeDisk is True and self.preWriteStatus is False) or (
                self.writeDisk is False and self.preWriteStatus is False):
            if self.ignoreFile is not None:
                os.remove(self.ignoreFile)
                self.ignoreFile = None
        now = datetime.now()
        date_time = now.strftime("%d_%m_%Y")
        if os.path.exists("RECORDS/{:s}/".format(date_time)) is False:
            os.makedirs("RECORDS/{:s}/".format(date_time))
        self.frame_counter = 0
        path = "{:s}{:s}.mkv".format("RECORDS/{:s}/".format(date_time), datetime.now().strftime("%H_%M_%S"))

        if self.writeDisk:
            self.currentFile = os.path.join(self.file_parent_path,path)
            csv_file = open(path.replace(".mkv", ".csv"), "w")
            self.csvWriter = csv.writer(csv_file, delimiter=';')
        else:
            self.ignoreFile = os.path.join(self.file_parent_path,path)
            self.preWriteStatus = False
        return path

    def __new_buffer(self, sink, buffer, pad, data):

        if self.csvWriter is not None:
            if self.lat and self.lon is None:
                self.csvWriter.writerow(["{:s},{:s}".format(str(self.pre_lat), str(self.pre_lon))])
            else:
                self.csvWriter.writerow(["{:s},{:s}".format(str(self.lat), str(self.lon))])
            self.frame_counter += 1
        return Gst.FlowReturn.OK

    def run_pipeline(self):

        self.resume_pipeline()
        self.camera_status = True

    def resume_pipeline(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set the pipeline to the playing state.")
            exit(-1)
        self.camera_status = True

    def get_gps(self):

        gps_thread = threading.Thread(target=self.gps.readGPS)
        gps_thread.start()
        while True:
            gc.collect()
            if self.gps.lat and self.gps.lon is not None:
                self.lat = self.gps.lat
                self.lon = self.gps.lon
            else:
                self.pre_lat = self.lat
                self.pre_lon = self.lon
                self.lat = None
                self.lon = None
            time.sleep(2)

    def stop_pipeline(self):
        # Free resources
        self.pipeline.set_state(Gst.State.PAUSED)
        self.camera_status = False
        print("Stopped")

    def stop_stream(self):
        self.streamValve.set_property("drop", True)
        self.stream_status = False

    def start_stream(self):
        self.streamValve.set_property("drop", False)
        self.stream_status = True

    def stop_write(self):

        self.fileSink.emit("split-now")
        self.fakeValve.set_property("drop", True)
        self.writeDisk = False
        self.preWriteStatus = True

    def start_write(self):

        self.fileSink.emit("split-now")
        self.fakeValve.set_property("drop", False)
        self.writeDisk = True
        self.preWriteStatus = False

    def compress_h265(self, file):

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
