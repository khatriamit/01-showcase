from rest_framework import serializers
from booking.models import Booking
from users.serializers import UserSerializer


class TodaysBookingSerializer(serializers.ModelSerializer):
    booked_by =  UserSerializer(read_only=True)
    room_type = serializers.CharField(read_only=True)
    nights = serializers.CharField(read_only=True)
    no_of_children = serializers.CharField(read_only=True)
    no_of_adults = serializers.CharField(read_only=True)
    booking_ref = serializers.CharField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "property",
            "booked_by",
            "user_info",
            "booking_ref",
            "checkin_date",
            "checkout_date",
            "payment_status",
            "paid_amount",
            "nights",
            "no_of_children",
            "no_of_adults",
            "room_type"
        ]