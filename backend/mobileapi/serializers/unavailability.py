from rest_framework import serializers
import datetime
from organisation.models import OrganisationRoomUnavailability, Room


class OrganisationRoomUnavailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganisationRoomUnavailability
        read_only_fields = ["organisation", "created_by"]
        fields = [
            "id",
            "organisation",
            "from_date",
            "to_date",
            "room_type",
            "room_numbers",
            "created_on",
            "created_by"
        ]

    def validate_from_date(self, value):
        if value < datetime.date.today():
            raise serializers.ValidationError("from_date should not accept past dates")
        return value

    def validate_to_date(self, value):
        if value < datetime.date.today():
            raise serializers.ValidationError("to_date should not accept past dates")
        return value

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        if to_date < from_date:
            raise serializers.ValidationError("to_date should not be less than past dates")
        return attrs

