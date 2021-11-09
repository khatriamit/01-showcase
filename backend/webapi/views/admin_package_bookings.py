from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from backend.utils import CustomPageSizePagination
from package.models import PackageBooking
from webapi.serializers.package import PackageBookingSerializer
from datetime import date
from backend.utils import convert_str_to_date
from webapi.utils.export_booking_data import package_booking_export
from mobileapi.views.dashboard import check_if_organisation_authorized


class CommonPackageBookingInfoViewset(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = PackageBookingSerializer
    queryset = PackageBooking.objects.none()
    http_method_names = ["get"]
    pagination_class = CustomPageSizePagination

    def get_queryset(self):
        organisation = self.request.query_params.get("property")
        guest_name = self.request.query_params.get("guest_name")
        booking_ref = self.request.query_params.get("booking_ref")
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")
        if from_date and to_date:
            from_date = convert_str_to_date(from_date)
            to_date = convert_str_to_date(to_date)
            if to_date < from_date:
                raise ValidationError(
                    {"error": "to_date cannot be less than from_date"}
                )
        if organisation:
            organisation = check_if_organisation_authorized(
                organisation, self.request.user
            )
            queryset = PackageBooking.objects.filter(
                is_deleted=False, cancelled=False, package__organisation=organisation
            )
            if guest_name:
                queryset = queryset.filter(Q(user_info__name__icontains=guest_name))
            if from_date:
                queryset = queryset.filter(checkin_date__gte=from_date)
            if to_date:
                queryset = queryset.filter(package__checkin_valid_end_date__lte=to_date)
            if booking_ref:
                queryset = queryset.filter(uuid__icontains=booking_ref)
            return queryset
        else:
            raise ValidationError({"error": "property is required query parameter"})


class OwnerUpcomingPackageBooking(CommonPackageBookingInfoViewset):
    def get_queryset(self):
        queryset = super(OwnerUpcomingPackageBooking, self).get_queryset()
        queryset = queryset.filter(
            Q(checkin_checkout_information=None)
            | Q(checkin_checkout_information__checkin_status="B"),
            checkin_date__gt=date.today(),
        )
        return queryset

    @action(detail=False, methods=["get"])
    def export(self, request):
        queryset = self.get_queryset()
        d_ = date.today()
        url = package_booking_export(
            queryset, "package-booking-upcoming_" + d_.strftime("%Y-%m-%d")
        )
        return Response({"download_url": url})


class OwnerOngoingPackageBooking(CommonPackageBookingInfoViewset):
    def get_queryset(self):
        queryset = super(OwnerOngoingPackageBooking, self).get_queryset()
        queryset = queryset.filter(
            checkin_checkout_information__checkin_status="Ci",
            checkin_date__lte=date.today(),
            package__checkin_valid_end_date__gte=date.today(),
        )
        return queryset

    @action(detail=False, methods=["get"])
    def export(self, request):
        queryset = self.get_queryset()
        d_ = date.today()
        url = package_booking_export(
            queryset, "package-booking-ongoing_" + d_.strftime("%Y-%m-%d")
        )
        return Response({"download_url": url})


class OwnerCompletedPackageBooking(CommonPackageBookingInfoViewset):
    def get_queryset(self):
        queryset = super(OwnerCompletedPackageBooking, self).get_queryset()
        queryset = queryset.filter(
            package__checkin_valid_end_date__lt=date.today(),
            checkin_checkout_information__checkin_status="Co",
        )
        return queryset

    @action(detail=False, methods=["get"])
    def export(self, request):
        queryset = self.get_queryset()
        d_ = date.today()
        url = package_booking_export(
            queryset, "package-booking-completed_" + d_.strftime("%Y-%m-%d")
        )
        return Response({"download_url": url})


class OwnerCancelledPackageBooking(CommonPackageBookingInfoViewset):
    def get_queryset(self):
        organisation = self.request.query_params.get("property")
        guest_name = self.request.query_params.get("guest_name")
        booking_ref = self.request.query_params.get("booking_ref")
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")
        if from_date and to_date:
            from_date = convert_str_to_date(from_date)
            to_date = convert_str_to_date(to_date)
            if to_date < from_date:
                raise ValidationError(
                    {"error": "to_date cannot be less than from_date"}
                )
        if organisation:
            organisation = check_if_organisation_authorized(
                organisation, self.request.user
            )
            queryset = PackageBooking.objects.filter(
                is_deleted=False, cancelled=True, package__organisation=organisation
            )
            if guest_name:
                queryset = queryset.filter(Q(user_info__name__icontains=guest_name))
            if from_date:
                queryset = queryset.filter(checkin_date__gte=from_date)
            if to_date:
                queryset = queryset.filter(package__checkin_valid_end_date__lte=to_date)
            if booking_ref:
                queryset = queryset.filter(uuid__icontains=booking_ref)
            return queryset
        else:
            raise ValidationError({"error": "property is required query parameter"})

    @action(detail=False, methods=["get"])
    def export(self, request):
        queryset = self.get_queryset()
        d_ = date.today()
        url = package_booking_export(
            queryset, "package-booking-cancelled_" + d_.strftime("%Y-%m-%d")
        )
        return Response({"download_url": url})
