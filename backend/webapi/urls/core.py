from django.urls import path
from .package import urlpatterns as package_urls
from .country import urlpatterns as country_urls
from .organisation import urlpatterns as organisation_urls
from .referrals import urlpatterns as referrals_urls
from .booking import urlpatterns as booking_urls
from .admin_booking import urlpatterns as admin_booking_urls
from .admin_package_booking import urlpatterns as admin_package_booking_urls
from webapi.views.available_rooms import GetAvailableRoomNumbers
from .update_package_booking import urlpatterns as package_booking_update_urls
from .organisation_room import urlpatterns as organisation_room_urls

room_numbers_url = [path("available_room_numbers/", GetAvailableRoomNumbers.as_view())]

urlpatterns = (
    package_urls
    + country_urls
    + organisation_urls
    + referrals_urls
    + room_numbers_url
    + booking_urls
    + admin_booking_urls
    + admin_package_booking_urls
    + package_booking_update_urls
    + organisation_room_urls
)
