from django.db import models


class Crawler(models.Model):
    started = models.DateTimeField(auto_now_add=True)