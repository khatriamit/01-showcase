from rest_framework import serializers
from datetime import date


class UpdateBookingCheckoutSerializer(serializers.Serializer):
    checkout_date = serializers.DateField()

    def validate_checkout_date(self, value):
        if value < date.today():
            raise serializers.ValidationError(
                "checkout date should not accept past dates"
            )
        return value
