import pandas as pd
from django.db.models import ExpressionWrapper, DurationField, F
from .generate_excel import get_media_file_from_data_frame


def booking_export(queryset, filename):
    columns = [
        "Name",
        "Phone",
        "Booking ID",
        "Checkin At",
        "Checkout At",
        "Nights",
        "Room Type",
        "Guest",
        "Paid",
        "Cost",
    ]
    db_columns = [
        "user_info__name",
        "user_info__mobile_number",
        "uuid",
        "checkin_date",
        "checkout_date",
        "nights",
        "room_type",
        "guests",
        "paid_amount",
        "total_amount",
    ]
    queryset = queryset.annotate(
        nights=ExpressionWrapper(
            F("checkout_date") - F("checkin_date"), output_field=DurationField()
        ),
        guests=F("room_detail__no_of_children") + F("room_detail__no_of_adults"),
        room_type=F("room_detail__room__category"),
    ).values_list(*db_columns)
    df = pd.DataFrame.from_records(queryset, columns=columns)
    df = df.groupby("Booking ID", as_index=False).agg(
        {
            "Name": "first",
            "Phone": "first",
            "Booking ID": "first",
            "Checkin At": "first",
            "Checkout At": "first",
            "Nights": "first",
            "Room Type": ", ".join,
            "Guest": "first",
            "Paid": "first",
            "Cost": "first",
        }
    )
    return get_media_file_from_data_frame(df, filename)


def package_booking_export(queryset, filename):
    columns = [
        "Name",
        "Booking ID",
        "Checkin At",
        "Checkout At",
        "Nights",
        "Package Type",
        "Quantity",
        "Paid",
        "Cost",
    ]
    db_columns = [
        "user_info__name",
        "uuid",
        "checkin_date",
        "package__checkin_valid_end_date",
        "package__number_of_nights",
        "package__package_type__name",
        "quantity",
        "paid_amount",
        "total_amount",
    ]
    queryset = queryset.values_list(*db_columns)
    df = pd.DataFrame.from_records(queryset, columns=columns)
    df = df.groupby("Booking ID", as_index=False).agg(
        {
            "Name": "first",
            "Booking ID": "first",
            "Checkin At": "first",
            "Checkout At": "first",
            "Nights": "first",
            "Package Type": ", ".join,
            "Quantity": "first",
            "Paid": "first",
            "Cost": "first",
        }
    )

    return get_media_file_from_data_frame(df, filename)


def checkin_export(queryset, filename):
    columns = [
        "Name",
        "Phone",
        "Booking ID",
        "Checkin At",
        "Nights",
        "Room Type",
        "Guest",
        "Paid",
        "Cost",
    ]
    db_columns = [
        "user_info__name",
        "user_info__mobile_number",
        "uuid",
        "checkin_date",
        "nights",
        "room_type",
        "guests",
        "paid_amount",
        "total_amount",
    ]
    queryset = queryset.annotate(
        nights=ExpressionWrapper(
            F("checkout_date") - F("checkin_date"), output_field=DurationField()
        ),
        guests=F("room_detail__no_of_children") + F("room_detail__no_of_adults"),
        room_type=F("room_detail__room__category"),
    ).values_list(*db_columns)
    df = pd.DataFrame.from_records(queryset, columns=columns)
    df = df.groupby("Booking ID", as_index=False).agg(
        {
            "Name": "first",
            "Phone": "first",
            "Booking ID": "first",
            "Checkin At": "first",
            "Nights": "first",
            "Room Type": ", ".join,
            "Guest": "first",
            "Paid": "first",
            "Cost": "first",
        }
    )
    return get_media_file_from_data_frame(df, filename)
