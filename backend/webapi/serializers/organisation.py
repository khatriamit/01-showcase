from rest_framework import serializers
from common.models import UserSearchHistory
from organisation.models import Room


class UserSearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSearchHistory
        fields = ["id", "uuid", "content", "created_on", "modified_on"]

    def validate_content(self, value):
        if UserSearchHistory.objects.filter(content=value).exists():
            raise serializers.ValidationError(
                "user search history with provided data already exists"
            )
        return value


class OrganisationRoomBasicInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "category", "no_of_rooms"]
