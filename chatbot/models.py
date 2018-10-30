import pyfcm
from django.conf import settings

from django.core.validators import int_list_validator
from django.db import models
from django.contrib.auth import models as auth_models


class Muser(auth_models.User):
    objects = auth_models.UserManager()

    gender = models.PositiveSmallIntegerField(blank=True, default=0) # 1: male, 2: female
    birthdate = models.DateField(blank=True, null=True)

    push_token = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.username


class Artist(models.Model):
    name = models.CharField(max_length=100, blank=True, default='')
    debut = models.DateField(blank=True, null=True)
    agent = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return self.name


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
    title = models.CharField(max_length=100, blank=True, default='')
    artists = models.ManyToManyField(Artist)
    release = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.title


class Music(models.Model):
    title = models.CharField(max_length=100)
    album = models.ForeignKey('chatbot.Album', related_name='music', on_delete=models.CASCADE, blank=True, null=True)
    artists = models.ManyToManyField(Artist)
    genre = models.CharField(max_length=100, blank=True, default='')
    length = models.PositiveSmallIntegerField(blank=True, default=0)

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
    chips = models.CharField(validators=[int_list_validator], max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs):
        is_first = self.id is None
        super(Message, self).save(*args, **kwargs)
        if self.sender is None and is_first and self.receiver.push_token is not None:
            # push notification to user device
            push_service = pyfcm.FCMNotification(api_key=settings.SERVER_KEY)
            push_service.notify_single_device(registration_id=self.receiver.push_token, data_message={'message_id': self.id, 'text': self.text})

    def __str__(self):
        if not self.sender:
            return f'mu-bot -> {self.receiver.username}'
        else:
            return f'{self.sender.username} -> mu-bot'
