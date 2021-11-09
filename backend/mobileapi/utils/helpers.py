from django.db.models import CharField, IntegerField
from booking.models import Booking
import datetime

from django.db.models import F, Sum, Avg, Prefetch, Q, Value
from django.db.models.aggregates import Min
from django.db.models.functions import Coalesce

from backend.countries_list import countries
from rest_framework.serializers import ValidationError
from datetime import timedelta
from django.db import models

from organisation.models import Organisation, OrganisationRoomUnavailability, Room
from common.models import UserSearchHistory


def get_country_flag(country):
    for c in countries:
        if c["name"] == country.capitalize():
            return c["flag_url"]
    return None


def get_dates_between_two_dates(from_date, to_date):
    delta = to_date - from_date  # as timedelta
    dates = []
    for i in range(delta.days + 1):
        day = from_date + timedelta(days=i)
        dates.append(day.strftime("%Y-%m-%d"))
    return dates


class ArrayLength(models.Func):
    function = "CARDINALITY"


def validate_rating(ratings, queryset):
    if "," in ratings:
        ratings = ratings.split(",")
        for rating in ratings:
            if rating not in ["1", "2", "3", "4", "5"]:
                raise ValidationError(
                    {"error": "rating only accepts the value 1,2,3,4,5"}
                )
        queryset = queryset.filter(user_rating__in=ratings)
    else:
        if ratings not in ["1", "2", "3", "4", "5"]:
            raise ValidationError({"error": "rating only accepts the value 1,2,3,4,5"})
        queryset = queryset.filter(user_rating=ratings)
    return queryset


def get_filter_organisations(request):
    """
    helper function to apply filter into the organisation
    """
    min_price = request.query_params.get("min_price")
    max_price = request.query_params.get("max_price")
    facilities = request.query_params.get("facilities")
    city = request.query_params.get("city")
    checkin_date = request.query_params.get("checkin_date")
    checkout_date = request.query_params.get("checkout_date")
    category = request.query_params.get("category")
    queryset = Organisation.objects.filter(
        is_deleted=False, property_status="Published", is_visible=True
    ).order_by("-pk")
    children = request.query_params.get("children")
    adult = request.query_params.get("adult")
    no_of_rooms = request.query_params.get("no_of_rooms", 0)
    rooms = Room.objects.filter(is_deleted=False).annotate(
        number_of_available_rooms=F("no_of_rooms")
        - Coalesce(
            Sum(
                "booked_room__no_of_rooms",
                filter=Q(
                    booked_room__booking__is_deleted=False,
                    booked_room__booking__checkin_date__gte=datetime.date.today(),
                    booked_room__booking__checkout_date__gt=datetime.date.today(),
                ),
            ),
            0,
        )
    )

    if category:
        if "{" in category:
            category = [int(i) for i in category.strip("{").strip("}").split(",")]
            queryset = queryset.filter(category__id__in=category)
    if min_price and float(min_price) < 0:
        raise ValidationError({"error": "min_price must be valid positive value"})

    if max_price and float(max_price) < 0:
        raise ValidationError({"error": "max_price must be valid positive value"})

    if min_price and max_price:
        if float(max_price) < float(min_price):
            raise ValidationError(
                {"error": "max_price should not be less than min price"}
            )

    search_key = request.query_params.get("search_key")
    if search_key:
        queryset = queryset.filter(
            Q(name__icontains=search_key)
            | Q(location__city__icontains=search_key)
            | Q(location__country__icontains=search_key)
            | Q(category__name__icontains=search_key)
        )

    parent_search_key = request.query_params.get("parent_search_key")
    if parent_search_key:
        queryset = queryset.filter(
            Q(name__icontains=parent_search_key)
            | Q(location__city__icontains=parent_search_key)
            | Q(location__country__icontains=parent_search_key)
            | Q(location__continent__icontains=parent_search_key)
            | Q(category__name__icontains=parent_search_key)
        )

    child_search_key = request.query_params.get("child_search_key")
    if child_search_key:
        queryset = queryset.filter(
            Q(name__icontains=child_search_key)
            | Q(location__city__icontains=child_search_key)
            | Q(location__country__icontains=child_search_key)
            | Q(location__continent__icontains=child_search_key)
            | Q(category__name__icontains=child_search_key)
        )

    if parent_search_key or child_search_key:
        res = {
            "parent_search_key": parent_search_key.title() if parent_search_key else "",
            "child_search_key": child_search_key.title() if child_search_key else "",
        }
        UserSearchHistory.objects.create(content=res)

    if facilities:
        queryset = queryset.filter(facilities__contains=facilities)

    if city:
        queryset = queryset.filter(location__city=city)

    if checkin_date and checkout_date:
        if (
            datetime.datetime.strptime(checkin_date, "%Y-%m-%d").date()
            < datetime.date.today()
        ):
            raise ValidationError({"error": "Invalid checkin date"})
        if (
            datetime.datetime.strptime(checkout_date, "%Y-%m-%d").date()
            <= datetime.date.today()
        ):
            raise ValidationError({"error": "Invalid checkout date"})

        if (
            datetime.datetime.strptime(checkin_date, "%Y-%m-%d").date()
            > datetime.datetime.strptime(checkout_date, "%Y-%m-%d").date()
        ):
            raise ValidationError(
                {"error": "checkin date should not be greater than checkout date"}
            )

    elif checkin_date:
        raise ValidationError({"error": "checkout_date is required"})

    elif checkout_date:
        raise ValidationError({"error": "checkin_date is required"})

    if checkin_date and checkout_date:
        total_unavailable = OrganisationRoomUnavailability.objects.filter(
            Q(
                from_date__gte=checkin_date,
                to_date__lte=checkout_date,
            )
            | Q(
                from_date__lte=checkin_date,
                to_date__gte=checkin_date,
            )
            | Q(
                from_date__lte=checkout_date,
                to_date__gte=checkout_date,
            ),
            is_deleted=False,
        )
        total_bookings = Booking.objects.filter(
            ~Q(payment_status="Draft"),
            Q(
                checkin_date__gte=checkin_date,
                checkout_date__lte=checkout_date,
            )
            | Q(
                checkin_date__lte=checkin_date,
                checkout_date__gte=checkin_date,
            )
            | Q(
                checkin_date__lte=checkout_date,
                checkout_date__gte=checkout_date,
            ),
            is_deleted=False,
            cancelled=False,
        )
        queryset = queryset.annotate(total_rooms=Sum("rooms__no_of_rooms"))
        exclude_org = []

        for q in list(queryset):
            total_room_booked = (
                total_bookings.filter(property=q).aggregate(
                    total_room_booked=Coalesce(Sum("room_detail__no_of_rooms"), 0)
                )
            ).get("total_room_booked")
            total_room_unavailable = (
                total_unavailable.filter(organisation=q).aggregate(
                    total_room_unavailable=Coalesce(Sum(ArrayLength("room_numbers")), 0)
                )
            ).get("total_room_unavailable")
            total_room_available = (
                q.total_rooms - total_room_booked - total_room_unavailable
            )
            if total_room_available <= no_of_rooms:
                exclude_org.append(q.id)
        queryset = queryset.exclude(id__in=exclude_org)
    if max_price or min_price:
        organisation_ids = rooms.filter(
            price__lte=max_price if max_price else 100000,
            price__gte=min_price if min_price else 0,
        ).values("organisation__id")
        queryset = queryset.filter(id__in=organisation_ids).prefetch_related(
            Prefetch(
                "rooms",
                queryset=rooms.filter(
                    price__lte=max_price if max_price else 100000,
                    price__gte=min_price if min_price else 0,
                ),
            )
        )
    elif max_price and min_price:
        organisation_ids = rooms.filter(
            price__lte=max_price,
            price__gte=min_price,
        ).values("organisation__id")
        queryset = queryset.filter(id__in=organisation_ids).prefetch_related(
            Prefetch(
                "rooms",
                queryset=rooms.filter(
                    price__lte=max_price,
                    price__gte=min_price,
                ),
            )
        )

    if children:
        queryset = queryset.filter(rooms__children_accomodate__gte=children)

    if adult:
        queryset = queryset.filter(rooms__accomodates__gte=adult)
    queryset = queryset.annotate(
        user_rating=Avg("rating__rating_star", filter=Q(rating__is_deleted=False)),
        min_room_price=Min("rooms__price", filter=Q(rooms__is_deleted=False)),
    )

    if request.query_params.get("ratings"):
        queryset = validate_rating(request.query_params.get("ratings"), queryset)
    return queryset
