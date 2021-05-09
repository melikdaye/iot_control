from django.db import models
from tytocam.django_orm.Users.models import TytoUser
from tytocam.django_orm.Video_Files import Video_File
class Map(models.Model):
    user = models.ForeignKey(TytoUser, default=1,on_delete=models.CASCADE)
    video = models.ForeignKey(Video_File, default=595,on_delete=models.CASCADE)
    #s3_url=models.URLField()
    map_name=models.TextField(default="")
    isHidden=models.BooleanField(default=False)