from django.db.models import Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
import datetime
from organisation.models import Organisation, Room, OrganisationRoomUnavailability
from mobileapi.serializers.unavailability import (
    OrganisationRoomUnavailabilitySerializer,
)
from mobileapi.utils.custom_filter import RoomUnavailabilityFilter
from booking.models import BookingDetail


class OrganisationRoomUnAvailabilityViewset(viewsets.ModelViewSet):
    """
    api view to perform organisation room unavailability CRUD:
    CASES:
        case1:room_numbers coming from front-end must
              be in the organisation room numbers
        case2:from_date should be greater than past dates
        case3:to_date should not be greater than from_date and should be greater than past_dates
        case4:organisation should belong to logged in user
        case5:room unavailability with similar from_date, to_date, room_type and  room_number not applicable
        case6: validation as if room is available to set unavailability or not
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = OrganisationRoomUnavailabilitySerializer
    queryset = OrganisationRoomUnavailability.objects.none()
    filter_backends = [DjangoFilterBackend]
    filter_class = RoomUnavailabilityFilter

    def validate_room_unavailability(self, serializer):
        room_numbers = serializer.validated_data.get("room_numbers")
        organisation = self.request.query_params.get("organisation")
        room_types = self.request.data.get("room_type")
        from_date = self.request.data.get("from_date")
        to_date = self.request.data.get("to_date")
        try:
            Organisation.objects.get(
                id=organisation, user=self.request.user, is_deleted=False
            )
        except Organisation.DoesNotExist:
            raise ValidationError(
                {
                    "error": "Either organisation with this ID doesn't exists or you are unauthorized"
                }
            )
        if OrganisationRoomUnavailability.objects.filter(
            **serializer.validated_data, organisation__id=organisation, is_deleted=False
        ).exists():
            raise ValidationError(
                {"error": "room unavailability with such room_detail already exists"}
            )
        organisation_room_numbers = Room.objects.filter(organisation__id=organisation)
        organisation_rooms = []
        [
            [
                organisation_rooms.append(room_number)
                for room_number in room.room_numbers
            ]
            for room in list(organisation_room_numbers)
        ]
        for room in room_numbers:
            if room not in organisation_rooms:
                raise ValidationError({"error": f"Invalid room : {room}"})

        booked_rooms = BookingDetail.objects.filter(
            ~Q(booking__payment_status="Draft"),
            Q(
                booking__checkin_date__gte=from_date,
                booking__checkout_date__lte=to_date,
            )
            | Q(
                booking__checkin_date__lte=from_date,
                booking__checkout_date__gte=from_date,
            )
            | Q(
                booking__checkin_date__lte=to_date,
                booking__checkout_date__gte=to_date,
            ),
            booking__property__id=organisation,
            booking__is_deleted=False,
            booking__cancelled=False,
        )
        single_booked_rooms = booked_rooms.filter(room__category="Single").aggregate(
            Sum("no_of_rooms")
        )
        double_booked_rooms = booked_rooms.filter(room__category="Double").aggregate(
            Sum("no_of_rooms")
        )
        deluxe_booked_rooms = booked_rooms.filter(room__category="Deluxe").aggregate(
            Sum("no_of_rooms")
        )

        if single_booked_rooms.get("no_of_rooms__sum") is None:
            single_booked_rooms = 0
        else:
            single_booked_rooms = single_booked_rooms.get("no_of_rooms__sum")

        if double_booked_rooms.get("no_of_rooms__sum") is None:
            double_booked_rooms = 0
        else:
            double_booked_rooms = double_booked_rooms.get("no_of_rooms__sum")

        if deluxe_booked_rooms.get("no_of_rooms__sum") is None:
            deluxe_booked_rooms = 0
        else:
            deluxe_booked_rooms = deluxe_booked_rooms.get("no_of_rooms__sum")

        for room_type in room_types:
            organisation_rooms = []
            count = 0
            [
                [
                    organisation_rooms.append(room_number)
                    for room_number in room.room_numbers
                ]
                for room in list(organisation_room_numbers.filter(category=room_type))
            ]
            for room in room_numbers:
                if room in organisation_rooms:
                    count += 1

            if room_type == "Single":
                if single_booked_rooms == len(organisation_rooms):
                    raise ValidationError(
                        {
                            "error": "All the rooms are already booked for the selected date range"
                        }
                    )
                elif len(organisation_rooms) - single_booked_rooms < count:
                    available_rooms = len(organisation_rooms) - single_booked_rooms
                    if available_rooms < 0:
                        raise ValidationError(
                            {
                                "error": "All the rooms are already booked for the selected date range"
                            }
                        )
                    raise ValidationError(
                        {
                            "error": f"{single_booked_rooms} rooms are already booked for the selected date range"
                        }
                    )

            if room_type == "Double":
                if double_booked_rooms == len(organisation_rooms):
                    raise ValidationError(
                        {
                            "error": "All the rooms are already booked for the selected date range"
                        }
                    )
                elif len(organisation_rooms) - double_booked_rooms < count:
                    available_rooms = len(organisation_rooms) - double_booked_rooms
                    if available_rooms < 0:
                        raise ValidationError(
                            {
                                "error": "All the rooms are already booked for the selected date range"
                            }
                        )
                    raise ValidationError(
                        {
                            "error": f"{double_booked_rooms} rooms are already booked for the selected date range"
                        }
                    )

            if room_type == "Deluxe":
                if deluxe_booked_rooms == len(organisation_rooms):
                    raise ValidationError(
                        {
                            "error": "All the rooms are already booked for the selected date range"
                        }
                    )
                elif len(organisation_rooms) - deluxe_booked_rooms < count:
                    available_rooms = len(organisation_rooms) - deluxe_booked_rooms
                    if available_rooms < 0:
                        raise ValidationError(
                            {
                                "error": "All the rooms are already booked for the selected date range"
                            }
                        )
                    raise ValidationError(
                        {
                            "error": f"{deluxe_booked_rooms} rooms are already booked for the selected date range"
                        }
                    )

    def get_queryset(self):
        queryset = OrganisationRoomUnavailability.objects.filter(
            organisation__user=self.request.user, is_deleted=False
        ).exclude(to_date__lt=datetime.date.today())
        return queryset

    def perform_create(self, serializer):
        organisation = self.request.query_params.get("organisation")
        serializer.save(
            organisation=Organisation(id=organisation), created_by=self.request.user
        )

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.validate_room_unavailability(serializer)
        return super(OrganisationRoomUnAvailabilityViewset, self).create(
            request, *args, **kwargs
        )

    def update(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.validate_room_unavailability(serializer)
        return super(OrganisationRoomUnAvailabilityViewset, self).update(
            request, *args, **kwargs
        )
