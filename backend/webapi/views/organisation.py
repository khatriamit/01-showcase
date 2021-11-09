from backend.utils import convert_str_to_date
from booking.models import Booking
from django.shortcuts import get_object_or_404
import pandas as pd
import datetime
from django.db.models import Q, Count, Sum, Avg, Min
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from common.models import UserSearchHistory
from rest_framework.generics import ListCreateAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from webapi.serializers.organisation import (
    UserSearchHistorySerializer,
    OrganisationRoomBasicInfoSerializer,
)
from mobileapi.serializers.organisation import OrganisationListInfoSerializer
from mobileapi.views.dashboard import check_if_organisation_authorized
from organisation.models import Organisation, Room, OrganisationRoomUnavailability


class UserSearchHistoryAPIView(ListCreateAPIView):
    queryset = UserSearchHistory.objects.filter(is_deleted=False)
    serializer_class = UserSearchHistorySerializer


class PopularDestinationAPIView(ListAPIView):
    """
    CASE:
        1. If no search_key provided most booked hotel in the world
    """

    serializer_class = OrganisationListInfoSerializer

    def get_queryset(self):
        queryset = Organisation.objects.filter(
            is_deleted=False, is_visible=True
        ).annotate(
            number_of_booked=Count(
                "booked_organisation",
                filter=Q(
                    booked_organisation__is_deleted=False,
                    booked_organisation__cancelled=False,
                ),
            )
        )
        parent_search_key = self.request.query_params.get("parent_search_key")
        child_search_key = self.request.query_params.get("child_search_key")
        if parent_search_key:
            queryset = queryset.filter(
                Q(name__icontains=parent_search_key)
                | Q(location__city__icontains=parent_search_key)
                | Q(location__country__icontains=parent_search_key)
                | Q(location__continent__icontains=parent_search_key)
            )

        if child_search_key:
            queryset = queryset.filter(
                Q(name__icontains=child_search_key)
                | Q(location__city__icontains=child_search_key)
                | Q(location__country__icontains=child_search_key)
                | Q(location__continent__icontains=child_search_key)
            )
        queryset = queryset.annotate(
            user_rating=Avg("rating__rating_star", filter=Q(rating__is_deleted=False)),
            min_room_price=Min("rooms__price", filter=Q(rooms__is_deleted=False)),
        )
        return queryset.order_by("-number_of_booked")


class OrganisationRoomListAPIView(ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("property")
        if organisation:
            organisation = check_if_organisation_authorized(organisation, request.user)
            rooms = Room.objects.filter(organisation=organisation)
            serializer = OrganisationRoomBasicInfoSerializer(rooms, many=True)
            return Response(serializer.data)
        raise ValidationError({"missing": "property is required query param"})


class OrganisationRoomAvailability(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.request.query_params.get("booking_id")

        checkin_date = self.request.query_params.get("checkin_date")
        checkout_date = self.request.query_params.get("checkout_date")
        checkin_date = convert_str_to_date(checkin_date)
        checkout_date = convert_str_to_date(checkout_date)
        if checkin_date < datetime.date.today():
            raise ValidationError(
                {"checkin_date": "checkin_date should not accept past dates"}
            )

        if checkout_date < datetime.date.today():
            raise ValidationError(
                {"checkout_date": "checkout_date should not accept past dates"}
            )

        if checkin_date > checkout_date:
            raise ValidationError(
                {"error": "checkin date should not be greater than checkout date"}
            )

        if checkin_date and checkout_date and booking_id:

            booking = get_object_or_404(
                Booking,
                id=booking_id,
                property__user=self.request.user,
                is_deleted=False,
            )
            # if checkin_date != booking.checkout_date:
            #     raise ValidationError(
            #         {
            #             "checkin_date": "checkin_date should be equal to old checkout date"
            #         }
            #     )
            organisation = get_object_or_404(
                Organisation, id=booking.property.id, is_deleted=False
            )
            bookings = Booking.objects.filter(
                ~Q(payment_status="Draft"),
                ~Q(id=booking_id),
                property=organisation,
                is_deleted=False,
                cancelled=False,
            )
            from_date = checkin_date
            to_date = checkout_date
            if to_date < from_date:
                raise ValidationError(
                    {"error": "to_date should not be less than from_date"}
                )

            # here I got all the bookings in the given from and to dates
            bookings = bookings.filter(
                Q(checkin_date__gte=from_date, checkout_date__lte=to_date)
                | Q(checkin_date__lte=from_date, checkout_date__gte=from_date)
                | Q(checkin_date__lte=to_date, checkout_date__gte=to_date)
            )

            # since we have single, double, deluxe category I calculated total number of provided category room is booked
            single_number_of_room_booked = bookings.filter(
                room_detail__room__category="Single"
            ).aggregate(Sum("room_detail__no_of_rooms"))
            double_number_of_room_booked = bookings.filter(
                room_detail__room__category="Double"
            ).aggregate(Sum("room_detail__no_of_rooms"))
            deluxe_number_of_room_booked = bookings.filter(
                room_detail__room__category="Deluxe"
            ).aggregate(Sum("room_detail__no_of_rooms"))
            if not single_number_of_room_booked.get("room_detail__no_of_rooms__sum"):
                single_number_of_room_booked = 0
            else:
                single_number_of_room_booked = single_number_of_room_booked.get(
                    "room_detail__no_of_rooms__sum"
                )

            if not double_number_of_room_booked.get("room_detail__no_of_rooms__sum"):
                double_number_of_room_booked = 0
            else:
                double_number_of_room_booked = double_number_of_room_booked.get(
                    "room_detail__no_of_rooms__sum"
                )

            if not deluxe_number_of_room_booked.get("room_detail__no_of_rooms__sum"):
                deluxe_number_of_room_booked = 0
            else:
                deluxe_number_of_room_booked = deluxe_number_of_room_booked.get(
                    "room_detail__no_of_rooms__sum"
                )

            # check how many rooms are unavailable on provided date range
            organisation_unavailability = OrganisationRoomUnavailability.objects.filter(
                Q(from_date__gte=from_date, to_date__lte=to_date)
                | Q(from_date__lte=from_date, to_date__gte=from_date)
                | Q(from_date__lte=to_date, to_date__gte=to_date),
                organisation=organisation,
                is_deleted=False,
            ).values("room_numbers")
            unavailable_rooms = [
                r
                for room in organisation_unavailability
                for r in room.get("room_numbers")
            ]
            rooms = Room.objects.filter(
                organisation=organisation, is_deleted=False
            ).values("id", "room_numbers", "category")

            available_room_category = {
                room.get("category"): room.get("id") for room in rooms
            }
            rooms_df = pd.DataFrame(rooms)
            if not rooms_df.empty:
                rooms_df["filtered_rooms"] = rooms_df.apply(
                    lambda row: list(set(row["room_numbers"]) - set(unavailable_rooms)),
                    axis=1,
                )
                rooms_df["room_count"] = rooms_df.apply(
                    lambda row: len(row["filtered_rooms"]), axis=1
                )
                total_single_room = rooms_df.loc[
                    rooms_df["category"] == "Single", "room_count"
                ].sum()
                total_double_room = rooms_df.loc[
                    rooms_df["category"] == "Double", "room_count"
                ].sum()
                total_deluxe_room = rooms_df.loc[
                    rooms_df["category"] == "Deluxe", "room_count"
                ].sum()
                res = {}
                room_detail = []
                total_single_available = (
                    total_single_room - single_number_of_room_booked
                )
                if "Single" in available_room_category.keys():
                    room_detail.append(
                        {
                            "id": available_room_category["Single"],
                            "category": "Single",
                            "available_count": total_single_available
                            if total_single_available >= 0
                            else 0,
                        }
                    )

                total_double_available = (
                    total_double_room - double_number_of_room_booked
                )

                if "Double" in available_room_category.keys():
                    room_detail.append(
                        {
                            "id": available_room_category["Double"],
                            "category": "Double",
                            "available_count": total_double_available
                            if total_double_available >= 0
                            else 0,
                        }
                    )

                total_deluxe_available = (
                    total_deluxe_room - deluxe_number_of_room_booked
                )

                if "Deluxe" in available_room_category.keys():
                    room_detail.append(
                        {
                            "id": available_room_category["Deluxe"],
                            "category": "Deluxe",
                            "available_count": total_deluxe_available
                            if total_deluxe_available >= 0
                            else 0,
                        }
                    )
                res.update({"room_details": room_detail})
                return Response(res)
            return Response([])
        else:
            raise ValidationError(
                {
                    "missing_query_param": "checkin_date, checkout_date and booking_id is required query param"
                }
            )
