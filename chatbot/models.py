import os

from django.core.validators import int_list_validator
from django.db import models
from django.contrib.auth import models as auth_models


class Muser(auth_models.User):
    objects = auth_models.UserManager()

    gender = models.PositiveSmallIntegerField(blank=True, default=0) # 1: male, 2: female
    birthdate = models.DateField(blank=True, null=True)

    push_token = models.CharField(max_length=200, blank=True, null=True)
    cluster = models.PositiveSmallIntegerField(blank=True, null=True)

    recommended = models.ManyToManyField('chatbot.Music')

    class Meta:
        verbose_name = 'Muser'

    def __str__(self):
        return self.username


class Artist(models.Model):
    original_id = models.IntegerField()
    name = models.CharField(max_length=255, blank=True, default='')
    debut = models.DateField(blank=True, null=True)
    agent = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class SoloArtist(Artist):
    gender = models.BooleanField(blank=True, null=True) # True: male, False: female
    birthday = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name


class GroupArtist(Artist):
    members = models.ManyToManyField(Artist, related_name='group_set')

    def __str__(self):
        return self.name


def album_image_path(album, filename):
    return os.path.join('album_image', f"{album.title.replace('/', '-').replace(' ', '_')}.jpg")


class Album(models.Model):
    original_id = models.IntegerField()
    title = models.CharField(max_length=500, blank=True)
    genre = models.CharField(max_length=255, blank=True, null=True)
    artists = models.ManyToManyField(Artist, related_name='albums')
    release = models.DateField(blank=True, null=True)
    image = models.ImageField(null=True, upload_to=album_image_path, max_length=500)

    def __str__(self):
        return self.title


class Music(models.Model):
    original_id = models.IntegerField()
    title = models.CharField(max_length=500)
    album = models.ForeignKey('chatbot.Album', related_name='music', on_delete=models.CASCADE, blank=True, null=True)
    genre = models.CharField(max_length=255, blank=True, null=True)
    artists = models.ManyToManyField(Artist, related_name='music')
    release = models.DateField(blank=True, null=True)
    length = models.PositiveSmallIntegerField(blank=True, default=0)
    original_rating = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Evaluation(models.Model):
    user = models.ForeignKey('chatbot.Muser', related_name='evaluations', on_delete=models.CASCADE)
    music = models.ForeignKey('chatbot.Music', related_name='evaluations', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(blank=False)

    def __str__(self):
        return f'{self.music.title}-{self.user.username}'


class Message(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey('chatbot.Muser', related_name='sent_messages', on_delete=models.CASCADE, blank=True, null=True)
    receiver = models.ForeignKey('chatbot.Muser', related_name='received_messages', on_delete=models.CASCADE, blank=True, null=True)
    text = models.TextField(blank=True)
    music = models.ForeignKey('chatbot.Music', on_delete=models.CASCADE, blank=True, null=True)
    chips = models.CharField(validators=[int_list_validator], max_length=255, default=[])

    def __str__(self):
        if not self.sender:
            return f'mu-bot -> {self.receiver.username}'
        else:
            return f'{self.sender.username} -> mu-bot'
