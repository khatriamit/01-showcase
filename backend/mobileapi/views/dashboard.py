from django.db.models import Sum, Count, F, Q
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from booking.serializers import UserBookingSerializer
import datetime
import pandas as pd

from organisation.models import Organisation
from booking.models import Booking
from mobileapi.serializers.dashboard import TodaysBookingSerializer


def get_forward_month_list():
    months_choices = []
    for i in range(1, 13):
        months_choices.append((i, datetime.date(2008, i, 1).strftime("%b")))
    return months_choices


def check_if_organisation_authorized(organisation, user):
    """
    helper function to check if organisation is belongs to user or not
    """
    try:
        organisation = Organisation.objects.get(
            id=organisation, user=user, is_deleted=False
        )
        return organisation
    except Organisation.DoesNotExist:
        raise ValidationError(
            {
                "error": "Either organisation with ID doesn't exists or unauthorized access"
            }
        )


def get_year_based_bookings(organisation, last_year, current_year):
    if last_year:
        bookings = Booking.objects.filter(
            created_on__date__year=last_year,
            is_deleted=False,
            cancelled=False,
            property=organisation,
        ).values(
            "id",
            "room_detail__room__category",
            "room_detail__price",
            "created_on__date__month",
            "paid_amount",
        )
    else:
        bookings = Booking.objects.filter(
            created_on__date__year=current_year,
            is_deleted=False,
            cancelled=False,
            property=organisation,
        ).values(
            "id",
            "room_detail__room__category",
            "room_detail__price",
            "created_on__date__month",
            "paid_amount",
        )
    return bookings


class DashboardTotalAnalytics(APIView):
    """
    api view to calculat
    """

    def get(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("property")
        organisation = check_if_organisation_authorized(organisation, self.request.user)
        today_date = datetime.date.today()
        first = today_date.replace(day=1)
        current_month = today_date.month
        lastMonth = first - datetime.timedelta(days=1)
        yesterday_date = datetime.date.today() - datetime.timedelta(1)
        today_bookings = Booking.objects.filter(
            created_on__date=today_date,
            is_deleted=False,
            cancelled=False,
            property=organisation,
        )
        yesterday_bookings = Booking.objects.filter(
            created_on__date=yesterday_date,
            is_deleted=False,
            cancelled=False,
            property=organisation,
        )
        today_booking_count = today_bookings.count()
        yesterday_booking_count = yesterday_bookings.count()
        booking_guests_today = today_bookings.annotate(
            total_guests=F("room_detail__no_of_children")
            + F("room_detail__no_of_adults")
        )
        booking_guests_yesterday = yesterday_bookings.annotate(
            total_guests=F("room_detail__no_of_children")
            + F("room_detail__no_of_adults")
        )
        today_guest_count = booking_guests_today.aggregate(Sum("total_guests"))
        yesterday_guest_count = booking_guests_yesterday.aggregate(Sum("total_guests"))
        today_revenue = booking_guests_today.aggregate(Sum("paid_amount"))
        yesterday_revenue = booking_guests_yesterday.aggregate(Sum("paid_amount"))

        bookings_occupy_current_month = Booking.objects.filter(
            created_on__date__year=today_date.year,
            created_on__date__month=current_month,
            is_deleted=False,
            cancelled=False,
            property=organisation,
        ).aggregate(Sum("room_detail__no_of_rooms"))

        bookings_occupy_last_month = Booking.objects.filter(
            created_on__date__year=today_date.year,
            created_on__date__month=lastMonth.month,
            is_deleted=False,
            cancelled=False,
            property=organisation,
        ).aggregate(Sum("room_detail__no_of_rooms"))

        earning_analytics = {
            "today_booking_count": today_booking_count,
            "yesterday_booking_count": yesterday_booking_count,
            "today_guest_count": today_guest_count.get("total_guests__sum")
            if today_guest_count.get("total_guests__sum")
            else 0,
            "yesterday_guest_count": yesterday_guest_count.get("total_guests__sum")
            if yesterday_guest_count.get("total_guests__sum")
            else 0,
            "today_revenue": today_revenue.get("paid_amount__sum")
            if today_revenue.get("paid_amount__sum")
            else 0,
            "yesterday_revenue": yesterday_revenue.get("paid_amount__sum")
            if yesterday_revenue.get("paid_amount__sum")
            else 0,
            "bookings_occupy_current_month": bookings_occupy_current_month.get(
                "room_detail__no_of_rooms__sum"
            )
            if bookings_occupy_current_month.get("room_detail__no_of_rooms__sum")
            else 0,
            "bookings_occupy_last_month": bookings_occupy_last_month.get(
                "room_detail__no_of_rooms__sum"
            )
            if bookings_occupy_last_month.get("room_detail__no_of_rooms__sum")
            else 0,
        }
        return Response(earning_analytics)


class DashboardEarningAnalyticsView(APIView):
    """
    api view for viewing organisation earning based on room type
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("property")
        organisation = check_if_organisation_authorized(organisation, self.request.user)
        current_year = datetime.date.today().year
        last_year = self.request.query_params.get("last_year")
        bookings = get_year_based_bookings(organisation, last_year, current_year)
        months = get_forward_month_list()
        earning_based_on_room_type = {}
        bookings_dataframe = pd.DataFrame(bookings)
        for mnth in months:
            if not bookings_dataframe.empty:
                earning_based_on_room_type.update(
                    {
                        mnth[1]: [
                            {
                                "Single": bookings_dataframe.loc[
                                    (
                                        bookings_dataframe[
                                            "room_detail__room__category"
                                        ]
                                        == "Single"
                                    )
                                    & (
                                        bookings_dataframe["created_on__date__month"]
                                        == mnth[0]
                                    ),
                                    "paid_amount",
                                ].sum()
                            },
                            {
                                "Double": bookings_dataframe.loc[
                                    (
                                        bookings_dataframe[
                                            "room_detail__room__category"
                                        ]
                                        == "Double"
                                    )
                                    & (
                                        bookings_dataframe["created_on__date__month"]
                                        == mnth[0]
                                    ),
                                    "paid_amount",
                                ].sum()
                            },
                            {
                                "Deluxe": bookings_dataframe.loc[
                                    (
                                        bookings_dataframe[
                                            "room_detail__room__category"
                                        ]
                                        == "Deluxe"
                                    )
                                    & (
                                        bookings_dataframe["created_on__date__month"]
                                        == mnth[0]
                                    ),
                                    "paid_amount",
                                ].sum()
                            },
                        ]
                    }
                )
            else:
                earning_based_on_room_type.update(
                    {mnth[1]: [{"Single": 0}, {"Double": 0}, {"Deluxe": 0}]}
                )
        return Response(earning_based_on_room_type)


class DashboardTodaysBookingView(APIView, PageNumberPagination):
    """
    api view for listing the todays booking
    """

    permission_classes = (IsAuthenticated,)
    page_size = 5

    def get(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("property")
        organisation = check_if_organisation_authorized(organisation, self.request.user)
        filter_date = self.request.query_params.get("filter_date")
        if filter_date:
            bookings = Booking.objects.filter(
                created_on__date=filter_date,
                is_deleted=False,
                cancelled=False,
                property=organisation,
            )
        else:
            bookings = Booking.objects.filter(
                created_on__date=datetime.date.today(),
                is_deleted=False,
                cancelled=False,
                property=organisation,
            )
        bookings = bookings.annotate(
            booking_ref=F("uuid"),
            nights=F("checkout_date") - F("checkin_date"),
            no_of_children=F("room_detail__no_of_children"),
            no_of_adults=F("room_detail__no_of_adults"),
            room_type=F("room_detail__room__category"),
        )
        bookings = self.paginate_queryset(bookings, self.request)
        serializer = TodaysBookingSerializer(bookings, many=True)
        return self.get_paginated_response(serializer.data)


class DashboardTotalBooking(APIView):
    """
    api view for visualizing the total bookings
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("property")
        organisation = check_if_organisation_authorized(organisation, self.request.user)
        current_year = datetime.date.today().year
        last_year = self.request.query_params.get("last_year")
        monthly_number_of_bookings = {}
        months = get_forward_month_list()
        bookings = get_year_based_bookings(organisation, last_year, current_year)
        bookings_dataframe = pd.DataFrame(bookings)
        for mnth in months:
            if not bookings_dataframe.empty:
                monthly_number_of_bookings.update(
                    {
                        mnth[1]: bookings_dataframe.loc[
                            bookings_dataframe["created_on__date__month"] == mnth[0],
                            "id",
                        ].count()
                    }
                )
            else:
                monthly_number_of_bookings.update({mnth[1]: 0})
        return Response(monthly_number_of_bookings)


class DashboardTodayToBeCheckInListView(APIView, PageNumberPagination):
    permission_classes = (IsAuthenticated,)
    page_size = 5

    def get(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("property")
        organisation = check_if_organisation_authorized(organisation, self.request.user)
        bookings = Booking.objects.filter(
            checkin_checkout_information=None,
            checkin_date=datetime.date.today(),
            is_deleted=False,
            cancelled=False,
            property=organisation,
        )
        bookings = self.paginate_queryset(bookings, self.request)
        serializer = UserBookingSerializer(bookings, many=True)
        return self.get_paginated_response(serializer.data)
