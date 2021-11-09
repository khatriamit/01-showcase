from rest_framework import serializers
from booking.models import *
from mobileapi.serializers.organisation import OrganisationListInfoSerializer


class UserBookedRoomSerializer(serializers.ModelSerializer):
    room_price = serializers.CharField(source='room.price', read_only=True)
    room_photo_url = serializers.CharField(source='room.photo_url', read_only=True)
    room_category = serializers.CharField(source='room.category', read_only=True)

    class Meta:
        model = BookingDetail
        fields = (
            'room_price', 'room_photo_url', 'room_category'
        )


class UserBookingSerializer(serializers.ModelSerializer):
    """
    organisation serializer
    """
    room_detail = UserBookedRoomSerializer(many=True, read_only=True)
    property = OrganisationListInfoSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id',
            'property',
            'paid_amount',
            'checkin_date',
            'checkout_date',
            'payment_status',
            'booked_by',
            'booked_on',
            'user_info',
            'room_detail',
        ]