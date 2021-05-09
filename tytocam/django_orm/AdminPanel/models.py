from django.db import models
from tytocam.django_orm.Users.models import TytoUser


class ComputeServer(models.Model):
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField()
    numberOfQueues=models.IntegerField(default=0)
    computer_name = models.TextField(default="")


class DatasetQueue(models.Model):

    dataset_name = models.TextField(default="")
    controlled = models.BooleanField(default=False)
    completed=models.BooleanField(default=False)
    numberOfVideos=models.IntegerField(default=0)
    current_size=models.FloatField(default=0.0)
    compute_server=models.ForeignKey(ComputeServer, default=1, on_delete=models.PROTECT)
    isLocked=models.BooleanField(default=False)
    lockedBy=models.ForeignKey(TytoUser, blank=True, null=True,on_delete=models.SET_NULL)


class TytoCamera(models.Model):
    mac_address = models.TextField(default="")
    ip_address = models.GenericIPAddressField()
    camera_status = models.BooleanField(default=False)
    write_status = models.BooleanField(default=False)
    stream_status = models.BooleanField(default=False)
    gps_status = models.BooleanField(default=False)
    device_status = models.TextField(blank=True, default="")
    last_lat = models.FloatField(blank=True, null=True)
    last_lon = models.FloatField(blank=True, null=True)
    ownership = models.ForeignKey(TytoUser, blank=True, null=True, on_delete=models.SET_NULL)
    gps_timestamp = models.DateTimeField(blank=True, null=True)
    device_timestamp = models.DateTimeField(blank=True, null=True)
    record_timestamp = models.DateTimeField(blank=True, null=True)
