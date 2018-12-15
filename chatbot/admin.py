from django.contrib import admin
from rest_framework.authtoken.models import Token

from .models import *


def ellipsize(list, max=2):
    sub = ', '.join(map(str, list[:max]))
    if len(list) > 2:
        return sub + ', ...'
    return sub


class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'number_of_music', 'number_of_albums', 'debut', 'agent', 'original_id')

    def type(self, obj):
        if SoloArtist.objects.filter(id=obj.id).exists():
            return 'solo'
        if GroupArtist.objects.filter(id=obj.id).exists():
            return 'group'
        return None

    def number_of_music(self, obj):
        return obj.music.count()
    number_of_music.short_description = '# of music'

    def number_of_albums(self, obj):
        return obj.albums.count()
    number_of_albums.short_description = '# of albums'


class SoloArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'group', 'birthday', 'debut', 'agent', 'original_id')

    def group(self, obj):
        groups = GroupArtist.objects.filter(members__id__exact=obj.id)
        if groups.exists():
            return ellipsize(groups)
        return None


class GroupArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'number_of_members', 'debut', 'agent', 'original_id')

    def number_of_members(self, obj):
        return obj.members.count()
    number_of_members.short_description = '# of members'


class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'number_of_music', 'genre', 'release', 'album_image', 'original_id')

    def artist(self, obj):
        return ellipsize(obj.artists.all())

    def number_of_music(self, obj):
        return obj.music.count()
    number_of_music.short_description = '# of music'

    def album_image(self, obj):
        return obj.image is not None
    album_image.boolean = True


class MusicAdmin(admin.ModelAdmin):
    list_display = ('title', 'album', 'artist', 'genre', 'length', 'release', 'original_rating', 'original_id')

    def artist(self, obj):
        return ellipsize(obj.artists.all())


class MuserAdmin(admin.ModelAdmin):
    list_display = ('username', 'gender_string', 'birthdate', 'number_of_messages', 'cluster', 'signed_in', 'pushtoken')

    def gender_string(self, obj):
        if obj.gender == 1:
            return 'male'
        if obj.gender == 2:
            return 'female'
        return None
    gender_string.short_description = 'gender'

    def number_of_messages(self, obj):
        return (Message.objects.filter(sender=obj) | Message.objects.filter(receiver=obj)).count()
    number_of_messages.short_description = '# of messages'

    def signed_in(self, obj):
        return Token.objects.filter(user=obj).exists()
    signed_in.boolean = True

    def pushtoken(self, obj):
        return obj.push_token is not None
    pushtoken.boolean = True
    pushtoken.short_description = 'push token'


class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'direction', 'text', 'created', 'music', 'number_of_chips')
    readonly_fields = ('id', 'sender', 'receiver', 'direction', 'text', 'created', 'music', 'chips')

    def direction(self, obj):
        if obj.sender is None:
            return f'🡺 {obj.receiver}'
        if obj.receiver is None:
            return f'🡸 {obj.sender}'

    def number_of_chips(self, obj):
        if obj.music is not None:
            return len(eval(obj.chips))
        return None
    number_of_chips.short_description = '# of chips'


class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'music', 'rating')


admin.site.register(Artist, ArtistAdmin)
admin.site.register(SoloArtist, SoloArtistAdmin)
admin.site.register(GroupArtist, GroupArtistAdmin)
admin.site.register(Album, AlbumAdmin)
admin.site.register(Music, MusicAdmin)
admin.site.register(Muser, MuserAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Evaluation, EvaluationAdmin)
