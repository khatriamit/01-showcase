from django.db.models import Q
from booking.models import BookingDetail
from organisation.models import OrganisationRoomUnavailability
from booking.helpers import get_dates


def get_booked_rooms(checkin_date, checkout_date, instance=None):
    booked_rooms = BookingDetail.objects.filter(
        ~Q(booking__payment_status="Draft"),
        Q(
            booking__checkin_date__gte=checkin_date,
            booking__checkout_date__lte=checkout_date,
        )
        | Q(
            booking__checkin_date__lte=checkin_date,
            booking__checkout_date__gte=checkin_date,
        )
        | Q(
            booking__checkin_date__lte=checkout_date,
            booking__checkout_date__gte=checkout_date,
        ),
        booking__property=instance.property,
        booking__is_deleted=False,
        booking__cancelled=False,
    ).values("id", "room__id", "no_of_rooms")

    if instance:
        booked_rooms = booked_rooms.filter(~Q(booking=instance))
    return booked_rooms


def get_room_unavailability(checkin_date, checkout_date, booking):
    booking_unavailability = OrganisationRoomUnavailability.objects.filter(
        Q(from_date__gte=checkin_date, to_date__lte=checkout_date)
        | Q(from_date__lte=checkin_date, to_date__gte=checkin_date)
        | Q(from_date__lte=checkout_date, to_date__gte=checkout_date),
        organisation=booking.property,
        is_deleted=False,
    ).values("id", "room_type", "room_numbers")
    return booking_unavailability


def get_detail_booking_pricing(booking_price_info, booking):
    for info1 in booking_price_info.get("more_info"):
        for info2 in booking_price_info.get("fees_tax"):
            if info2.get("room_category") == info1.get("room_type"):
                info1.update(
                    {
                        "children_count": info2.get("children_count"),
                        "adult_count": info2.get("adult_count"),
                    }
                )
    booking_price_info.pop("fees_tax")
    if booking.discount_code:
        dates = get_dates(
            booking.discount_code.from_date, booking.discount_code.to_date
        )
        new_price_info = []
        for info in booking_price_info.get("more_info"):
            discount_not_applicable_dates = set(info.get("date")) - set(dates)
            discount_applicable_dates = set(info.get("date")).intersection(set(dates))
            # getting the discount price in each dates
            if discount_applicable_dates:
                new_price_info.append(
                    {
                        "room": info.get("room"),
                        "date": sorted(list(discount_applicable_dates)),
                        "room_type": info.get("room_type"),
                        "number_of_nights": len(discount_applicable_dates),
                        "rate": info.get("rate"),
                        "quantity": 1,
                        "total": len(discount_applicable_dates) * info.get("rate"),
                        "discount_amount": float(
                            booking.discount_code.discount_percentage / 100
                        )
                        * float(info.get("rate"))
                        * len(discount_applicable_dates),
                    }
                )
            if discount_not_applicable_dates:
                new_price_info.append(
                    {
                        "room": info.get("room"),
                        "date": discount_not_applicable_dates,
                        "room_type": info.get("room_type"),
                        "number_of_nights": len(discount_not_applicable_dates),
                        "rate": info.get("rate"),
                        "quantity": 1,
                        "total": len(discount_not_applicable_dates) * info.get("rate"),
                        "discount_amount": 0,
                    }
                )
        booking_price_info["more_info"] = new_price_info
    else:
        for info in booking_price_info.get("more_info"):
            info.update({"discount_amount": 0})
    return booking_price_info
