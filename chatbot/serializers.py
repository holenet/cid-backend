from rest_framework import serializers
from chatbot.models import Muser, Evaluation

class MuserSerializer(serializers.ModelSerializer):
    evaluations = serializers.PrimaryKeyRelatedField(many=True, queryset=Evaluation.objects.all())

    class Meta:
        model = Muser
        fields = ('id', 'username', 'gender', 'age', 'evaluations',)