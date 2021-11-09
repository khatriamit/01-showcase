import django_filters
from organisation.models import OrganisationRoomUnavailability, OrganisationRoomPricing


class RoomUnavailabilityFilter(django_filters.FilterSet):
    from_date = django_filters.DateFilter(lookup_expr="gte")
    to_date = django_filters.DateFilter(lookup_expr="lte")
    room_type = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = OrganisationRoomUnavailability
        fields = ['organisation', 'room_type', 'from_date', 'to_date']


class RoomPricingFilter(django_filters.FilterSet):
    from_date = django_filters.DateFilter(lookup_expr="gte")
    to_date = django_filters.DateFilter(lookup_expr="lte")
    room_type = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = OrganisationRoomPricing
        fields = ['organisation', 'room_type', 'from_date', 'to_date']