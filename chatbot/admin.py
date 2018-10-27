from django.contrib import admin

from .models import *

admin.site.register([Muser, Artist, SoloArtist, GroupArtist, Album, Music, Evaluation, Message])
