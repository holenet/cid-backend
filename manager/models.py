from django.core.validators import MinValueValidator
from django.db import models


class Crawler(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    level = models.PositiveSmallIntegerField(default=1)
    thread = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=100, default='Preparing')
    progress = models.FloatField(null=True, blank=True, default=None)
    remain = models.IntegerField(null=True, blank=True, default=None)
    cancel = models.BooleanField(default=False)
    error = models.TextField(null=True, blank=True, default=None)
    detail = models.TextField(null=True, blank=True, default=None)
    started = models.DateTimeField(null=True, blank=True, default=None)
    elapsed = models.IntegerField(null=True, blank=True, default=None)
