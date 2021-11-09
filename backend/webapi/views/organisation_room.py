from django.db import models
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from rest_framework.generics import get_object_or_404
import datetime
import pandas as pd
from organisation.models import Organisation, Room
from checkin.models import AssignedRoom
from backend.utils import convert_str_to_date


def get_dates_between_two_date(sdate, edate):
    return (
        pd.date_range(sdate, edate - datetime.timedelta(days=1), freq="d")
        .strftime("%Y-%m-%d")
        .tolist()
    )


def check_room_status(df, room_number, date_):
    for index, row in df.iterrows():
        if room_number in row["assigned_rooms"] and date_ in row["dates"]:
            return "Booked"


class OrganisationRoomDetailAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        organisation = request.query_params.get("property")
        room_category = request.query_params.get("room_category")
        from_date = request.query_params.get("from_date")
        days = request.query_params.get("days")
        if organisation and room_category and from_date and days:
            organisation = get_object_or_404(
                Organisation, id=organisation, user=self.request.user, is_deleted=False
            )
            if room_category.lower() not in ["single", "double", "deluxe"]:
                raise ValidationError(f"invalid room_category")
            rooms = Room.objects.filter(
                organisation=organisation,
                category=room_category.title(),
                is_deleted=False,
            ).values("room_numbers")
            to_date = convert_str_to_date(from_date) + datetime.timedelta(
                days=int(days)
            )
            filter_dates = get_dates_between_two_date(from_date, to_date)
            assigned_rooms = AssignedRoom.objects.filter(
                checkin_checkout_information__booking__property=organisation,
            ).values(
                "assigned_rooms",
                "checkin_checkout_information__booking__checkin_date",
                "checkin_checkout_information__booking__checkout_date",
            )
            df = pd.DataFrame(assigned_rooms)
            df["dates"] = df.apply(
                lambda row: get_dates_between_two_date(
                    row["checkin_checkout_information__booking__checkin_date"],
                    row["checkin_checkout_information__booking__checkout_date"],
                ),
                axis=1,
            )

            room_numbers = [
                room_number
                for room in list(rooms)
                for room_number in room.get("room_numbers")
            ]
            room_detail = []
            for room_number in room_numbers:
                info = []
                for date_ in filter_dates:
                    info.append(
                        {
                            "date": date_,
                            "status": check_room_status(df, room_number, date_),
                        }
                    )
                room_detail.append({room_number: info})
            return Response(room_detail)
        raise ValidationError(
            {
                "missing": "organisation, room_category, from_date and days are the required query param"
            }
        )
