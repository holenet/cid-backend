from django.db import models


class Crawler(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Preparing')
    progress = models.FloatField(null=True, blank=True, default=None)
    remain = models.IntegerField(null=True, blank=True, default=None)
    destroy = models.BooleanField(default=False)
    error = models.TextField(null=True, blank=True, default=None)

    def __str__(self):
        if self.error:
            return f'{self.created} {self.status}'
        if self.progress is not None:
            if self.remain is not None:
                return f'{self.created} {self.status}...{self.progress:.1f}% ({self.remain}s remaining)'
            return f'{self.created} {self.status}...{self.progress:.1f}%'
        return f'{self.created} {self.status}'
