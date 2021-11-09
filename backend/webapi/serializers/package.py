from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db.models import Sum, Q
from package.models import Package, PackageType, PackageBooking, PackageImage
from mobileapi.serializers.organisation import (
    OrganisationListInfoSerializer,
    OrganisationSerializer,
)
from users.serializers import UserSerializer
import datetime
from django.db import transaction
from organisation.models import Organisation
from datetime import date


class PackageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageType
        fields = ["id", "name", "color", "rate_depends_per_person"]


class PackageImageSerializer(serializers.ModelSerializer):
    id_ = serializers.IntegerField(allow_null=True, write_only=True)

    class Meta:
        read_only_fields = ["package"]
        model = PackageImage
        fields = ["id", "id_", "package", "image"]


class PackageSerializer(serializers.ModelSerializer):
    package_type_id = serializers.PrimaryKeyRelatedField(
        queryset=PackageType.objects.filter(is_deleted=False),
        source="package_type",
        write_only=True,
    )
    organisation_id = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.filter(is_deleted=False),
        source="organisation",
        write_only=True,
    )
    package_type = PackageTypeSerializer(read_only=True)
    organisation = OrganisationSerializer(read_only=True)
    number_of_days_nights = serializers.SerializerMethodField(read_only=True)
    property_review_count = serializers.IntegerField(read_only=True)
    price = serializers.FloatField()
    package_image = PackageImageSerializer(many=True)
    is_active = serializers.BooleanField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    number_of_booked = serializers.IntegerField(read_only=True)

    class Meta:
        model = Package
        fields = [
            "id",
            "package_type",
            "package_type_id",
            "organisation",
            "organisation_id",
            "title",
            "description",
            "booking_start_date",
            "booking_end_date",
            "number_of_days_nights",
            "number_of_nights",
            "number_of_days",
            "price",
            "quantity",
            "available_quantity",
            "property_review_count",
            "checkin_valid_start_date",
            "checkin_valid_end_date",
            "is_active",
            "package_image",
            "number_of_booked",
        ]

    def validate_booking_start_date(self, booking_start_date):
        """
        Check provided start date is not valid to past date
        """
        if not self.instance:
            today = date.today()
            if booking_start_date < today:
                raise serializers.ValidationError(
                    "Booking start date should not accept past date!"
                )
        return booking_start_date

    def validate_booking_end_date(self, booking_end_date):
        """
        Check provided start date is not valid to past date
        """
        if not self.instance:
            today = date.today()
            if booking_end_date < today:
                raise serializers.ValidationError(
                    "Booking end date should not accept past date"
                )
        return booking_end_date

    def validate(self, attrs):
        # check start date and end date should not be same
        if attrs["booking_start_date"] > attrs["booking_end_date"]:
            raise serializers.ValidationError(
                {"error": "Booking End date should be greater than Booking start date."}
            )
        # check valid start date and valid end date should not be same
        if attrs["checkin_valid_start_date"] > attrs["checkin_valid_end_date"]:
            raise serializers.ValidationError(
                {"error": "Valid end date should be greater than valid start date."}
            )
        if attrs["booking_end_date"] > attrs["checkin_valid_end_date"]:
            raise serializers.ValidationError(
                {"error": "Valid end date should not be greater than end  date."}
            )

        return attrs

    def validate_checkin_valid_start_date(self, checkin_valid_start_date):
        """
        Check provided valid start date is not valid to past date
        """
        if not self.instance:
            today = date.today()
            if checkin_valid_start_date < today:
                raise serializers.ValidationError(
                    "Checkin valid start date should not accept past date!"
                )
        return checkin_valid_start_date

    def validate_checkin_valid_end_date(self, checkin_valid_end_date):
        """
        Check provided valid end date is not valid to past date
        """
        today = date.today()
        if checkin_valid_end_date < today:
            raise serializers.ValidationError(
                "Checkin valid end date should not accept past date!"
            )
        return checkin_valid_end_date

    def validate_price(self, price):
        """
        check if the provided price has negative value
        """
        if price <= 0:
            raise serializers.ValidationError(
                "Price cannot be less than or equals to zero!"
            )
        return price

    def validate_number_of_nights(self, number_of_nights):
        """
        check if the provided price has negative value
        """
        if number_of_nights <= 0:
            raise serializers.ValidationError(
                "Number of Nights cannot be less than or equals to zero"
            )
        return number_of_nights

    def validate_number_of_days(self, number_of_days):
        """
        check if the provided price has negative value
        """
        if number_of_days <= 0:
            raise serializers.ValidationError(
                "Number of Days cannot be less than or equals to zero"
            )
        return number_of_days

    def validate_quantity(self, quantity):
        """
        check if the provided price has negative value
        """
        if quantity <= 0:
            raise serializers.ValidationError(
                "Quantity cannot be less than or equals to zero"
            )
        return quantity

    def validate_package_image(self, value):
        if len(value) == 0:
            raise ValidationError("this should not be empty")
        return value

    @transaction.atomic
    def create(self, validated_data):
        package_type_data = validated_data.pop("package_type")
        organisation_data = validated_data.pop("organisation")
        package_images = validated_data.pop("package_image")
        package = Package.objects.create(
            package_type=package_type_data,
            organisation=organisation_data,
            **validated_data,
        )
        if package_images:
            bulk_package_image = []
            for image in package_images:
                package_image = PackageImage(package=package, image=image.get("image"))
                bulk_package_image.append(package_image)
            PackageImage.objects.bulk_create(bulk_package_image)
        return package

    @transaction.atomic
    def update(self, instance, validated_data):
        package_images = validated_data.pop("package_image")
        bulk_image_update = []
        bulk_image_create = []
        if package_images:
            existing_package_images = []
            for image in package_images:
                if image.get("id_"):
                    existing_package_images.append(image.get("id_"))
                if image.get("id_"):
                    package_image = PackageImage(id=image.get("id_"))
                    package_image.image = image.get("image")
                    bulk_image_update.append(package_image)
                else:
                    package_image = PackageImage(
                        package=instance, image=image.get("image")
                    )
                    bulk_image_create.append(package_image)
            print(existing_package_images)
            package_images = (
                PackageImage.objects.filter(package=instance)
                .exclude(id__in=existing_package_images)
                .delete()
            )
            PackageImage.objects.bulk_create(bulk_image_create)
            PackageImage.objects.bulk_update(bulk_image_update, fields=["image"])
        return super(PackageSerializer, self).update(instance, validated_data)

    def get_number_of_days_nights(self, obj):
        return f"{obj.number_of_nights} Nights {obj.number_of_nights+1} Days"


class PackageBookingSerializer(serializers.ModelSerializer):
    # package_id = serializers.PrimaryKeyRelatedField(
    #     queryset=Package.objects.filter(is_deleted=False),
    #     write_only=True,
    # )
    # booking_id = serializers.CharField(read_only=True)
    packagebooking_id = serializers.UUIDField(read_only=True, source="uuid")
    package = PackageSerializer(read_only=True)
    booked_by = UserSerializer(read_only=True)
    total_amount = serializers.FloatField(required=False)
    paid_amount = serializers.FloatField(required=False)
    remaining_amount = serializers.FloatField(required=False)
    upcoming = serializers.BooleanField(read_only=True)
    completed = serializers.BooleanField(read_only=True)
    ongoing = serializers.BooleanField(read_only=True)

    class Meta:
        model = PackageBooking
        fields = [
            "id",
            "package",
            "packagebooking_id",
            # "package_id",
            "paid_amount",
            "remaining_amount",
            "total_amount",
            "payment_status",
            "booked_on",
            "booked_by",
            "user_info",
            "payment_method",
            # "khalti_payment_status",
            "quantity",
            "checkin_date",
            "upcoming",
            "completed",
            "ongoing",
            "cancelled",
            "created_on",
            "modified_on",
            "deleted_on",
            "is_deleted",
        ]

    def validate_checkin_date(self, value):
        if value < datetime.date.today():
            raise ValidationError("should not accept past dates")
        return value


class UpdatePackageBookingSerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    valid_checkin_start_date = serializers.DateField(read_only=True)
    valid_checkin_end_date = serializers.DateField(read_only=True)

    class Meta:
        model = PackageBooking
        fields = (
            "id",
            "checkin_date",
            "quantity",
            "available_quantity",
            "valid_checkin_start_date",
            "valid_checkin_end_date",
        )
