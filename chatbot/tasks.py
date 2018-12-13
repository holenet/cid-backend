from __future__ import absolute_import, unicode_literals

import socket

import requests
from fcm_django.models import FCMDevice

from backend.celery import app
from chatbot.models import Message, Muser, Music


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
        command, args = text.split(':')
        command = command.strip().lower()
        args = 'dict(' + args.strip()[1:-1] + ')'
        if command == 'recommend':
            music = recommend(*eval(args))
            chips = [1, 2, 4]
            message = Message.objects.create(receiver=user, text=text, music=music, chips=chips)

    if message is None:
        message = Message.objects.create(receiver=user, text=text)

    for device in FCMDevice.objects.filter(user=user):
        send_push.delay(device.id, message.id)


def recommend(genre, artist):
    print(genre, artist)
    from random import randint
    music = Music.objects.all()[randint(0, Music.objects.count() - 1)]
    return music


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
