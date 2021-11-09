from booking.serializers import UserBookingSerializer
import json
from django.db.models import Q, Sum, F
from django.db.models.functions import Coalesce
from package.models import Package, PackageBooking
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from webapi.utils.helpers import validate_package_booking
from webapi.views.abstract.validation import UserInfo
from webapi.serializers.package import (
    UpdatePackageBookingSerializer,
    PackageBookingSerializer,
)
from package.domain.model import package_booking_factory
from package.helpers import calculate_price


class UpdatePackageBookingUserInfo(APIView):
    """
    API View to update the package booking user info
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_package_booking(booking_id, self.request.user)
        return Response(booking.user_info)

    def put(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_package_booking(booking_id, self.request.user)
        try:
            UserInfo(**request.data)
        except Exception as e:
            raise ValidationError({"error": json.loads(e.json())})
        booking.user_info = request.data
        booking.save()
        return Response(booking.user_info)


class UpdatePackageBookingDetail(APIView):
    """
    API view to update the package checkin and quantity
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_package_booking(booking_id, self.request.user)
        total_booking = PackageBooking.objects.filter(
            ~Q(id=booking_id),
            ~Q(payment_status="Draft"),
            package=booking.package,
            is_deleted=False,
            cancelled=False,
        ).aggregate(total_booking=Coalesce(Sum("quantity"), 0))
        booking.valid_checkin_start_date = booking.package.checkin_valid_start_date
        booking.valid_checkin_end_date = booking.package.checkin_valid_end_date
        booking.available_quantity = booking.package.quantity - total_booking.get(
            "total_booking"
        )
        serializer = UpdatePackageBookingSerializer(booking)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_package_booking(booking_id, self.request.user)
        request.data.update(
            {"package_id": booking.package, "user_info": booking.user_info}
        )
        serializer = PackageBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = Package.objects.values(
            "id",
            "quantity",
            "booking_start_date",
            "booking_end_date",
            "checkin_valid_start_date",
            "checkin_valid_end_date",
        ).get(id=booking.package.id)
        booked_package_count = PackageBooking.objects.filter(
            ~Q(id=booking_id),
            ~Q(payment_status="Draft"),
            package__id=package.get("id"),
            cancelled=False,
            is_deleted=False,
        ).aggregate(number_of_booked=Coalesce(Sum("quantity"), 0))
        try:
            booking_factory = package_booking_factory(
                package=package,
                checkin_date=serializer.data.get("checkin_date"),
                quantity=serializer.data.get("quantity"),
                number_of_booked=booked_package_count.get("number_of_booked"),
            )
        except Exception as e:
            raise ValidationError({"error": e})

        booking = PackageBooking.objects.get(id=booking_id)
        pricing_detail = calculate_price(booking.package, booking_factory.quantity)
        booking.checkin_date = booking_factory.checkin_date
        booking.quantity = booking_factory.quantity
        booking.total_amount = pricing_detail.get("total")
        booking.gst_amount = pricing_detail.get("gst_amount")
        booking.save()
        serializer = UpdatePackageBookingSerializer(booking)
        return Response(serializer.data)


class GetPackageBookingPriceDetail(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        booking_id = self.kwargs.get("id")
        booking = validate_package_booking(booking_id, self.request.user)
        serializer = PackageBookingSerializer(booking)
        pricing_detail = calculate_price(booking.package, booking.quantity)
        serializer.data.get("package").pop("organisation")
        res = {"booking_detail": serializer.data, "pricing_detail": pricing_detail}
        return Response(res)
