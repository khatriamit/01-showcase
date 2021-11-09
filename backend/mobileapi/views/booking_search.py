from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q, Sum, Count, F
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
import datetime
from organisation.models import Organisation
from booking.models import Booking
from organisation.models import (
    OrganisationSpecialDeal,
    Room,
    OrganisationRoomUnavailability,
)
from mobileapi.serializers.special_deal import OrganisationSpecialDealSerializer
from mobileapi.utils.helpers import ArrayLength
import pandas as pd


def convert_to_set(a, b):
    return list(set(a) - set(b))


class BookingSearchAPIView(APIView):
    """
    booking search API along with special deals
    """

    def get(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("organisation")
        organisation = get_object_or_404(
            Organisation, id=organisation, is_deleted=False
        )
        bookings = Booking.objects.filter(
            ~Q(payment_status="Draft"),
            property=organisation,
            is_deleted=False,
            cancelled=False,
        )
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")

        if from_date and to_date:
            from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").date()
            if from_date < datetime.date.today():
                raise ValidationError(
                    {"error": "from_date should not accept past dates"}
                )
            if to_date < datetime.date.today():
                raise ValidationError({"error": "to_date should not accept past dates"})
            if to_date < from_date:
                raise ValidationError(
                    {"error": "to_date should not be less than from_date"}
                )

            # here I got all the bookings in the given from and to dates
            bookings = bookings.filter(
                ~Q(payment_status="Draft"),
                Q(checkin_date__gte=from_date, checkout_date__lte=to_date)
                | Q(checkin_date__lte=from_date, checkout_date__gte=from_date)
                | Q(checkin_date__lte=to_date, checkout_date__gte=to_date),
                is_deleted=False,
                cancelled=False,
            )

            # get all the special deals that are applicable for the give from and to dates
            special_deals = OrganisationSpecialDeal.objects.filter(
                Q(from_date__gte=from_date, to_date__lte=to_date)
                | Q(from_date__lte=from_date, to_date__gte=from_date)
                | Q(from_date__lte=to_date, to_date__gte=to_date),
                organisation=organisation,
                is_deleted=False,
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
                # booking_detail.update({
                #     "booked_dates": get_dates_between_two_dates(booking.checkin_date, booking.checkout_date),
                #     "single_number_of_room_booked": single_number_of_room_booked,
                #     "double_number_of_room_booked": double_number_of_room_booked,
                #     "deluxe_number_of_room_booked": deluxe_number_of_room_booked
                # })

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
                res = {
                    "special_deals": OrganisationSpecialDealSerializer(
                        special_deals, many=True
                    ).data,
                }
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
                {"missing_query_param": "from_date and to_date is required query param"}
            )
