from __future__ import absolute_import, unicode_literals

import socket

import requests
from django.contrib.postgres.search import TrigramSimilarity
from fcm_django.models import FCMDevice

from backend.celery import app
from chatbot.models import Message, Muser, Evaluation, Music, Artist
from chatbot.recommend import recommend


def chatscript(username, text):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 1024))
    content = f'{username}\0\0{text}\0'
    sock.send(bytes(content, encoding='utf-8'))
    response = sock.recv(1024).decode('utf-8')
    sock.close()
    return response


@app.task
def greet(user_id):
    user = Muser.objects.get(pk=user_id)
    text = chatscript(user.username, '')
    Message.objects.create(receiver=user, text=text)


@app.task
def respond(user_id, user_text):
    user = Muser.objects.get(pk=user_id)
    text = chatscript(user.username, user_text)
    message = None
    if '@@' in text:
        text, cmd_opt = text.split('@@')
        cmd, opt = cmd_opt.split(':')
        cmd = cmd.strip().lower()
        opt = eval('dict(' + opt.strip()[1:-1] + ')')
        if cmd == 'recommend':
            profit, music = recommend(user, opt)
            user.recommended.add(music)

            if not profit:
                text = 'Sorry, I cannot find such music. What about this?'
            chips = [1, 2]
            message = Message.objects.create(receiver=user, text=text, music=music, chips=chips)
        elif cmd == 'evaluate':
            rating = int(opt['rating'])
            title = opt['title'].strip()
            music = Music.objects.filter(title__trigram_similar=title).annotate(similarity=TrigramSimilarity('title', title)).order_by('-similarity').first()
            if music:
                Evaluation.objects.create(user_id=user_id, music=music, rating=rating)
            else:
                text = 'Sorry, I cannot find such music.'
        ###
        elif cmd == 'fan':
            artist_name = opt.get('artist')
            genre_name = opt.get('genre')

            if artist_name:
                artist = Artist.objects.filter(name__trigram_similar=artist_name).annotate(similarity=TrigramSimilarity('name', artist_name)).order_by('-similarity').first()
                if artist:
                    user.fan_artists.add(artist)
                else:
                    text = "Sorry, I haven't heard of that artist. What kind of artist is he?"

            if genre_name:
                music =  Music.objects.filter(genre__trigram_similar=genre_name).annotate(similarity=TrigramSimilarity('genre', genre_name)).order_by('-similarity').first()
                if music:
                    genre_name = music.genre
                    fan_genres = user.fan_genres
                    if genre_name in fan_genres:
                        pass
                    else:
                        user.fan_genres.set(fan_genres + genre_name + "@")
                else:
                    text = "Sorry, I haven't heard of that genre. What kind of genre is it?"
        ###

    if message is None:
        message = Message.objects.create(receiver=user, text=text)

    for device in FCMDevice.objects.filter(user=user):
        send_push.delay(device.id, message.id)


@app.task
def send_push(device_id, message_id):
    device = FCMDevice.objects.get(pk=device_id)
    message = Message.objects.get(pk=message_id)
    retry = 10
    for _ in range(retry):
        try:
            device.send_message(data={'message_id': message.id, 'text': message.text})
        except requests.exceptions.ReadTimeout as e:
            print(e)
        else:
            break
