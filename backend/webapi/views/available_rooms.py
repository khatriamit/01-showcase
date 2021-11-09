from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from django.db.models import Q
from checkin.models import CheckInCheckOutInformation
from organisation.models import Organisation, RoomDetail
from booking.models import Booking, BookingDetail


class GetAvailableRoomNumbers(APIView):
    """
    API view to get the available rooms
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.request.query_params.get("booking_id")
        if booking_id:
            if Booking.objects.filter(id=booking_id).exists():
                booking = Booking.objects.get(id=booking_id)
            else:
                raise ValidationError(
                    {"booking_id": "Booking with this ID doesn't exists "}
                )
            checkin_checkout_info = CheckInCheckOutInformation.objects.filter(
                ~Q(booking__payment_status="Draft"),
                Q(
                    booking__checkin_date__gte=booking.checkin_date,
                    booking__checkout_date__lte=booking.checkout_date,
                )
                | Q(
                    booking__checkin_date__lte=booking.checkin_date,
                    booking__checkout_date__gte=booking.checkin_date,
                )
                | Q(
                    booking__checkin_date__lte=booking.checkout_date,
                    booking__checkout_date__gte=booking.checkout_date,
                ),
                checkin_status="Check in",
            ).values("room__assigned_rooms")
            assigned_room_numbers = []
            [
                assigned_room_numbers.append(r)
                for room_number in checkin_checkout_info
                for r in room_number.get("room__assigned_rooms")
            ]

            room_type = [
                room.get("room__category")
                for room in BookingDetail.objects.filter(booking=booking).values(
                    "room__category"
                )
            ]
            res = []
            for type_ in room_type:
                total_room_numbers = Organisation.objects.filter(
                    id=booking.property.id, rooms__category=type_
                ).values("rooms__room_numbers")
                room_numbers = []
                [
                    room_numbers.append(r)
                    for room_number in total_room_numbers
                    for r in room_number.get("rooms__room_numbers")
                ]

                available_rooms = [
                    room for room in room_numbers if room not in assigned_room_numbers
                ]
                res.append({type_: available_rooms})
            return Response(res)
        raise ValidationError(
            {
                "missing_query_param": "booking_id and room_type is required query parameter"
            }
        )
