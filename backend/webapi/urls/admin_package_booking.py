from django.urls import path
from django.urls.conf import include
from webapi.views.admin_package_bookings import (
    OwnerCancelledPackageBooking,
    OwnerOngoingPackageBooking,
    OwnerCompletedPackageBooking,
    OwnerUpcomingPackageBooking,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("package-upcoming-booking", OwnerUpcomingPackageBooking)
router.register("package-ongoing-booking", OwnerOngoingPackageBooking)
router.register("package-completed-booking", OwnerCompletedPackageBooking)
router.register("package-cancelled-booking", OwnerCancelledPackageBooking)


urlpatterns = [path("owner/", include(router.urls))]
