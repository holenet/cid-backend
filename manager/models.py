from django.db import models


class Crawler(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    level = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, default='Preparing')
    progress = models.FloatField(null=True, blank=True, default=None)
    remain = models.IntegerField(null=True, blank=True, default=None)
    destroy = models.BooleanField(default=False)
    error = models.TextField(null=True, blank=True, default=None)
