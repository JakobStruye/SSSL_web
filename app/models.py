from __future__ import unicode_literals

from django.db import models

class User(models.Model):
    user_id = models.CharField(max_length=256)
    password = models.CharField(max_length=256)

class Message(models.Model):
    user_id = models.ForeignKey(User)
    date = models.DateTimeField()
    text = models.CharField(max_length=100000)
    
class Image(models.Model):
    user_id = models.ForeignKey(User)
    date = models.DateTimeField()
    image_location = models.CharField(max_length=256)