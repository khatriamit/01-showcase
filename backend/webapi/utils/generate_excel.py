import os
import uuid
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import pandas as pd


def to_excel_auto_width(filename, df):
    writer = pd.ExcelWriter(filename, engine="xlsxwriter")
    df.to_excel(writer, index=False)  # send df to writer
    worksheet = writer.sheets["Sheet1"]  # pull worksheet object
    for idx, col in enumerate(df):  # loop through all columns
        series = df[col]
        max_len = (
            max(
                (
                    series.astype(str).map(len).max(),  # len of largest item
                    len(str(series.name)),  # len of column name/header
                )
            )
            + 2
        )  # adding a little extra space
        max_len = 20 if max_len != max_len else max_len
        worksheet.set_column(idx, idx, max_len)  # set column width
    writer.save()


def save_file(df, directory, filename):
    if not os.path.exists("media/" + directory):
        os.makedirs("media/" + directory)
    file_path = "media/" + directory + filename
    to_excel_auto_width(file_path, df)
    with open("media/" + directory + filename, "rb") as fin:
        buffer_file = BytesIO(fin.read())
        buffer_file.seek(0)
        path = default_storage.save(
            directory + filename,
            ContentFile(buffer_file.getvalue()),
        )
        buffer_file.close()
    os.remove("media/" + directory + filename)
    if hasattr(settings, "AWS_STORAGE_BUCKET_NAME"):
        path = "https://{}.s3.amazonaws.com/media/exports/{}".format(
            settings.AWS_STORAGE_BUCKET_NAME, filename
        )
    return path


def save_file1(df, directory, filename):
    # if not os.path.exists("media/" + directory):
    #     os.makedirs("media/" + directory)
    # file_path = "media/" + directory + filename
    # to_excel_auto_width(file_path, df)
    # with open("media/" + directory + filename, "rb") as fin:
    # csv_buffer = BytesIO()
    # df.to_excel(csv_buffer)
    # buffer_file = BytesIO(csv_buffer.read())
    # print(buffer_file)
    # path = default_storage.save(
    #     directory + filename,
    #     ContentFile(buffer_file.getvalue()),
    # )
    # buffer_file.close()
    # os.remove("media/" + directory + filename)
    print(filename)
    with BytesIO() as b:
        # Use the StringIO object as the filehandle.
        writer = pd.ExcelWriter(b, engine="xlsxwriter")
        df.to_excel(writer, sheet_name="Sheet1", index=False)
        writer.save()
        # Set up the Http response.
        path = default_storage.save(
            directory + filename,
            ContentFile(b.getvalue()),
        )
    if hasattr(settings, "AWS_STORAGE_BUCKET_NAME"):
        path = "https://{}.s3.amazonaws.com/media/exports/{}".format(
            settings.AWS_STORAGE_BUCKET_NAME, filename
        )
    return path


def get_media_file_from_data_frame(df: pd.DataFrame, filename):
    filename = filename + ".xlsx"
    url = save_file1(df, "exports/", filename)
    if url:
        return url
    return None
