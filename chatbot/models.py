from django.db import models
from django.contrib.auth.models import User, UserManager


class Hotel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    address = models.CharField(max_length=100, blank=True, default='')
    contact = models.CharField(max_length=100, blank=True, default='')
    website = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ('created',)