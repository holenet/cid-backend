from rest_framework import serializers
from chatbot.models import Muser, Evaluation

class MuserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Muser
        fields = ('id', 'username', 'gender', 'age', 'evaluations',)