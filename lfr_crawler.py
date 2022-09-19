import os
import re
import xml.etree.ElementTree as element_tree
from typing import List

import urllib3

from abstract_crawler import AbstractCrawler, download_site, well_form, format_date_split, format_date_time_start, \
    format_date_time_end, generate_content, generate_image
from abstract_event import AbstractEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LfrEvent(AbstractEvent):
    """
    Represents an event posted on https://www.landesfrauenrat-berlin.de/veranstaltungen-in-berlin/
    """

    def __init__(self, identifier, url, title, subtitle, description, image, image_bucket, start_date, end_date,
                 category, languages, organizer, fees, contact_person, contact_phone, contact_mail, location_street,
                 location_city):

        source = "Landesfrauenrat Berlin"

        super().__init__(identifier, source, url, title, subtitle, description, image, image_bucket, start_date,
                         end_date, category, languages, organizer, fees, contact_person, contact_phone, contact_mail,
                         location_street, location_city)


def transform_html(workspace_path, html_file_name, xml_file_name):
    """
    Transforms an html file into a well-formed xml file by removing tags and attributes
    :param workspace_path:
    :param html_file_name:
    :param xml_file_name:
    :return:
    """
    with open(os.path.join(workspace_path, html_file_name), "r") as html_file:
        content = " ".join(html_file.read().splitlines())
        content = re.sub(r'.*<body', "<body", content)
        content = re.sub(r'body>.*', "body>", content)

        content = well_form(content)

    with open(os.path.join(workspace_path, xml_file_name), "w") as xml_file:
        xml_file.write(content)


def parse_html(logger, workspace_path, html_file_name, clean, quiet) -> List[AbstractEvent]:
    """
    Parses html file into a list of events
    :param logger:
    :param workspace_path:
    :param html_file_name:
    :param clean:
    :param quiet:
    :return:
    """
    xml_file_name = re.sub('.html$', ".xml", html_file_name)
    transform_html(workspace_path, html_file_name, xml_file_name)

    root = element_tree.parse(os.path.join(workspace_path, xml_file_name)).getroot()

    events = []

    # Parse page
    for event_view in root.findall('.//ul[@class="event-list-view"]')[0]:

        field_title = event_view.find('.//a')
        field_subtitle = root.find('.//h1[@class="event--subtitle"]')
        field_year = event_view.find('.//div[@class="event-year"]')
        field_month = event_view.find('.//div[@class="event-month"]')
        field_day = event_view.find('.//div[@class="event-day"]')
        field_time = root.find('.//span[@class="event-time"]')
        field_location = root.find('.//span[@class="event-location"]')
        field_language = root.find('.//div[@class="field--spoken-language"]/dt')
        field_fee = root.find('.//div[@class="field--spoken-language"]/dd')  # TODO: fix copy paste
        field_content = root.findall('.//div[@class="event-content"]')
        field_url = event_view.find('.//a').attrib.get('href')

        title = field_title.text.strip() if field_title is not None and field_title.text is not None else ""
        identifier = title.replace(' // ', ' ').lower() \
                .replace(".", "").replace("!", "").replace("&", "").replace(":", "") \
                .replace("„", "").replace("“", "").replace("\"", "") \
                .replace(" ", "-").replace("--", "-").replace("--", "-") \
                .replace("-–-", "-").replace("---", "-")

        subtitle = field_subtitle.text.strip() if field_subtitle is not None and field_subtitle[0].text is not None else ""
        description = field_content[0].text.strip() if field_content is not None and field_content[0].text is not None else ""
        image = ""

        if field_year is not None and field_year.text is not None and \
                field_month is not None and field_month.text is not None and \
                field_day is not None and field_day.text is not None and \
                field_time is not None and field_time.text is not None:
            start_date = format_date_time_start(field_year.text, field_month.text, field_day.text, field_time.text)
            end_date = format_date_time_end(field_year.text, field_month.text, field_day.text, field_time.text)
        elif field_year is not None and field_year.text is not None and \
                field_month is not None and field_month.text is not None and \
                field_day is not None and field_day.text is not None:
            start_date = format_date_split(field_year.text, field_month.text, field_day.text)
            end_date = format_date_split(field_year.text, field_month.text, field_day.text)
        else:
            start_date = ""
            end_date = ""

        category = ""
        languages = [field_language.text.strip()] if field_language is not None and field_language.text is not None else []
        organizer = field_location.text.strip() if field_location is not None and field_location.text is not None else ""
        fees = [field_fee.text.strip()] if field_fee is not None and field_fee.text is not None else ""
        url = field_url.strip() if field_url is not None else ""

        contact_person = ""
        contact_phone = ""
        contact_mail = ""

        location_street = ""
        location_city = ""

        event = LfrEvent(
            identifier=identifier,
            url=url,
            title=title,
            subtitle=subtitle,
            description=description,
            image=image,
            image_bucket=None,
            start_date=start_date,
            end_date=end_date,
            category=category,
            languages=languages,
            organizer=organizer,
            fees=fees,
            contact_person=contact_person,
            contact_phone=contact_phone,
            contact_mail=contact_mail,
            location_street=location_street,
            location_city=location_city
        )

        events.append(event)

    return events


class LfrCrawler(AbstractCrawler):
    """
    Crawls events posted on https://www.landesfrauenrat-berlin.de/veranstaltungen-in-berlin/
    """

    url = f"https://www.landesfrauenrat-berlin.de/veranstaltungen-in-berlin/"

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

        super().run(logger, workspace_path, content_path, uploads_path, clean, quiet)

        # Download overview site
        download_site(logger, workspace_path, self.url, "lfr.html", clean, quiet)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "lfr.html", clean, quiet):
            # Generate image for event
            generate_image(logger, workspace_path, uploads_path, event)

            # Add image bucket URL
            if event.image != "":
                event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

            # Generate content for event
            generate_content(logger, content_path, event)
