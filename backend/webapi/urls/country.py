from django.urls import path
from webapi.views.country import CountryListAPIView, GetCountryAPIView

urlpatterns = [
    path("countries/", CountryListAPIView.as_view()),
    path("get_country/", GetCountryAPIView.as_view(), name="get_country"),
]
