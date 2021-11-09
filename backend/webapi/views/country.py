from rest_framework.views import APIView
from rest_framework.response import Response
from webapi.serializers.country import CountrySerializer
from backend.countries_list import countries
from webapi.utils.helpers import get_client_ip, get_visitor_info


class CountryListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        countries_ = []
        for country in countries:
            countries_.append(
                {"country": country["name"], "short_code": country["alpha2_code"]}
            )
        serializer = CountrySerializer(countries_, many=True)
        return Response(serializer.data)


class GetCountryAPIView(APIView):
    """
    api view to get the country from the IP Address
    """

    def get(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        result = get_visitor_info(client_ip, request)
        return Response(result)
