from django.contrib import admin

# Register your models here.

from .models import *

admin.site.register([Muser, Artist, SoloArtist, GroupArtist, Album, Music, Evaluation, Message])
