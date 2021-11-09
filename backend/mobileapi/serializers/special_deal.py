from rest_framework import serializers
from organisation.models import OrganisationSpecialDeal


class OrganisationSpecialDealSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    organisation_name = serializers.CharField(
        source="organisation.name", read_only=True
    )
    organisation_location = serializers.JSONField(
        source="organisation.location", read_only=True
    )
    organisation_photo_url = serializers.URLField(
        source="organisation.photo_url", read_only=True
    )
    organisation_category = serializers.CharField(
        source="organisation.category", read_only=True
    )
    upcoming = serializers.BooleanField(read_only=True)
    ongoing = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrganisationSpecialDeal
        fields = [
            "id",
            "organisation",
            "organisation_name",
            "organisation_location",
            "organisation_photo_url",
            "organisation_category",
            "name",
            "description",
            "from_date",
            "to_date",
            "category",
            "status",
            "breakfast_included",
            "discount_off",
            "discount_percentage",
            "discount_code",
            "upcoming",
            "ongoing",
            "created_on",
        ]
