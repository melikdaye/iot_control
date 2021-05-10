from time import sleep
import serial


class GPS:

    def __init__(self):

        try:
            serw = serial.Serial("/dev/ttyUSB2", baudrate=115200, timeout=1, rtscts=True, dsrdtr=True)
            serw.write('AT+QGPS=1\r'.encode())
            serw.close()
            sleep(1)
        except Exception as e:
            print("Serial port connection failed.")
            print(e)

        self.lat = None
        self.lon = None
        try:
            self.gps_serial = serial.Serial("/dev/ttyUSB1", baudrate=115200, timeout=0.5, rtscts=True, dsrdtr=True)
        except Exception as e:
            self.gps_serial=None
            print("Serial port connection failed.")
            print(e)

    @classmethod
    def decode(self, coord):
        # Converts DDDMM.MMMMM -> DD deg MM.MMMMM min
        x = coord.split(".")
        head = x[0]
        tail = x[1]
        deg = head[0:-2]
        min = head[-2:]
        return deg + " deg " + min + "." + tail + " min"

    def __parseGPS(self, data):

        if data[0:6] == "$GPRMC":

            sdata = data.split(",")
            if sdata[2] == 'V':
                return

            lat = self.decode(sdata[3])  # latitude
            lon = self.decode(sdata[5])  # longitute

            latitude = lat.split()
            longitute = lon.split()

            fl_lat = int(latitude[0]) + (float(latitude[2]) / 60)

            fl_lon = int(longitute[0]) + (float(longitute[2]) / 60)

            self.lat = fl_lat
            self.lon = fl_lon

    def readGPS(self):

        while True:
            if self.gps_serial is not None:
                data = self.gps_serial.readline().decode('utf-8')
                self.__parseGPS(data)
