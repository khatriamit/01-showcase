from django.urls import path
from webapi.views.update_package_booking import (
    UpdatePackageBookingUserInfo,
    UpdatePackageBookingDetail,
    GetPackageBookingPriceDetail,
)

urlpatterns = [
    path(
        "update-package-booking/user-info/<id>/",
        UpdatePackageBookingUserInfo.as_view(),
    ),
    path(
        "update-package-booking/detail/<id>/",
        UpdatePackageBookingDetail.as_view(),
    ),
    path(
        "update-package-booking/pricing-detail/<id>/",
        GetPackageBookingPriceDetail.as_view(),
    ),
]
