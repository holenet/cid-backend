from django.contrib import admin

# Register your models here.

from .models import *

admin.site.register(User)
admin.site.register(Artist)
admin.site.register(SoloArtist)
admin.site.register(GroupArtist)
admin.site.register(Album)
admin.site.register(Music)
admin.site.register(Evaluation)
admin.site.register(Message)
