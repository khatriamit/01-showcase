from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.db.models import Min
from datetime import datetime
from organisation.models import Organisation, OrganisationRoomPricing, Room
from rest_framework.views import APIView
from booking.helpers import get_dates
import pandas as pd


class OrganisationCalendarPricingAPIView(APIView):
    def get(self, request, *args, **kwargs):
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        organisation = self.request.query_params.get("organisation")
        get_object_or_404(Organisation, id=organisation, is_deleted=False)
        dates = get_dates(from_date, to_date)
        organisation_pricings = OrganisationRoomPricing.objects.filter(
            from_date__gte=from_date, to_date__lte=to_date, organisation__id=organisation, is_deleted=False
        ).values("room_type", "price", "from_date", "to_date")
        min_room_price = Room.objects.filter(organisation__id=organisation).aggregate(
            Min("price")
        )
        date_pricing = list()
        # get the organisation price on the given date range of from and to_date
        # if pricing is set, then take the minimum price from Single, Double, Deluxe room category

        for date in dates:
            if organisation_pricings:
                for organisation_pricing in organisation_pricings:
                    if date in get_dates(
                        organisation_pricing.get("from_date"),
                        organisation_pricing.get("to_date"),
                    ):
                        date_pricing.append(
                            {"date": date, "price": organisation_pricing.get("price")}
                        )
                    else:
                        date_pricing.append(
                            {
                                "date": date,
                                "price": min_room_price.get("price__min")
                                if min_room_price.get("price__min")
                                else 0,
                            }
                        )
            else:
                date_pricing.append(
                    {
                        "date": date,
                        "price": min_room_price.get("price__min")
                        if min_room_price.get("price__min")
                        else 0,
                    }
                )
        updated_date_pricing_df = pd.DataFrame(date_pricing)
        res = []
        if not updated_date_pricing_df.empty:
            min_price = updated_date_pricing_df.groupby("date", as_index=False).agg(
                {"price": ["min"]}
            )
            min_price_dict = min_price.to_dict("list")
            dates = list(min_price_dict.values())[0]
            prices = list(min_price_dict.values())[1]
            res = [{k.strftime("%Y-%m-%d"): v} for k, v in zip(dates, prices)]
        return Response(res)
