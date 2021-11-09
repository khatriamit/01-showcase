from django.urls import path, include
from mobileapi.views.home import RecommendationPackageListView, CountryPropertyCountView, ContinentPropertyCountView


urlpatterns = [
    path('recommendation-package/', RecommendationPackageListView.as_view()),
    path('country-property/', CountryPropertyCountView.as_view()),
    path('continent-property/', ContinentPropertyCountView.as_view())
]
