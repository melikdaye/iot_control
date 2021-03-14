import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject

from gi.repository import Gst
import cv2
import numpy


def gst_to_opencv(sample):
    buf = sample.get_buffer()
    caps = sample.get_caps()
    # print(caps.get_structure(0).get_value('format'))
    # print(caps.get_structure(0).get_value('height'))
    # print(caps.get_structure(0).get_value('width'))

    # print(buf.get_size())

    arr = numpy.ndarray(
        (caps.get_structure(0).get_value('height'),
         caps.get_structure(0).get_value('width'),
         3),
        buffer=buf.extract_dup(0, buf.get_size()),
        dtype=numpy.uint8)
    return arr


def new_buffer(sink, data):
    global image_arr
    sample = sink.emit("pull-sample")
    arr = gst_to_opencv(sample)
    image_arr = arr
    return Gst.FlowReturn.OK



GObject.threads_init()
Gst.init(None)
image_arr = None
writeDisk = True
pipeline = Gst.Pipeline("tx2_onboard")
source = Gst.ElementFactory.make("nvarguscamerasrc", "source")
nvvidconvsrc = Gst.ElementFactory.make("nvvidconv", "convertor")
convert = Gst.ElementFactory.make("videoconvert", "convert")
file_sink = Gst.ElementFactory.make("appsink", "sink")
file_sink.set_property("emit-signals", True)
srccaps = Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)1280, height=(int)720,format=(string)NV12, framerate=(fraction)30/1")
sinkcaps = Gst.Caps.from_string("video/x-raw, format=(string)BGR")
convertcaps = Gst.Caps.from_string("flip-method=0")
file_sink.set_property("caps", sinkcaps)
file_sink.connect("new-sample", new_buffer, file_sink)

pipeline.add(source)
pipeline.add(nvvidconvsrc)
pipeline.add(convert)
pipeline.add(file_sink)

if not source.link_filtered(nvvidconvsrc, srccaps):
    print("Elements could not be linked.")
    exit(-1)
if not nvvidconvsrc.link_filtered(convert, convertcaps):
    print("Elements could not be linked.")
    exit(-1)

if not Gst.Element.link(convert, file_sink):
    print("Elements could not be linked.")
    exit(-1)

ret = pipeline.set_state(Gst.State.PLAYING)
if ret == Gst.StateChangeReturn.FAILURE:
        print("Unable to set the pipeline to the playing state.")
        exit(-1)

bus = pipeline.get_bus()
while True:

    message = bus.timed_pop_filtered(10000, Gst.MessageType.ANY)

    if image_arr is not None :
            cv2.imshow("appsink image arr", image_arr)
            cv2.waitKey(1)
    if message:
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(("Error received from element %s: %s" % (
                message.src.get_name(), err)))
            print(("Debugging information: %s" % debug))
            break
        elif message.type == Gst.MessageType.EOS:
            print("End-Of-Stream reached.")
            break
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if isinstance(message.src, Gst.Pipeline):
                old_state, new_state, pending_state = message.parse_state_changed()
                print(("Pipeline state changed from %s to %s." %
                       (old_state.value_nick, new_state.value_nick)))
        else:
            print("Unexpected message received.")
