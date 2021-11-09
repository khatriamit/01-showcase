from django.contrib.auth import models
from rest_framework import serializers
from users.models import Referrals, UserReferPointStat, SecondaryUserReferral
from users.serializers import UserSerializer


class ReferralSerializer(serializers.ModelSerializer):
    referred = UserSerializer(read_only=True)

    class Meta:
        model = Referrals
        fields = ("id", "referred", "referred_by", "created_date")


class UserReferPointStatSerializer(serializers.ModelSerializer):
    current_point = serializers.FloatField()
    added_point = serializers.FloatField()
    previous_point = serializers.FloatField()

    class Meta:
        model = UserReferPointStat
        fields = (
            "id",
            "current_point",
            "added_point",
            "previous_point",
            "user",
            "created_at",
        )


class SecondaryReferralSerializer(serializers.ModelSerializer):
    referred = UserSerializer(read_only=True)
    referred_by = UserSerializer(read_only=True)

    class Meta:
        model = SecondaryUserReferral
        fields = (
            "id",
            "referred",
            "referred_by",
            "main_referred_by",
            "created_date",
        )
