from __future__ import absolute_import, unicode_literals

import socket

import requests
from fcm_django.models import FCMDevice

from backend.celery import app
from chatbot.models import Message, Muser


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
def respond(user_id, text):
    print(f'respond {user_id}')
    from random import sample

    user = Muser.objects.get(pk=user_id)
    text = chatscript(user.username, text)
    chips = sample(range(0, 20), 4)
    message = Message.objects.create(receiver=user, text=text, chips=chips)

    device = FCMDevice.objects.filter(user=user).first()
    if device:
        retry = 10
        for _ in range(retry):
            try:
                device.send_message(data={'message_id': message.id, 'text': text})
            except requests.exceptions.ReadTimeout as e:
                print(e)
            else:
                break
