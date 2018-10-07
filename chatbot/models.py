from django.core.validators import int_list_validator
from django.db import models
from django.contrib.auth import models as auth_models


class Muser(auth_models.User):
    objects = auth_models.UserManager()

    created = models.DateTimeField(auto_now_add=True)
    gender = models.PositiveSmallIntegerField(blank=True, default=0) # 1: male, 2: female
    age = models.PositiveSmallIntegerField(blank=True, null=True)


class Artist(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    debut = models.DateField(blank=True, null=True)
    agent = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('created',)


class SoloArtist(Artist):
    gender = models.BooleanField(blank=True, null=True) # True: male, False: female
    birthday = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name


class GroupArtist(Artist):
    members = models.ManyToManyField(SoloArtist)

    def __str__(self):
        return self.name


class Album(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, blank=True, default='')
    artists = models.ManyToManyField(Artist)
    release = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('created',)


class Music(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100)
    album = models.ForeignKey('chatbot.Album', related_name='music', on_delete=models.CASCADE, blank=True, null=True)
    artists = models.ManyToManyField(Artist)
    genre = models.CharField(max_length=100, blank=True, default='')
    length = models.PositiveSmallIntegerField(blank=True, default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('created',)


class Evaluation(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('chatbot.Muser', related_name='evaluations', on_delete=models.CASCADE)
    music = models.ForeignKey('chatbot.Music', related_name='evaluations', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(blank=False)

    def __str__(self):
        return "{0}-{1}".format(self.music.title, self.user.username)

    class Meta:
        ordering = ('created',)


class Message(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey('chatbot.Muser', related_name='sent_messages', on_delete=models.CASCADE, blank=True, null=True)
    receiver = models.ForeignKey('chatbot.Muser', related_name='received_messages', on_delete=models.CASCADE, blank=True, null=True)
    text = models.TextField(blank=True)
    music = models.ForeignKey('chatbot.Music', on_delete=models.CASCADE, blank=True, null=True)
    chips = models.CharField(validators=[int_list_validator], max_length=20)

    class Meat:
        ordering = ('created',)
