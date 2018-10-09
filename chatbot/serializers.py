from rest_framework import serializers
from chatbot.models import Muser, Evaluation

class MuserSerializer(serializers.ModelSerializer):
    def validate_gender(self, value):
        if 3 <= value:
            raise serializers.ValidationError("gender value must be one of 0, 1, 2")
        return value

    class Meta:
        model = Muser
        fields = ('id', 'username', 'gender', 'birthdate', 'evaluations', )
        read_only_fields = ('username', )
