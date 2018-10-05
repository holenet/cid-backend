from django.db import models
from django.contrib.auth import models as auth_models


class User(auth_models.User):
    objects = auth_models.UserManager()

    created = models.DateTimeField(auto_now_add=True)
    gender = models.BooleanField(blank=True, null=True) # True: male, False: female
    age = models.PositiveSmallIntegerField(blank=True, null=True)


class Artist(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    debut = models.DateField(blank=True, null=True)
    agent = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ('created',)


class SoloArtist(Artist):
    gender = models.BooleanField(blank=True, null=True) # True: male, False: female
    birthday = models.DateField(blank=True, null=True)


class GroupArtist(Artist):
    members = models.ManyToManyField(SoloArtist)


class Album(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, blank=True, default='')
    artists = models.ManyToManyField(Artist)
    release = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ('created',)


class Music(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100)
    album = models.ForeignKey('chatbot.Album', related_name='music', on_delete=models.CASCADE, blank=True, null=True)
    artist = models.ForeignKey('chatbot.Artist', related_name='music', on_delete=models.CASCADE, blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True, default='')
    length = models.PositiveSmallIntegerField(blank=True, default=0)

    class Meta:
        ordering = ('created',)


class Evaluation(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('chatbot.User', related_name='evaluations', on_delete=models.CASCADE, blank=True, null=True)
    music = models.ForeignKey('chatbot.Music', related_name='evaluations', on_delete=models.CASCADE)

    class Meta:
        ordering = ('created',)


class Message(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey('chatbot.User', related_name='sent', on_delete=models.CASCADE, blank=True, null=True)
    receiver = models.ForeignKey('chatbot.User', related_name='received', on_delete=models.CASCADE, blank=True, null=True)
    text = models.CharField(max_length=500, blank=True, default='')
    music = models.ForeignKey('chatbot.Music', related_name='messages', on_delete=models.CASCADE, blank=True, null=True)
    chips = models.CharField(max_length=100, blank=True, default='')

    class Meat:
        ordering = ('created',)
