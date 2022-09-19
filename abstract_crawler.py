import os
import re
from pathlib import Path

import cv2
import requests
import urllib3
from google.cloud import storage

from abstract_event import AbstractEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_site(logger, results_path, url, file_name, clean, quiet):
    """
    Download a website into a given file
    :param logger:
    :param results_path:
    :param url:
    :param file_name:
    :param clean:
    :param quiet:
    :return:
    """

    # Define file path
    file_path = os.path.join(results_path, file_name)

    # Check if result needs to be generated
    if clean or not os.path.exists(file_path):

        download_file(
            logger=logger,
            file_path=file_path,
            url=url
        )

        if not quiet:
            logger.log_line(f"✓ Download {file_path}")
    else:
        logger.log_line(f"✓ Already exists {file_path}")


def download_file(logger, file_path, url):
    """
    Downloads value of a given URL into a file
    :param logger:
    :param file_path:
    :param url:
    :return:
    """
    try:
        data = requests.get(url, verify=False)
        with open(file_path, 'wb') as file:
            file.write(data.content)
    except Exception as e:
        logger.log_line(f"✗️ Exception: {str(e)}")
        return None


def well_form(value):
    """
    Well-form html value
    :param value: value
    :return:
    """

    value = re.sub(r'<br(.*?)>', "", value)
    value = re.sub(r'<img(.*?)/*>', r'<img \1></img>', value)
    value = re.sub(r'&hellip;', "", value)
    value = re.sub(r'<input(.*?)>', "", value)
    value = re.sub(r'<meta(.*?)>', "", value)
    value = re.sub(r'data-drupal-messages-fallback', "", value)
    value = re.sub(r'xml:lang="EN-US"', "", value)
    value = re.sub(r'&nbsp;–', "", value)
    value = re.sub(r'&copy;', "", value)
    value = re.sub(r'&nbsp;', "", value)
    value = re.sub(r'<hr>', "", value)
    value = re.sub(r'&', "", value)

    value = re.sub(r'<script(.*?)/script>', "", value)
    value = re.sub(r'download>', ">", value)
    value = re.sub(r'<\?xml version="1.0" encoding="UTF-8"\?>', "", value)

    return value


def format_date(date):
    date_parts = date.split(" ")

    year = date_parts[3]
    month = format_month(date_parts[2])
    day = format_day(date_parts[1].replace(".", ""))

    return f"{year}-{month}-{day}"


def format_date_split(year, month, day):
    return f"{year}-{format_month(month)}-{day}"


def format_date_time(date, time):
    date_parts = date.split(" ")
    time_parts = time.split(".")

    year = date_parts[3]
    month = format_month(date_parts[2])
    day = format_day(date_parts[1].replace(".", ""))
    hours = time_parts[0]
    minutes = time_parts[1]

    return f"{year}-{month}-{day}T{hours}:{minutes}:00.000"


def format_date_times(date_time):
    date_time = re.sub(' +', ' ', date_time)
    date_time_parts = date_time.strip().split(" ")
    time_parts = date_time_parts[4].split(".")

    year = date_time_parts[3].replace(",", "")
    month = format_month(date_time_parts[2])
    day = format_day(date_time_parts[1].replace(".", ""))
    hours = time_parts[0]
    minutes = time_parts[1]

    return f"{year}-{month}-{day}T{hours}:{minutes}:00.000"


def format_date_time_start(year, month, day, time, delimiter=":"):
    time_parts = time.replace("Uhr", "").split("-")

    start_time = time_parts[0].strip()
    start_time_parts = start_time.split(delimiter)
    hours = start_time_parts[0].strip()
    minutes = start_time_parts[1].strip()

    return f"{year}-{format_month(month)}-{day}T{hours}:{minutes}:00.000"


def format_date_time_end(year, month, day, time, delimiter=":"):
    time_parts = time.replace("Uhr", "").split("-")

    if len(time_parts) == 2:
        # There is an actual end time
        end_time = time_parts[1].strip()
    else:
        # As a fallback use start time
        end_time = time_parts[0].strip()

    end_time_parts = end_time.split(delimiter)
    hours = end_time_parts[0].strip()
    minutes = end_time_parts[1].strip()

    return f"{year}-{format_month(month)}-{day}T{hours}:{minutes}:00.000"


def format_month(month):
    if month == "Januar" or month == "Jan":
        return "01"
    if month == "Februar" or month == "Feb":
        return "02"
    if month == "März" or month == "Mär":
        return "03"
    if month == "April" or month == "Apr":
        return "04"
    if month == "Mai" or month == "Mai":
        return "05"
    if month == "Juni" or month == "Jun":
        return "06"
    if month == "Juli" or month == "Jul":
        return "07"
    if month == "August" or month == "Aug":
        return "08"
    if month == "September" or month == "Sep":
        return "09"
    if month == "Oktober" or month == "Okt":
        return "10"
    if month == "November" or month == "Nov":
        return "11"
    if month == "Dezember" or month == "Dez":
        return "12"


def format_day(day: str):
    if int(day) < 10:
        return f"0{int(day)}"
    else:
        return f"{int(day)}"


def generate_content(logger, content_path, event: AbstractEvent):
    file_name = f"{event.identifier}.md"
    file_path = os.path.join(content_path, file_name)

    updated = False

    values = {}
    values_contact = {}
    values_location = {}

    languages = []

    if os.path.exists(file_path):

        # Read existing file
        with open(file_path, 'r') as file:
            for line in file.readlines():
                if "=" in line:
                    key = line.split("=")[0].strip().replace("\"", "").replace("'", "")
                    value = "=".join(line.split("=")[1:]).strip().replace("\"", "").replace("'", "").replace("amp;",
                                                                                                             "&")
                    value = str(value)

                    if key == "contact_person" or key == "contact_phone" or key == "contact_mail":
                        values_contact[key] = value
                    elif key == "location_street" or key == "location_city":
                        values_location[key] = value
                    elif key == "languages":
                        languages_list = value
                        languages_list = re.sub(r'^\'', "", languages_list)
                        languages_list = re.sub(r'\'$', "", languages_list)
                        languages_list = re.sub(r'\[', "", languages_list)
                        languages_list = re.sub(r']', "", languages_list)
                        if len(languages_list) > 0:
                            languages = languages_list.split(",")
                        pass
                    else:
                        values[key] = value

    # Update values
    if needs_update("identifier", event.identifier, values):
        values["identifier"] = event.identifier
        updated = True
    if needs_update("source", event.source, values):
        values["source"] = event.source
        updated = True
    if needs_update("url", event.url, values):
        values["url"] = event.url
        updated = True
    if needs_update("type", event.type, values):
        values["type"] = event.type
        updated = True
    if needs_update("title", event.title, values):
        values["title"] = event.title
        updated = True
    if needs_update("subtitle", event.subtitle, values):
        values["subtitle"] = event.subtitle
        updated = True
    if needs_update("description", event.description, values):
        values["description"] = event.description
        updated = True
    if needs_update("image", event.image, values):
        values["image"] = event.image
        updated = True
    if needs_update("image_bucket", event.image_bucket, values):
        values["image_bucket"] = event.image_bucket
        updated = True
    if needs_update("start_date", event.start_date, values):
        values["start_date"] = event.start_date
        updated = True
    if needs_update("end_date", event.end_date, values):
        values["end_date"] = event.end_date
        updated = True
    if needs_update("category", event.category, values):
        values["category"] = event.category
        updated = True
    if needs_update("organizer", event.organizer, values):
        values["organizer"] = event.organizer
        updated = True
    if needs_update("fees", event.fees, values):
        values["fees"] = event.fees
        updated = True

    if len(event.languages) > 0:
        for language in event.languages:
            languages.append(language)
            languages = list(dict.fromkeys(languages))

    if needs_update("contact_person", event.contact_person, values):
        values_contact["contact_person"] = event.contact_person
        updated = True
    if needs_update("contact_phone", event.contact_phone, values):
        values_contact["contact_phone"] = event.contact_phone
        updated = True
    if needs_update("contact_mail", event.contact_mail, values):
        values_contact["contact_mail"] = event.contact_mail
        updated = True

    if needs_update("location_street", event.location_street, values):
        values_contact["location_street"] = event.location_street
        updated = True
    if needs_update("location_city", event.location_city, values):
        values_contact["location_city"] = event.location_city
        updated = True

    if len(event.updated) > 0 and updated:
        values["updated"] = event.updated

    # Assemble content
    content = "+++"
    for key, value in values.items():
        content += f"\n{key} = \"{value}\""

    content += f"\nlanguages = ["
    for language in languages:
        if len(language) > 0:
            content += f"\"{language.replace('_', ' ')}\","
    content += "]"

    content += "\n[contact]"
    for key, value in values_contact.items():
        content += f"\n{key} = \"{value}\""

    content += "\n[location]"
    for key, value in values_location.items():
        content += f"\n{key} = \"{value}\""

    content += "\n+++"

    # Clean up
    content = content.replace(",]", "]").replace("amp;", "&")

    with open(file_path, 'w') as file:
        logger.log_line(f"✓ Generate {file_name}")
        file.write(content)


def generate_image(logger, workspace_path, upload_path, event: AbstractEvent, target_width=480):
    if event.image != "":
        # Download original image
        original_file_name = event.image
        original_file_name = re.sub(r'\?.*', '', original_file_name)
        original_file_name = re.sub(r'.*/', '', original_file_name)
        original_file_path = os.path.join(workspace_path, "images", original_file_name)
        os.makedirs(os.path.join(os.path.join(workspace_path, "images")), exist_ok=True)
        download_file(logger, original_file_path, event.image)

        # Resize image
        original_img = cv2.imread(original_file_path, cv2.IMREAD_UNCHANGED)
        original_width = int(original_img.shape[1])
        original_height = int(original_img.shape[0])
        ratio = original_height / original_width

        target_file_name = f"{event.identifier}.webp"
        target_file_path = os.path.join(upload_path, target_file_name)
        target_img = cv2.resize(original_img, (target_width, int(target_width * ratio)))
        cv2.imwrite(target_file_path, target_img)


def needs_update(name, value, values):
    return value is not None and len(value) > 0 and (name not in values or name in values and value != values[name])


def upload_file(logger, gcp_token_file, upload_file_path, project_id, bucket_name, quiet=False):
    """
    See https://cloud.google.com/storage/docs/creating-buckets#storage-create-bucket-python
    """

    # Set script path
    file_path = os.path.realpath(__file__)
    script_path = os.path.dirname(file_path)
    config_file_path = os.path.join(script_path, gcp_token_file)

    # Check for config file
    if not Path(config_file_path).exists():
        logger.log_line(f"✗️ Google Cloud config not found {config_file_path}")
        return

    # Define storage client
    client = storage.Client.from_service_account_json(
        config_file_path, project=project_id
    )

    bucket = client.bucket(bucket_name=bucket_name)
    bucket.storage_class = "STANDARD"

    blob = bucket.blob(os.path.basename(upload_file_path))
    blob.upload_from_filename(upload_file_path)

    if not quiet:
        logger.log_line(f"✓️ Uploading {os.path.basename(upload_file_path)}")


class AbstractCrawler:

    def run(self, logger, workspace_path, content_path, uploads_path, clean=False, quiet=False):
        """
        Runs crawler
        :param logger:
        :param workspace_path:
        :param content_path:
        :param uploads_path:
        :param clean:
        :param quiet:
        :return:
        """
        # Make workspace path
        os.makedirs(os.path.join(workspace_path), exist_ok=True)

        # Make results paths
        os.makedirs(os.path.join(content_path), exist_ok=True)
        os.makedirs(os.path.join(uploads_path), exist_ok=True)
