from rest_framework import serializers


class CountrySerializer(serializers.Serializer):
    country = serializers.CharField(read_only=True)
    short_code = serializers.CharField(read_only=True)