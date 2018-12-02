from django.contrib import admin

from .models import *


class CrawlerAdmin(admin.ModelAdmin):
    list_display = ('id', 'level', 'status', 'progress_percentage', 'remain_time', 'created', 'destroy')
    readonly_fields = ('id', 'status', 'progress', 'remain', 'error', 'created')

    def progress_percentage(self, obj):
        if obj.progress is not None:
            return f'{obj.progress:.1f}%'
        else:
            return None

    def remain_time(self, obj):
        if obj.remain is not None:
            return f'{obj.remain} s'
        else:
            return None


admin.site.register(Crawler, CrawlerAdmin)
