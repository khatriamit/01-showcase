from booking.models import RatingByIndividual
from django.db.models import Avg
from rest_framework import serializers
from mobileapi.serializers.rating import RatingByIndividualSerializer
from mobileapi.utils.helpers import get_country_flag
from organisation.models import *


class RoomRelatedOrganisationSerializer(serializers.ModelSerializer):
    """
    listing the organisation based on room price
    """

    name = serializers.CharField(source="organisation.name", read_only=True)
    ratings = serializers.CharField(source="organisation.ratings", read_only=True)
    location = serializers.JSONField(source="organisation.location", read_only=True)

    class Meta:
        model = Room
        fields = ["id", "photo_url", "name", "ratings", "location", "price"]


class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = ("id", "image", "caption")


class RoomInfoSerializer(serializers.ModelSerializer):
    """
    listing out the rooms for the different listing section
    """

    room_image = RoomImageSerializer(read_only=True, many=True)

    class Meta:
        model = Room
        fields = [
            "id",
            "uuid",
            "modified_on",
            "created_on",
            "is_deleted",
            "deleted_on",
            "no_of_rooms",
            "room_numbers",
            "category",
            "photo_url",
            "price",
            "size",
            "description",
            "accomodates",
            "children_accomodate",
            "bathrooms",
            "amenities",
            "single_bed",
            "double_bed",
            "triple_bed",
            "organisation",
            "room_image",
        ]


class OrganisationImageSerializer(serializers.ModelSerializer):
    """
    listing the image gallery of the organisation
    """

    class Meta:
        model = OrganisationImage
        fields = ["image", "caption"]


class OrganisationSerializer(serializers.ModelSerializer):
    """
    organisation serializer
    """

    rating = RatingByIndividualSerializer(many=True, read_only=True)
    rooms = RoomInfoSerializer(many=True, read_only=True)
    organisation_images = OrganisationImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    favourite = serializers.BooleanField(read_only=True)
    user_rating = serializers.SerializerMethodField(read_only=True)
    user_review_count = serializers.SerializerMethodField(read_only=True)
    favourite = serializers.BooleanField(read_only=True)
    rating_location_average = serializers.IntegerField(read_only=True)
    rating_comfort_average = serializers.IntegerField(read_only=True)
    rating_personnel_average = serializers.IntegerField(read_only=True)
    rating_cleanliness_average = serializers.IntegerField(read_only=True)
    rating_good_offer_average = serializers.IntegerField(read_only=True)
    rating_service_average = serializers.IntegerField(read_only=True)

    def get_user_rating(self, obj):
        user_rating = obj.rating.filter(is_deleted=False).aggregate(Avg("rating_star"))
        return (
            user_rating.get("rating_star__avg")
            if user_rating.get("rating_star__avg")
            else 0
        )

    def get_user_review_count(self, obj):
        return obj.rating.filter(is_deleted=False).count()

    class Meta:
        model = Organisation
        fields = [
            "id",
            "name",
            "category_name",
            "location",
            "property_status",
            "size",
            "website",
            "photo_url",
            "recommended",
            "accessibility",
            "internet",
            "kitchen",
            "facilities",
            "safety",
            "description",
            "description_name",
            "house_rules",
            "is_accepted",
            "is_refundable",
            "join_membership",
            "membership_plan",
            "local_law",
            "checkin_time",
            "checkout_time",
            "views",
            "announcement",
            "user_rating",
            "user_review_count",
            "rating_location_average",
            "rating_comfort_average",
            "rating_personnel_average",
            "rating_cleanliness_average",
            "rating_good_offer_average",
            "rating_service_average",
            "rating",
            "rooms",
            "organisation_images",
            "favourite",
            "discount_code_prefix",
        ]


class OrganisationRoomSerializer(serializers.ModelSerializer):
    """
    organisation room serializer
    """

    class Meta:
        model = Room
        fields = "__all__"


class RatingStarFilterSerializer(serializers.Serializer):
    rating_star = serializers.IntegerField(read_only=True)
    rating_star_count = serializers.IntegerField(read_only=True)


class PropertyTypeFilterSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    property_type = serializers.CharField(read_only=True)
    property_type_count = serializers.IntegerField(read_only=True)


class FacilitiesFilterSerializer(serializers.Serializer):
    facility_name = serializers.CharField(read_only=True)
    facility_count = serializers.IntegerField(read_only=True)


class OrganisationListInfoSerializer(serializers.ModelSerializer):
    """
    listing out the organisation for the different organisation listing section
    """

    rooms = RoomInfoSerializer(many=True, read_only=True)
    category_name = serializers.CharField(read_only=True)
    category_color_code = serializers.CharField(source="category.color", read_only=True)
    user_rating = serializers.SerializerMethodField(read_only=True)
    user_review_count = serializers.SerializerMethodField(read_only=True)
    min_room_price = serializers.FloatField(read_only=True)
    flag_url = serializers.SerializerMethodField(read_only=True)
    favourite = serializers.BooleanField(read_only=True)
    number_of_booked = serializers.IntegerField(read_only=True)

    def get_flag_url(self, obj):
        try:
            return get_country_flag(obj.location.get("country"))
        except Exception as e:
            return get_country_flag(obj.get("location").get("country"))

    def get_user_rating(self, obj):
        try:
            user_rating = obj.rating.filter(is_deleted=False).aggregate(
                Avg("rating_star")
            )
        except Exception as e:
            user_rating = RatingByIndividual.objects.filter(
                rated_on__id=obj.get("id"), is_deleted=False
            ).aggregate(Avg("rating_star"))
        return (
            user_rating.get("rating_star__avg")
            if user_rating.get("rating_star__avg")
            else 0
        )

    def get_user_review_count(self, obj):
        try:
            return obj.rating.filter(is_deleted=False).count()
        except Exception as e:
            return RatingByIndividual.objects.filter(
                rated_on__id=obj.get("id"), is_deleted=False
            ).count()

    class Meta:
        model = Organisation
        fields = [
            "id",
            "name",
            "category_name",
            "photo_url",
            "location",
            "category_color_code",
            "user_rating",
            "user_review_count",
            "min_room_price",
            "rooms",
            "flag_url",
            "is_visible",
            "favourite",
            "number_of_booked",
            "discount_code_prefix",
        ]


class OrganisationListFilterInfoSerilizer(serializers.Serializer):
    organisations = OrganisationListInfoSerializer()
    rating_filter_count = RatingStarFilterSerializer(read_only=True, many=True)
    property_type_filter_count = PropertyTypeFilterSerializer(read_only=True, many=True)
    facilities_filter_count = FacilitiesFilterSerializer(read_only=True, many=True)
    min_room_price = serializers.FloatField(read_only=True)
    max_room_price = serializers.FloatField(read_only=True)


class CountryPropertyAnnotateSerializer(serializers.ModelSerializer):
    """
    listing out the country property count
    """

    no_of_property = serializers.IntegerField(read_only=True)
    flag_url = serializers.URLField(read_only=True)
    continent = serializers.CharField(read_only=True)
    background_image = serializers.URLField(read_only=True)

    class Meta:
        model = Organisation
        fields = [
            "location",
            "no_of_property",
            "flag_url",
            "continent",
            "background_image",
        ]


class ContinentPropertyAnnotateSerializer(serializers.ModelSerializer):
    """
    listing out the country property count
    """

    no_of_property = serializers.IntegerField(read_only=True)
    continent = serializers.CharField(read_only=True)
    background_image = serializers.URLField(read_only=True)

    class Meta:
        model = Organisation
        fields = ["continent", "no_of_property", "background_image"]


class UserOrganisationFavouriteSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.id", read_only=True)

    class Meta:
        model = UserOrganisationFavorites
        fields = ("id", "organisation", "user")


class OrganisationFetchRoomNumberSerializer(serializers.ModelSerializer):
    """
    serializer to fetch the room number from the organisation
    """

    class Meta:
        model = Room
        fields = [
            "id",
            "category",
            "room_numbers",
            "organisation",
            "no_of_rooms",
        ]
