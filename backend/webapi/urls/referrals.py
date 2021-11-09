from django.urls import path
from webapi.views.referrals import (
    ReferralsView,
    UserReferralsPointStatView,
    SecondaryUserReferralView,
)

urlpatterns = [
    path("referrals/", ReferralsView.as_view(), name="referrals"),
    path(
        "referrals_point_stat/",
        UserReferralsPointStatView.as_view(),
        name="referrals_point_stat",
    ),
    path(
        "secondary_referrals/",
        SecondaryUserReferralView.as_view(),
        name="secondary_referrals",
    ),
]
