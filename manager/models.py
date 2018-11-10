from django.db import models


class CrawlerStatus(models.Model):
    started = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.started} ({self.progress} %)'


class Crawler(models.Model):
    created = models.DateTimeField(auto_now_add=True)
