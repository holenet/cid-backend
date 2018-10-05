from django.contrib import admin

# Register your models here.

from .models import *

admin.site.register([User, Artist, SoloArtist, GroupArtist, Album, Music, Evaluation, Message])
