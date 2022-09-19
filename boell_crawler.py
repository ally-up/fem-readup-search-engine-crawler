import os
import re
import xml.etree.ElementTree as element_tree
from typing import List

import urllib3

from abstract_crawler import AbstractCrawler, download_site, well_form, format_date_time, format_date_times, \
    format_date, generate_content, generate_image
from abstract_event import AbstractEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BoellEvent(AbstractEvent):
    """
    Represents an event posted on https://calendar.boell.de/
    """

    def __init__(self, identifier, url, title, subtitle, description, image, image_bucket, start_date, end_date,
                 category, languages, organizer, fees, contact_person, contact_phone, contact_mail, location_street,
                 location_city):
        source = "Heinrich Böll Stiftung"

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
        content = re.sub(r'.*<main', "<main", content)
        content = re.sub(r'main>.*', "main>", content)

        content = well_form(content)

    with open(os.path.join(workspace_path, xml_file_name), "w") as xml_file:
        xml_file.write(content)


def parse_html(logger, workspace_path, html_file_name, clean, quiet) -> List[BoellEvent]:
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
    for event_view in root.findall('.//div[@class="event-views views-rows"]')[0]:
        link_element = event_view.find('.//div[@class="event--title--wrapper"]/a')
        link = link_element.attrib["href"]

        identifier = re.sub(r'.*/', "", link)
        url = link

        base_url = re.sub(r'\.de.*', ".de", link)

        html_file_name = identifier + ".html"
        xml_file_name = identifier + ".xml"

        download_site(logger, workspace_path, link, html_file_name, clean, quiet)
        transform_html(workspace_path, html_file_name, xml_file_name)

        root = element_tree.parse(os.path.join(workspace_path, xml_file_name)).getroot()

        field_image = root.find('.//div[@class="event--image"]/div/img')
        field_title = root.find('.//h1[@class="event--title"]')
        field_subtitle = root.find('.//h2[@class="event--subtitle"]')
        field_category = root.find('.//span[@class="field--event_type"]')
        field_date_date = root.find('.//span[@class="field--date_date"]')
        field_date_time_with_day = root.find('.//span[@class="field--date_time_with_day"]')
        field_date_time_hyphen = root.find('.//span[@class="field--date_time_hyphen"]')
        field_date_day_only = root.findall('.//span[@class="field--date_date day-only"]')
        field_date_time = root.find('.//span[@class="field--date_time"]')
        field_spoken_language = root.findall('.//dl[@class="field--spoken-language"]/dd')
        # field_location = root.find('.//dl[@class="field--location"]/dd/address')
        field_organizer = root.find('.//dl[@class="field--organizer"]/dd/a')
        field_fee = root.find('.//div[@class="field--spoken-language"]/dd')
        field_content = root.findall('.//div[@class="event--content"]/div[@class="column"]/div')

        title = field_title.text.strip() if field_title is not None and field_title.text is not None else ""
        subtitle = field_subtitle.text.strip() if field_subtitle is not None and field_subtitle.text is not None else ""
        description = field_content[0].text.strip() if field_content is not None and field_content[
            0].text is not None else ""
        image = f'{base_url}{field_image.attrib["src"].strip()}' if field_image is not None and field_image.attrib[
            "src"] is not None else ""

        if field_date_date is not None and field_date_date.text is not None and \
                field_date_time is not None and field_date_time.text is not None:
            start_date = format_date_time(field_date_date.text.strip(), field_date_time.text.strip().split(" ")[0])
            end_date = format_date_time(field_date_date.text.strip(), field_date_time.text.strip().split(" ")[1])
        elif field_date_date is not None and field_date_date.text is not None and \
                field_date_time_with_day is not None and field_date_time_with_day.text is not None and \
                field_date_time_hyphen is not None and field_date_time_hyphen.tail is not None:
            start_date = format_date_times(f"{field_date_date.text} {field_date_time_with_day.text}")
            end_date = format_date_times(field_date_time_hyphen.tail)
        elif field_date_day_only is not None:
            start_date = format_date(field_date_day_only[0].text.strip())
            end_date = format_date(field_date_day_only[1].text.strip())
        else:
            start_date = ""
            end_date = ""

        category = field_category.text.strip() if field_category is not None and field_category.text is not None else ""

        if field_spoken_language is not None:
            languages = []

            for spoken_language in field_spoken_language:
                languages.append(spoken_language.text.strip())
        else:
            languages = []

        # location = field_location.text.strip() if field_location is not None and field_location.text is not None
        # else ""
        organizer = field_organizer.text.strip() \
            if field_organizer is not None and field_organizer.text is not None else ""
        fees = [field_fee.text.strip()] if field_fee is not None and field_fee.text is not None else ""

        contact_person = ""
        contact_phone = ""
        contact_mail = ""

        location_street = ""
        location_city = ""

        event = BoellEvent(
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


class BoellCrawler(AbstractCrawler):
    """
    Crawls events posted on https://calendar.boell.de/
    """
    parameter_berlin = "f%5B0%5D=ort_slide_in%3A2445"
    parameter_feminism = "f%5B1%5D=thema_slide_in_menu%3A3431"
    parameter_women = "f%5B2%5D=thema_slide_in_menu%3A3487"
    parameter_antifeminism = "f%5B0%5D=thema_slide_in_menu%3A4371"
    parameter_lbtgi = "f%5B0%5D=thema_slide_in_menu%3A3485"

    parameters = [parameter_berlin, parameter_feminism, parameter_women, parameter_antifeminism, parameter_lbtgi]

    url = f"https://calendar.boell.de/de/calendar/frontpage?{'&'.join(parameters)}"

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
        download_site(logger, workspace_path, self.url, "boell.html", clean, quiet)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "boell.html", clean, quiet):
            # Generate image for event
            generate_image(logger, workspace_path, uploads_path, event)

            # Add image bucket URL
            if event.image != "":
                event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

            # Generate content for event
            generate_content(logger, content_path, event)
