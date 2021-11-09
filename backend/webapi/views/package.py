from django.conf import settings
from django.db.models import (
    Count,
    Prefetch,
    Avg,
    Q,
    Min,
    Max,
    Case,
    When,
    CharField,
    Value,
    IntegerField,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    get_object_or_404,
    CreateAPIView,
)
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
import datetime

from rest_framework.views import APIView
from organisation.models import Organisation
from payment.models import KhaltiTransactionDetail
from webapi.serializers.package import (
    PackageSerializer,
    PackageBookingSerializer,
    PackageTypeSerializer,
)
from package.models import Package, PackageBooking, PackageType
from webapi.custom_filters import PackageFilterSet
from mobileapi.utils.helpers import validate_rating
import requests
from django.contrib.auth import get_user_model
from package.helpers import calculate_price
from datetime import date, datetime
from rest_framework.exceptions import ValidationError
from django.db.models import Sum, F
from backend.constant import MIN_BOOKING_PAYOUT_PERCENTAGE
from django.db import transaction
from booking.utils import packagebooking_esewa_verification

User = get_user_model()


class PackageListView(ListAPIView):
    """
    api view for listing the package that are not expire
    """

    serializer_class = PackageSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = PackageFilterSet

    @staticmethod
    def validate_start_end_date(start_date, end_date):
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError(
                    {"invalid": "start_date must be less than end date"}
                )

    def get_serializer_context(self):
        context = super(PackageListView, self).get_serializer_context()
        context["rating_filter"] = self.request.query_params.get("ratings")
        return context

    def get_queryset(self):
        checkin_date = self.request.query_params.get("checkin_date")
        no_of_nights = self.request.query_params.get("no_of_nights")

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        ratings = self.request.query_params.get("ratings")
        facilities = self.request.query_params.get("facilities")
        night_range = self.request.query_params.get("night_range")
        self.validate_start_end_date(start_date, end_date)
        q = self.request.query_params.get("q")
        organisation = self.request.query_params.get("organisation")
        package_type = self.request.query_params.get("package_type")
        available = self.request.query_params.get("available")
        queryset = Package.objects.filter(
            booking_start_date__lte=date.today(),
            booking_end_date__gte=date.today(),
            is_deleted=False,
            is_active=True,
        )
        if checkin_date:
            queryset = queryset.filter(
                checkin_valid_start_date__lte=checkin_date,
                checkin_valid_end_date__gte=checkin_date,
            )

        if no_of_nights:
            queryset = queryset.filter(number_of_nights__lte=int(no_of_nights))
        if package_type:
            if "[" in package_type:
                category = [
                    int(i) for i in package_type.strip("[").strip("]").split(",")
                ]
                queryset = queryset.filter(package_type__id__in=category)

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(organisation__location__city__icontains=q)
                | Q(organisation__location__country__icontains=q)
                | Q(organisation__location__street_name__icontains=q)
                | Q(organisation__location__street_address__icontains=q)
                | Q(organisation__location__zip_code__icontains=q)
                | Q(organisation__name__icontains=q)
                | Q(organisation__category__name__icontains=q)
                | Q(package_type__name__icontains=q)
            )
        if ratings:
            queryset = queryset.annotate(
                user_rating=Avg("organisation__rating__rating_star")
            )
            queryset = validate_rating(ratings, queryset)
        if night_range:
            night_range = night_range.strip("[").strip("]").split(",")
            queryset = queryset.filter(
                number_of_nights__gte=int(night_range[0]),
                number_of_nights__lte=int(night_range[1]),
            )

        if facilities:
            queryset = queryset.filter(organisation__facilities__contains=facilities)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if organisation:
            queryset = queryset.filter(
                organisation__id=organisation,
            ).order_by("-created_on")
        else:
            queryset = queryset.filter(
                is_deleted=False,
                is_active=True,
            ).order_by("organisation", "-created_on")
            queryset = Package.objects.filter(id__in=queryset).order_by("-created_on")

        if queryset:
            queryset = queryset.annotate(
                available_quantity=F("quantity")
                - Coalesce(
                    Sum(
                        "package_booking__quantity",
                        filter=Q(
                            ~Q(package_booking__payment_status="Draft"),
                            package_booking__is_deleted=False,
                            package_booking__cancelled=False,
                        ),
                    ),
                    0,
                )
            )
            if available:
                queryset = queryset.filter(available_quantity__gt=0)
        return queryset


class PackageSearchAPIView(APIView):
    """
    API View to get the search factor, in Package ListView
    """

    def get(self, request, *args, **kwargs):
        queryset = Package.objects.filter(
            is_deleted=False,
            is_active=True,
        )
        min_price = queryset.aggregate(Min("price"))
        max_price = queryset.aggregate(Max("price"))
        min_duration_nights = queryset.aggregate(Min("number_of_nights"))
        max_duration_nights = queryset.aggregate(Max("number_of_nights"))
        package_types = PackageType.objects.filter(is_deleted=False).values(
            "id", "name"
        )
        package_type_count = []
        [
            package_type_count.append(
                {
                    "id": package_type.get("id"),
                    "package_type": package_type.get("name"),
                    "package_type_count": queryset.filter(
                        package_type__id=package_type.get("id"),
                        booking_start_date__lte=date.today(),
                        booking_end_date__gte=date.today(),
                    ).count(),
                }
            )
            for package_type in list(package_types)
        ]
        res = {
            "min_price": min_price.get("price__min"),
            "max_price": max_price.get("price__max"),
            "max_duration_nights": max_duration_nights.get("number_of_nights__max"),
            "min_duration_nights": min_duration_nights.get("number_of_nights__min"),
            "package_type_count": package_type_count,
        }
        return Response(res)


class PackageDetailAPIView(RetrieveAPIView):
    """
    api view for package list
    """

    serializer_class = PackageSerializer

    def get_object(self):
        obj = get_object_or_404(
            Package, id=self.kwargs.get("pk"), is_deleted=False, is_active=True
        )
        total_booked_quantity = PackageBooking.objects.filter(
            ~Q(payment_status="Draft"),
            is_deleted=False,
            cancelled=False,
            package=obj,
        ).aggregate(total_booked_quantity=Coalesce(Sum("quantity"), 0))
        obj.available_quantity = obj.quantity - total_booked_quantity.get(
            "total_booked_quantity"
        )
        return obj


class PackageBookingAPI(viewsets.ModelViewSet):
    serializer_class = PackageBookingSerializer
    permission_classes = (IsAuthenticated,)
    queryset = PackageBooking.objects.none()

    def get_queryset(self):
        queryset = PackageBooking.objects.filter(
            is_deleted=False, booked_by=self.request.user
        ).annotate(booking_id=F("uuid"))
        upcoming = self.request.query_params.get("upcoming")
        ongoing = self.request.query_params.get("ongoing")
        completed = self.request.query_params.get("completed")
        cancelled = self.request.query_params.get("cancelled")
        queryset = queryset.annotate(
            upcoming=Case(
                When(checkin_date__gt=date.today(), then=Value(True)),
                default=False,
                output_field=CharField(),
            )
        )

        queryset = queryset.annotate(
            ongoing=Case(
                When(
                    checkin_date__lte=date.today(),
                    package__checkin_valid_end_date__gte=date.today(),
                    then=Value(True),
                ),
                default=False,
                output_field=CharField(),
            )
        )

        queryset = queryset.annotate(
            completed=Case(
                When(checkout_enddate__lt=date.today(), then=Value(True)),
                default=False,
                output_field=CharField(),
            )
        )

        if upcoming:
            queryset = queryset.filter(upcoming=True)
        if ongoing:
            queryset = queryset.filter(ongoing=True)
        if completed:
            queryset = queryset.filter(completed=True)
        if cancelled:
            queryset = queryset.filter(cancelled=True)
        return queryset

    def perform_create(self, serializer):
        package = self.request.data.get("package")
        serializer.save(
            package=Package.objects.get(id=package), booked_by=self.request.user
        )

    # def perform_create(self, serializer):
    # serializer.save(booked_by=self.request.user)

    def validate_date(self, serializer):
        package_obj = Package.objects.get(id=self.request.data["package_id"])
        user_info = self.request.data.get("user_info")
        quantity = self.request.data.get("quantity")
        checkin_date = self.request.data.get("checkin_date")
        today = date.today()
        checkin_data = self.request.data.get("checkin_date")
        checkin_date = datetime.strptime(checkin_data, "%Y-%m-%d").date()
        # chekcing today date
        if package_obj.booking_start_date <= today <= package_obj.booking_end_date:
            pass
        else:
            raise ValidationError(
                {
                    "error": "Date should be made between booking start date and booking end date"
                }
            )
        # chekcing checkin date
        if (
            package_obj.checkin_valid_start_date
            <= checkin_date
            <= package_obj.checkin_valid_end_date
        ):
            pass
        else:
            raise ValidationError(
                {
                    "error": "Date should be made between checkin start date and checkin end date"
                }
            )

        # check that package can be book or not based on the quantity
        if package_obj:
            packagebook_obj = package_obj.package_booking.filter(
                ~Q(payment_status="Draft"), is_deleted=False, cancelled=False
            ).aggregate(Sum("quantity"))
            if packagebook_obj.get("quantity__sum") is None:
                booked_quantity = 0
            else:
                booked_quantity = packagebook_obj.get("quantity__sum")
            available_quantity = package_obj.quantity - booked_quantity

            if available_quantity < self.request.data.get("quantity"):
                raise ValidationError({"error": "This Package is already full"})
        return serializer

    # create the package booking
    def create(self, request, *args, **kwargs):
        if "package_id" not in self.request.data.keys():
            raise ValidationError({"package_id": "this field is required"})
        try:
            package_obj = get_object_or_404(
                Package, id=self.request.data["package_id"], is_active=True
            )

            # check if package is inactive
            if package_obj.is_active == False:
                raise ValidationError({"error": "This package is already expired"})

            # self.request.data.update({"package": package_obj.id})
            quantity = self.request.data.get("quantity")
            calc = calculate_price(package_obj, quantity)
            self.request.data.update(
                {
                    "package": package_obj.id,
                    "total_amount": float(
                        float(package_obj.price * quantity) + calc["gst_amount"]
                    ),
                }
            )
            packagebooking_serializer = PackageBookingSerializer(self.request.data)
            self.validate_date(packagebooking_serializer)
            self.request.data.update(calc)
        except Package.DoesNotExist:
            raise ValidationError({"package": "doesn't exists"})
        response = super().create(request, *args, **kwargs)
        response.data.update(calc)
        return Response({"data": response.data})

    # cancel the package
    @action(detail=True, methods=["post"], url_path="cancel_packagebooking")
    def cancel_packagebooking(self, request, pk=None):
        packagebooking = self.get_object()
        packagebooking.cancelled = True
        packagebooking.save()
        serializer = self.get_serializer(packagebooking)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def confirm_booking(self, request, *args, **kwargs):
        with transaction.atomic():
            token = request.data.get("token", False)
            amount = request.data.get("paid_amount", False)
            package_obj = Package.objects.get(id=self.request.data["package_id"])
            quantity = self.request.data.get("quantity")

            packagebooking = self.get_object()
            payment_method = request.data.get("payment_method", False)
            # check if package is inactive
            print(payment_method)
            if package_obj.is_active == False:
                raise ValidationError({"amount": "This package is already expired"})
            if amount < (
                packagebooking.total_amount * MIN_BOOKING_PAYOUT_PERCENTAGE / 100
            ):
                raise ValidationError({"error": "you must pay 15% of total amount"})

            if amount > packagebooking.total_amount:
                raise ValidationError(
                    {"error": "cannot be paid more than the actual amount"}
                )

            serializer = PackageBookingSerializer(packagebooking)

            if float(amount) == float(packagebooking.total_amount):
                packagebooking.payment_status = "Paid"
            else:
                packagebooking.payment_status = "Partially Paid"

            if payment_method == "khalti":
                try:
                    packagebooking = PackageBooking.objects.get(id=packagebooking.id)
                    try:
                        payload = {
                            "token": token,
                            "amount": amount * 100,
                        }
                        headers = {
                            "Authorization": "Key {}".format(settings.KHALTI_SECRET_KEY)
                        }
                        response = requests.post(
                            settings.KHALTI_VERIFY_URL, payload, headers=headers
                        )
                        if response.status_code == 200:
                            packagebooking.khalti_payment_status = "success"
                            packagebooking.payment_method = payment_method
                            packagebooking.payment_status = "Paid"
                            packagebooking.paid_amount = amount
                            packagebooking.save()
                            KhaltiTransactionDetail.objects.create(
                                token=token,
                                payment_status="success",
                                packagebooking_id=packagebooking,
                                amount=amount,
                            )
                        else:
                            packagebooking.khalti_payment_status = "failure"
                            packagebooking.save()
                            KhaltiTransactionDetail.objects.create(
                                token=token,
                                payment_status="failure",
                                packagebooking_id=packagebooking,
                                amount=amount,
                            )
                            return Response({"status": 401, "detail": response.json()})

                    except requests.exceptions.HTTPError as e:
                        packagebooking.status = "failed verification"
                        packagebooking.save()
                        raise ValidationError(
                            {
                                "detail": "unable to send payment verification request to khalti",
                            }
                        )
                except PackageBooking.DoesNotExist:
                    raise ValidationError(
                        {"details": "Unable to verify payment.Booking not available."}
                    )

            elif payment_method == "e-sewa":
                packagebooking_esewa_verification(
                    token, amount, package_booking_id=packagebooking
                )
            else:
                pass
            packagebooking.payment_method = payment_method
            packagebooking.paid_amount = amount
            # saving the remaining amount to be paid
            packagebooking.remaining_amount = (
                float(packagebooking.total_amount) - packagebooking.paid_amount
            )
            packagebooking.save()

            calc = calculate_price(package_obj, quantity)
            packagebooking_serializer = PackageBookingSerializer(packagebooking)
            res = {"packagebooking_detail": packagebooking_serializer.data}
            res.update(calc)
            return Response(res, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="price")
    def get_pricing_detail(self, request):
        package = self.request.data.get("package_id")
        package_obj = get_object_or_404(Package, id=package, is_active=True)

        # check if package is inactive
        if package_obj.is_active == False:
            raise ValidationError({"error": "This package is already expired"})
        quantity = self.request.data.get("quantity")
        if package_obj and quantity:
            calc = calculate_price(package_obj, quantity)
            self.request.data.update({"package": package_obj})
            packagebooking_serializer = PackageBookingSerializer(self.request.data)
            self.validate_date(packagebooking_serializer)
            serializer_data = dict(packagebooking_serializer.data)
            serializer_data.update(calc)
            return Response(serializer_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Please provide the neccesary details"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PackageViewset(viewsets.ModelViewSet):
    """
    A viewset for creating,viewing and editing packages by admin.
    """

    serializer_class = PackageSerializer
    queryset = Package.objects.none()

    def get_serializer_context(self):
        if (
            self.request.method == "POST"
            or self.request.method == "PUT"
            or self.request.method == "PATCH"
        ):
            organisation_id = self.request.data.get("organisation_id")

            context = super().get_serializer_context()
            try:
                organisation = Organisation.objects.get(
                    id=organisation_id, user=self.request.user, is_deleted=False
                )
                # organisation = Organisation.objects.filter(user=self.request.user.id)
                if organisation:
                    context["organisation_obj"] = organisation
            except Organisation.DoesNotExist:
                raise ValidationError({"error": "Invalid Organisation"})
            return context

    def get_queryset(self):
        organisation = self.request.query_params.get("organisation")

        queryset = Package.objects.filter(
            organisation__user=self.request.user, is_deleted=False
        )
        queryset = queryset.annotate(
            available_quantity=F("quantity")
            - Coalesce(
                Sum(
                    "package_booking__quantity",
                    filter=Q(
                        ~Q(package_booking__payment_status="Draft"),
                        package_booking__is_deleted=False,
                        package_booking__cancelled=False,
                    ),
                ),
                0,
            )
        )

        if organisation:
            queryset = queryset.filter(
                organisation__id=int(organisation),
                is_deleted=False,
            )

        return queryset


class PackageTypeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PackageTypeSerializer

    def get_queryset(self):
        queryset = PackageType.objects.filter(is_deleted=False)
        return queryset


class PopularPackageListAPIView(ListAPIView):
    """
    CASE:
        1. If no search_key provided most booked package in the world
    """

    serializer_class = PackageSerializer

    def get_queryset(self):
        current = self.request.query_params.get("current")
        queryset = (
            Package.objects.filter(
                is_deleted=False,
                booking_start_date__lte=date.today(),
                booking_end_date__gte=date.today(),
            )
            .annotate(
                number_of_booked=Count(
                    "package_booking",
                    filter=Q(
                        package_booking__is_deleted=False,
                        package_booking__cancelled=False,
                    ),
                    output_field=IntegerField(),
                ),
            )
            .annotate(
                available_quantity=F("quantity")
                - Coalesce(
                    Sum(
                        "package_booking__quantity",
                        filter=Q(
                            package_booking__is_deleted=False,
                            package_booking__cancelled=False,
                        ),
                    ),
                    0,
                )
            )
            .filter(available_quantity__gt=0)
        )
        parent_search_key = self.request.query_params.get("parent_search_key")
        child_search_key = self.request.query_params.get("child_search_key")
        if parent_search_key:
            queryset = queryset.filter(
                Q(package_type__name__icontains=parent_search_key)
                | Q(organisation__location__city__icontains=parent_search_key)
                | Q(organisation__location__country__icontains=parent_search_key)
                | Q(organisation__location__continent__icontains=parent_search_key)
            )

        if child_search_key:
            queryset = queryset.filter(
                Q(package_type__name__icontains=child_search_key)
                | Q(organisation__location__city__icontains=child_search_key)
                | Q(organisation__location__country__icontains=child_search_key)
                | Q(organisation__location__continent__icontains=child_search_key)
            )
        if current:
            queryset = queryset.exclude(id=current)
        return queryset.order_by("-number_of_booked")


class PackageNameSuggestion(APIView):
    def get(self, request, *args, **kwargs):
        name = self.request.query_params.get("name", "")
        name_suggestions = []

        if name:
            packages = Package.objects.filter(
                is_deleted=False,
                booking_start_date__lte=date.today(),
                booking_end_date__gte=date.today(),
            ).values(
                "package_type__name",
                "title",
                "organisation__name",
                "organisation__location",
                "organisation__category__name",
            )

            for package in packages:
                organisation_location = package.get("organisation__location", {})
                if name.lower() in organisation_location.get("city", "").lower():
                    name_suggestions.append(organisation_location.get("city").title())
                if name.lower() in organisation_location.get("country", "").lower():
                    name_suggestions.append(
                        organisation_location.get("country").title()
                    )
                if name.lower() in organisation_location.get("street_name", "").lower():
                    name_suggestions.append(
                        organisation_location.get("street_name").title()
                    )
                if name.lower() in organisation_location.get("continent", "").lower():
                    name_suggestions.append(
                        organisation_location.get("continent").title()
                    )
                if name.lower() in package.get("organisation__name", "").lower():
                    name_suggestions.append(package.get("organisation__name").title())
                if name.lower() in package.get("package_type__name", "").lower():
                    name_suggestions.append(package.get("package_type__name").title())
                if name.lower() in package.get("title").lower():
                    name_suggestions.append(package.get("title").title())

                if name.lower() in package.get("organisation__category__name").lower():
                    name_suggestions.append(
                        package.get("organisation__category__name").title()
                    )

        res = {"suggestions": list(set(name_suggestions))}

        return Response(res)
