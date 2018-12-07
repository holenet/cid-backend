import mimetypes

from django.contrib.auth import authenticate, password_validation
from django.core import exceptions
from django.db.utils import IntegrityError
from django.http import HttpResponse
from fcm_django.models import FCMDevice

from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_200_OK

from chatbot.models import Muser, Message, Album
from chatbot.serializers import MuserSerializer, MessageSerializer
from chatbot.tasks import respond, greet


@api_view(['POST'])
@permission_classes((AllowAny,))
def signup(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if username is None or password is None:
        return Response({'error': 'username/password not given'}, status=HTTP_400_BAD_REQUEST)

    user = None
    try:
        user = Muser.objects.create_user(username=username, password=password)
        password_validation.validate_password(password, user=user)
        return Response({'detail': 'sign-up successful'}, status=HTTP_200_OK)
    except IntegrityError:
        return Response({'username': 'username already taken'}, status=HTTP_400_BAD_REQUEST)
    except exceptions.ValidationError as e:
        if user is not None:
            user.delete()
        return Response({'password': e}, status=HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes((AllowAny,))
def signin(request):
    username = request.data.get('username')
    password = request.data.get('password')
    push_token = request.data.get('push_token')
    if username is None or password is None:
        return Response({'error': 'username/password not given'}, status=HTTP_400_BAD_REQUEST)
    if push_token is None:
        return Response({'error': 'token not given'}, status=HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'username/password invalid'}, status=HTTP_404_NOT_FOUND)

    device, _ = FCMDevice.objects.get_or_create(registration_id=push_token)
    device.user = user
    device.active = True
    device.save()

    greet.delay(user.id)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key}, status=HTTP_200_OK)


@api_view(['POST'])
@permission_classes((AllowAny,))
def signout(request):
    auth = request.environ.get('HTTP_AUTHORIZATION')
    if auth is None:
        return Response({'error': 'Authorization not given'}, status=HTTP_400_BAD_REQUEST)

    key = auth.replace("Token ", "")
    try:
        token = Token.objects.get(key=key)
        if token.user:
            device = FCMDevice.objects.filter(user=token.user).first()
            if device:
                device.user = None
                device.active = False
                device.save()
        token.delete()
        return Response(status=HTTP_200_OK)
    except exceptions.ObjectDoesNotExist:
        return Response({'error': 'Authorization invalid'}, status=HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes((AllowAny,))
def withdraw(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if username is None or password is None:
        return Response({'error': 'username/password not given'}, status=HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'credentials invalid'}, status=HTTP_404_NOT_FOUND)

    try:
        token = Token.objects.get(user=user)
        token.delete()
    except exceptions.ObjectDoesNotExist:
        pass

    user.delete()
    return Response({'detail': 'withdraw successful'}, status=HTTP_200_OK)


class MuserDetail(generics.RetrieveUpdateAPIView):
    queryset = Muser.objects.all()
    serializer_class = MuserSerializer

    def get_object(self):
        return Muser.objects.get_by_natural_key(self.request.user.username)

    def update(self, request, *args, **kwargs):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if old_password is not None and new_password is not None:
            user = self.get_object()
            if user.check_password(old_password) is True:
                try:
                    password_validation.validate_password(new_password, user=user)
                    user.set_password(new_password)
                    user.save()
                    Token.objects.get(user=user).delete()
                except exceptions.ValidationError as e:
                    return Response({'error': e}, status=HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'credentials invalid'}, status=HTTP_400_BAD_REQUEST)

        return super(MuserDetail, self).update(request, *args, **kwargs)


class Chat(generics.ListCreateAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)

    def perform_create(self, serializer):
        user = Muser.objects.get_by_natural_key(self.request.user.username)
        text = self.request.data.get('text')
        serializer.save(sender=user, text=text)
        respond.delay(user.id, text)


class ChatDetail(generics.RetrieveAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)


@api_view(['GET'])
@permission_classes((AllowAny,))
def album_image(request, album_id):
    try:
        album = Album.objects.get(id=album_id)
    except Album.DoesNotExist:
        return Response({'detail': 'The album does not exist'}, status=HTTP_404_NOT_FOUND)
    with open(album.image.path, 'rb') as f:
        response = HttpResponse(f, content_type=mimetypes.guess_type(album.image.path))
        response['Content-Disposition'] = f'attachment; filename={album.image.name}'
        return response
