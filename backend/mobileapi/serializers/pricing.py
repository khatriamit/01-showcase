from rest_framework import serializers
from rest_framework.serializers import ValidationError
import datetime
from organisation.models import OrganisationRoomPricing


class OrganisationRoomPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganisationRoomPricing
        read_only_fields = ["organisation", "created_by"]
        fields = [
            "id",
            "organisation",
            "from_date",
            "to_date",
            "room_type",
            "price",
            "created_on",
            "created_by"
        ]

    def validate_from_date(self, value):
        if value < datetime.date.today():
            raise ValidationError("from_date should be greater than past dates")
        return value

    def validate_to_date(self, value):
        if value < datetime.date.today():
            raise ValidationError("to_date should be greater than past dates")
        return value

    def validate_price(self, value):
        if value < 0:
            raise ValidationError("price should be greater than 0")
        return value

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        if to_date < from_date:
            raise ValidationError("to_date should be greater than from_date")
        return attrs