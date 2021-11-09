from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mobileapi.viewsets.special_deal import OrganisationSpecialDealViewset


router = DefaultRouter()
router.register('organisation-special-deal', OrganisationSpecialDealViewset)

urlpatterns = [
    path('', include(router.urls))
]