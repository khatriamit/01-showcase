from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from mobileapi.serializers.booking import *


class UserBookedByViewset(viewsets.ModelViewSet):
    """
    listing the booking done by user
    """
    serializer_class = UserBookingSerializer

    def get_queryset(self):
        bookings = []
        if self.request.user.is_authenticated:
            bookings = Booking.objects.filter(booked_by=self.request.user, is_deleted=False)
        return bookings

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(booked_by=self.request.user, property=Organisation.objects.get(id=self.request.data.get('property')))
        serializer.save(property=Organisation.objects.get(id=self.request.data.get('property')))
        serializer.save()

    def create(self, request, *args, **kwargs):
        user_info = request.data.get('user_info', {})
        if user_info:
            if user_info.get('name'):
                if not isinstance(user_info.get('name'), str):
                    return Response({"error": "Invalid User name, must be string"},
                                    status=status.HTTP_406_NOT_ACCEPTABLE)

            if user_info.get('email'):
                if '@' not in user_info.get('email') or '.' not in user_info.get('email'):
                    return Response({"error": "Invalid email"},
                                    status=status.HTTP_406_NOT_ACCEPTABLE)

            if user_info.get('country'):
                if len(user_info.get('country')) > 10:
                    return Response({"error": "Country length must be less than 10"})

            if request.data.get('user_info', {}).get('mobile'):
                if len(request.data.get('user_info', {}).get('mobile')) < 10:
                    return Response({"error": "Invalid Phone number length"},
                                    status=status.HTTP_406_NOT_ACCEPTABLE)
        return super(UserBookedByViewset, self).create(request, *args, **kwargs)