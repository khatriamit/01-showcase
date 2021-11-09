from .organisation import urlpatterns as organisation_urls
from .booking import urlpatterns as booking_urls
from .user import urlpatterns as user_urls
from .home import urlpatterns as home_urls
from .special_deal import urlpatterns as special_deal_urls
from .unavailability import urlpatterns as unavailability_urls
from .pricing import urlpatterns as pricing_urls
from .booking_search import urlpatterns as booking_search_urls
from .dashboard import urlpatterns as dashboard_urls

urlpatterns = organisation_urls + booking_urls + user_urls + home_urls + special_deal_urls + unavailability_urls + pricing_urls + booking_search_urls + dashboard_urls