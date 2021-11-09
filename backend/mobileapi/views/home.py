from rest_framework.generics import ListAPIView
from mobileapi.serializers.organisation import (
    OrganisationListInfoSerializer,
    CountryPropertyAnnotateSerializer,
    ContinentPropertyAnnotateSerializer
)
from organisation.models import Organisation
from mobileapi.utils.helpers import get_country_flag
from backend.countries_list import countries
from common.models import BackgroundImage


class RecommendationPackageListView(ListAPIView):
    """
    listing the recommendation package in homepage
    """

    serializer_class = OrganisationListInfoSerializer
    queryset = Organisation.objects.filter(is_deleted=False)


class CountryPropertyCountView(ListAPIView):
    """
    listing out the country and no of properties the country have
    """

    serializer_class = CountryPropertyAnnotateSerializer

    def get_queryset(self):
        continent = self.request.query_params.get("continent")
        organisations = Organisation.objects.filter(is_deleted=False).values('location__country')
        if continent:
            organisations = organisations.filter(location__continent__icontains=continent)

        countries_list = [org.get("location__country").capitalize()
                          if org.get('location__country')
                          else "no_country"
                          for org in organisations]
        country_data = []
        for country in set(countries_list):
            background_image = BackgroundImage.objects.filter(name__icontains=country).first()
            context = {
                "no_of_property": organisations.filter(
                    location__country=country
                ).count(),
                "location": country,
                "flag_url": get_country_flag(country),
                "background_image": background_image.image_url if background_image else "https://img2.pngio.com/index-of-areaedu-wp-content-uploads-2016-02-default-png-600_600.png"
            }
            if continent:
                context.update({
                    "continent": continent.capitalize()
                })
            country_data.append(context)
        return country_data


class ContinentPropertyCountView(ListAPIView):
    """
    api view to list out the continent and number of property in the continent
    """
    serializer_class = ContinentPropertyAnnotateSerializer

    def get_queryset(self):
        organisations = Organisation.objects.filter(is_deleted=False, is_visible=True).values('location__continent')
        continent_list = [org.get("location__continent").lower()
                          if org.get('location__continent')
                          else "no_country"
                          for org in organisations]
        continent_data = []
        for continent in set(continent_list):
            background_image = BackgroundImage.objects.filter(name__icontains=continent).first()
            if continent != "no_country":
                context = {
                    "no_of_property": organisations.filter(
                        location__continent__icontains=continent
                    ).count(),
                    "continent": continent,
                    "flag_url": get_country_flag(continent),
                    "background_image": background_image.image_url if background_image else "https://img2.pngio.com/index-of-areaedu-wp-content-uploads-2016-02-default-png-600_600.png"
                }
                continent_data.append(context)
        return continent_data
