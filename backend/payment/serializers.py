from rest_framework import serializers
from .models import PaymentMethod, SetRate
from organisation.models import Room


class PaymentMethodSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentMethod
        fields = '__all__'


class SetRateSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['category'] = Room.objects.get(id=instance.room.id).category
        return representation

    class Meta:
        model = SetRate
        fields = '__all__'