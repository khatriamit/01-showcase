from django.urls import path
from django.urls.conf import include
from webapi.views.admin_bookings import (
    OwnerUpcomingOrganisationBooking,
    OwnerOngoingOrganisationBooking,
    OwnerCompletedOrganisationBooking,
    OwnerCancelledOrganisationBooking,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("organisation-upcoming-booking", OwnerUpcomingOrganisationBooking)
router.register("organisation-ongoing-booking", OwnerOngoingOrganisationBooking)
router.register("organisation-completed-booking", OwnerCompletedOrganisationBooking)
router.register("organisation-cancelled-booking", OwnerCancelledOrganisationBooking)


urlpatterns = [path("owner/", include(router.urls))]
