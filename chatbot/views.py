from django.contrib.auth import authenticate
from django.core import exceptions
from django.views.decorators.csrf import csrf_exempt

from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_200_OK
from rest_framework.response import Response

from chatbot.models import Muser
from chatbot.serializers import MuserSerializer
from chatbot.permissions import IsExactMuser


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def signin(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if username is None or password is None:
        return Response({'error': 'username/password not given'}, status=HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'credentials invalid'}, status=HTTP_404_NOT_FOUND)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key}, status=HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def signout(request):
    auth = request.environ.get('HTTP_AUTHORIZATION')
    if auth is None:
        return Response({'error': 'Authorization not given'}, status=HTTP_400_BAD_REQUEST)

    key = auth.replace("Token ", "")
    try:
        token = Token.objects.get(key=key)
        token.delete()
        return Response(status=HTTP_200_OK)
    except exceptions.ObjectDoesNotExist:
        return Response({'error': 'Authorization invalid'}, status=HTTP_404_NOT_FOUND)


class MuserList(generics.ListAPIView):
    queryset = Muser.objects.all()
    serializer_class = MuserSerializer
    permission_classes = (AllowAny,)


class MuserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Muser.objects.all()
    serializer_class = MuserSerializer
    permission_classes = (IsExactMuser,)
