
import django_filters
from package.models import Package


class PackageFilterSet(django_filters.FilterSet):
    start_date = django_filters.DateFilter(lookup_expr="gte")
    end_date = django_filters.DateFilter(lookup_expr="lte")

    class Meta:
        model = Package
        fields = [
            'organisation',
            'start_date',
            'end_date',
            'price'
        ]