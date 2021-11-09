import requests
import json
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from booking.models import Booking
from package.models import PackageBooking
from rest_framework.generics import get_object_or_404
from datetime import date


url = "http://ip-api.com/json/"


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_visitor_info(ip_address, request):
    res = requests.get(url + str(ip_address))
    res_text = json.loads(res.text)
    visited_url = request.get_full_path()

    result = {
        "ip_address": ip_address,
        "country": res_text.get("country"),
        "countryCode": res_text.get("countryCode"),
    }
    return result


def validate_booking(booking_id, user):
    booking = get_object_or_404(
        Booking,
        Q(checkin_checkout_information=None)
        | Q(checkin_checkout_information__checkin_status="B"),
        ~Q(payment_status="Draft"),
        id=booking_id,
        is_deleted=False,
        cancelled=False,
        property__user=user,
        checkout_date__gte=date.today(),
    )
    return booking


def validate_package_booking(booking_id, user):
    booking = get_object_or_404(
        PackageBooking,
        Q(checkin_checkout_information=None)
        | Q(checkin_checkout_information__checkin_status="B"),
        ~Q(payment_status="Draft"),
        id=booking_id,
        is_deleted=False,
        cancelled=False,
        package__organisation__user=user,
    )
    return booking
