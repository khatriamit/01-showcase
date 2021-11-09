from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.sites.shortcuts import get_current_site


User = get_user_model()


class UserInfoSerializer(serializers.ModelSerializer):
    """
    organisation serializer
    """

    # display_name = serializers.SerializerMethodField('get_full_name', read_only=True)
    #
    # def get_full_name(self, obj):
    #     if obj.first_name and obj.last_name:
    #         return f"{obj.first_name} {obj.last_name}"
    #     return ""
    referral_link = serializers.SerializerMethodField(read_only=True)

    def get_referral_link(self, obj):
        context = self.context
        # current_site = get_current_site(context.get("request"))
        # current_site = ("http://" if "http" not in str(current_site) else "") + str(
        #     current_site
        # )
        return (
            "https://stg.backend.com.au"
            + f"/signup/?referral_code={obj.referral_code}"
        )

    class Meta:
        model = User
        fields = [
            "pk",
            "email",
            "mobile",
            "first_name",
            "last_name",
            "display_name",
            "is_active",
            "referral_code",
            "referral_link",
            "profile_picture",
            "gender",
            "dob",
            "nationality",
            "user_membership",
            "push_notification",
            "facebook",
            "twitter",
            "instagram",
            "address",
            "postal_code",
            "country",
            "country_code",
            "city",
        ]
