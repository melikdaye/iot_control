import os
import pickle
import boto3
import threading
import glob
from django_orm.Video_Files.models import Video_File
from django_orm.Users.models import TytoUser
from wifi_connect import *
from aws_credentials import *



class Uploader:

    def __init__(self, user, camera=None):
        self.AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
        self.AWS_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
        self.AWS_STORAGE_BUCKET_NAME = AWS_STORAGE_BUCKET_NAME
        self.AWS_S3_REGION_NAME = AWS_S3_REGION_NAME
        self.s3_client = boto3.client('s3', aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                                      aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
                                      region_name=self.AWS_S3_REGION_NAME)
        self.user = user
        self.upload_thread = None
        self.video_status = {}
        self.part_size = int(15e6)
        self.camera = camera

        if os.path.exists('upload.data') and os.path.getsize('upload.data') > 0:
            with open('upload.data', 'rb') as handle:
                self.video_status = pickle.load(handle)

        self.upload_thread = threading.Thread(target=self.multiPartUpload)
        self.upload_thread.start()

    @staticmethod
    def as_percent(num, denom):
        return float(num) / float(denom) * 100.0

    def uploadParts(self, video):


        with open(self.video_status[video]["local_path"], "rb") as f:
            f.seek(self.video_status[video]["uploaded_bytes"])
            while True:
                if 0 < self.video_status[video]["total_bytes"] - self.video_status[video][
                    "uploaded_bytes"] < self.part_size:
                    data = f.read(
                        self.video_status[video]["total_bytes"] - self.video_status[video]["uploaded_bytes"])
                else:
                    data = f.read(self.part_size)
                if not len(data):
                    result = self.s3_client.complete_multipart_upload(
                        Bucket=self.AWS_STORAGE_BUCKET_NAME,
                        Key=video,
                        UploadId=self.video_status[video]["UploadId"],
                        MultipartUpload={"Parts": self.video_status[video]["Parts"]})
                    if result["ResponseMetadata"]["HTTPStatusCode"] == 200:
                        with open(self.video_status[video]["local_path"].replace(".mkv", ".csv"), 'rb') as csvfile:
                            self.s3_client.upload_fileobj(csvfile, self.AWS_STORAGE_BUCKET_NAME,
                                                          video.replace(".mkv", ".csv").replace("unprocessed",
                                                                                                "unprocessed_gps"))
                        selected_user = TytoUser.objects.get(username=self.user)
                        Video_File.objects.create(user=selected_user,
                                                  s3_url="https://{:s}.s3.{:s}.amazonaws.com/{:s}".format(
                                                      self.AWS_STORAGE_BUCKET_NAME,
                                                      self.AWS_S3_REGION_NAME,
                                                      '{:s}/{:s}/{:s}'.format(self.user, "unprocessed",
                                                                              os.path.basename(video))),
                                                  video_name=os.path.basename(video))
                        if os.path.exists(self.video_status[video]["local_path"]):
                            os.remove(self.video_status[video]["local_path"])
                            os.remove(self.video_status[video]["local_path"].replace(".mkv", ".csv"))
                        del self.video_status[video]
                        with open('upload.data', 'wb') as handle:
                            pickle.dump(self.video_status, handle, protocol=pickle.HIGHEST_PROTOCOL)

                    break

                part = self.s3_client.upload_part(Body=data, Bucket=self.AWS_STORAGE_BUCKET_NAME, Key=video,
                                                  UploadId=self.video_status[video]["UploadId"],
                                                  PartNumber=len(self.video_status[video]["Parts"]) + 1)
                self.video_status[video]["Parts"].append(
                    {"PartNumber": len(self.video_status[video]["Parts"]) + 1, "ETag": part["ETag"]})
                self.video_status[video]["uploaded_bytes"] += len(data)
                with open('upload.data', 'wb') as handle:
                    pickle.dump(self.video_status, handle, protocol=pickle.HIGHEST_PROTOCOL)
                logger.logger.info("Video: {3} --- {0} of {1} bytes uploaded ({2:.3f}%)".format(
                    self.video_status[video]["uploaded_bytes"], self.video_status[video]["total_bytes"],
                    self.as_percent(self.video_status[video]["uploaded_bytes"],
                                    self.video_status[video]["total_bytes"]),self.video_status[video]["local_path"]))



    def multiPartUpload(self):

        while True:

            if checkWifiConnectivity():
                key_parent_path = os.path.dirname(os.path.realpath(__file__))
                folders = glob.glob("{:s}/RECORDS/*".format(key_parent_path))
                for i in folders:
                    date_folder = os.path.basename(i)
                    videos = glob.glob("{:s}/*.mkv".format(i))
                    for video in videos:
                        if self.camera is not None:
                            currentFile = self.camera.currentFile
                        else:
                            currentFile = None
                        if os.path.exists(video) and os.path.exists(video.replace(".mkv", ".csv")):
                            if video != currentFile and os.path.getsize(video) > 5e6 and video != self.camera.ignoreFile:
                                video_key = "{:s}/unprocessed/{:s}_{:s}".format(self.user, date_folder,
                                                                                os.path.basename(video))
                                if video_key not in self.video_status.keys():
                                    try:
                                        mpu = self.s3_client.create_multipart_upload(Bucket=self.AWS_STORAGE_BUCKET_NAME,
                                                                                     Key=video_key)
                                        self.video_status.setdefault(video_key, {})
                                        self.video_status[video_key]["UploadId"] = mpu["UploadId"]
                                        self.video_status[video_key]["Parts"] = []
                                        self.video_status[video_key]["uploaded_bytes"] = 0
                                        self.video_status[video_key]["total_bytes"] = os.stat(video).st_size
                                        self.video_status[video_key]["local_path"] = video
                                    except:
                                        pass
                                try:
                                    self.uploadParts(video_key)
                                except:
                                    pass
                            elif (video==currentFile or video==self.camera.ignoreFile) and  len(videos)==1:
                                time.sleep(((self.camera.record_fps*self.camera.max_video_duration)-self.camera.frame_counter)//self.camera.record_fps)
                            else:
                                logger.logger.info("File name : {:s}, File Size: {:s} is not candidate for upload".format(video,str(os.path.getsize(video))))
                                if os.path.getsize(video) < 5e6 and video!=currentFile and video!=self.camera.ignoreFile:
                                    try:
                                        if os.path.exists(video):
                                            os.remove(video)
                                            os.remove(video.replace(".mkv", ".csv"))
                                            videos.remove(video)
                                    except Exception as e:
                                        logger.logger.error(
                                            "File: {:s} cannot be removed".format(video),exc_info=True)
                                        pass

                        else:
                            try:
                                if os.path.exists(video) and video != self.camera.ignoreFile:
                                    os.remove(video)
                                    videos.remove(video)
                            except Exception as e:
                                logger.logger.error("File: {:s} cannot be removed".format(video),exc_info=True)
                                pass

            else:
                logger.logger.warning("No Wifi Connection")
                time.sleep(120)
