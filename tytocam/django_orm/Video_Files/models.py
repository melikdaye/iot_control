from django.db import models
from django_orm.Users.models import TytoUser
from django_orm.AdminPanel.models import DatasetQueue
import datetime

class Video_File(models.Model):
    s3_url=models.URLField()
    upload_time=models.TimeField(auto_now_add=True)
    upload_date=models.DateField(auto_now_add=True,null=True)
    video_name=models.TextField(default="")
    process_status=models.BooleanField(default=False)
    isQueued=models.BooleanField(default=False)
    user = models.ForeignKey(TytoUser, default=1, on_delete=models.CASCADE)
    duration = models.DurationField(default=datetime.timedelta(seconds=0))
    queuedBy = models.ForeignKey(DatasetQueue, blank=True, null=True, on_delete=models.SET_NULL)
    download_status = models.BooleanField(default=False)

