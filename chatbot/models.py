from django.db import models
from django.contrib.auth.models import User, UserManager


class Artist(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    debut = models.DateField(blank=True, null=True)
    agent = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ('created',)


class SoloArtist(Artist):
    birthday = models.DateField(blank=True, null=True)
    member_of = models.ForeignKey('chatbot.GroupArtist', related_name='members', on_delete=models.DO_NOTHING, blank=True, null=True)


class GroupArtist(Artist):
    pass
