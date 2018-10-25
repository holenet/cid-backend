from django.db.models import signals
from django.dispatch import receiver
from manager.models import Crawler

@receiver(signals.pre_save, sender=Crawler)
def crawl(sender, instance, **kwargs):
    print('crawler instance created!')