from django.contrib import admin

from .models import *


class CrawlerAdmin(admin.ModelAdmin):
    list_display = ('id', 'level', 'status', 'detail', 'progress_percentage', 'elapsed_time', 'remaining_time', 'started', 'cancel')
    readonly_fields = ('id', 'status', 'progress', 'remain', 'error', 'detail', 'created', 'started', 'elapsed')

    def progress_percentage(self, obj):
        if obj.progress is not None:
            return f'{obj.progress:.1f} %'
        else:
            return None

    def elapsed_time(self, obj):
        if obj.elapsed is not None:
            return f'{obj.elapsed} s'
        return None

    def remaining_time(self, obj):
        if obj.remain is not None:
            return f'{obj.remain} s'
        return None


admin.site.register(Crawler, CrawlerAdmin)
