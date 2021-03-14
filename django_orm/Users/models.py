
from django.contrib.auth.models import AbstractUser
from django.db import models
import os

class TytoUser(AbstractUser):
    pass
    # add additional fields in here

    def __str__(self):
        return self.username

    def get_main_map(self):

        return os.path.join("user_maps",self.username,"main_map.html")
