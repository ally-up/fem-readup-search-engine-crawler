import os
import re
import xml.etree.ElementTree as element_tree
from typing import List

import urllib3

from abstract_crawler import AbstractCrawler, download_site, well_form, format_identifier, format_title, \
    generate_content, generate_image, format_date_time, format_date
from abstract_event import AbstractEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FfbizEvent(AbstractEvent):
    """
    Represents an event posted on https://ffbiz.de/
    """

    def __init__(self, identifier, url, title, subtitle, description, image, image_bucket, start_date, end_date,
                 category, languages, fees, contact_person, contact_phone, contact_mail):
        source = "Das feministische Archiv FFBIZ"
        organizer = "Das feministische Archiv FFBIZ"
        location_street = "Eldenaer Straße 35"
        location_city = "10247 Berlin"

        super().__init__(identifier, source, url, title, subtitle, description, image, image_bucket, start_date,
                         end_date, category, languages, organizer, fees, contact_person, contact_phone,
                         contact_mail, location_street, location_city)


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


def parse_html(logger, workspace_path, html_file_name, clean, quiet) -> List[FfbizEvent]:
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
    for event in root.find('.//ul[@class="events"]'):
        link = event.find('.//a').attrib['href']
        identifier = format_identifier(re.sub(r'.*/', "", link))
        html_file_name = identifier + ".html"
        xml_file_name = identifier + ".xml"
        date = event.find('.//div[@class="date"]')
        time_raw = event.find('.//div[@class="time"]')
        time = "" if time_raw is None else time_raw.text.replace("um ", "").replace(" Uhr", "")
        field_date_time_with_day = format_date(("00 " + date.text.replace(".", ""))) if time == "" else \
            (format_date_time(("00 " + date.text.replace(".", "")), time.replace(":", ".")))
        image_url = "" if event.find('.//img') is None else event.find('.//img').attrib['data-src']
        category = event.find('.//div[@class="tags"]')
        download_site(logger, workspace_path, link, html_file_name, clean, quiet)
        with open(os.path.join(workspace_path, html_file_name), "r") as html_file:
            content = " ".join(html_file.read().splitlines())
            content = re.sub(r'.*<article>', "<article>", content)
            content = re.sub(r'/article>.*', "/article>", content)

            content = well_form(content)

        with open(os.path.join(workspace_path, xml_file_name), "w") as xml_file:
            xml_file.write(content)

        root = element_tree.parse(os.path.join(workspace_path, xml_file_name)).getroot()
        field_title = root.find('.//h1').text
        field_title = re.sub(r'#(\d+);', lambda m: chr(int(m.group(1))), field_title)  # convert unicode characters
        field_image = image_url #root.find('.//img').attrib['data-src']
        field_content = ""
        text = root.find('.//main')
        for paragraph in text.findall('.//p'):

            if paragraph.text is not None:
                paragraph_text = re.sub(r'#(\d+);', lambda m: chr(int(m.group(1))), paragraph.text)
                field_content += f'{paragraph_text}\n'

        title = field_title if field_title is not None and field_title is not None else ""
        subtitle = ""
        description = field_content.strip() if field_content is not None else ""
        image = field_image if field_image is not None else ""
        start_date = field_date_time_with_day \
            if field_date_time_with_day is not None and field_date_time_with_day is not None else ""
        end_date = field_date_time_with_day \
            if field_date_time_with_day is not None and field_date_time_with_day is not None else ""
        category = category.text.strip() if category is not None and category.text is not None else ""
        languages = []
        fees = ""

        url = link

        contact_person = ""
        contact_phone = ""
        contact_mail = ""

        event = FfbizEvent(
            identifier=identifier,
            title=title,
            subtitle=subtitle,
            description=description,
            image=image,
            image_bucket=None,
            start_date=start_date,
            end_date=end_date,
            category=category,
            languages=languages,
            fees=fees,
            url=url,
            contact_person=contact_person,
            contact_phone=contact_phone,
            contact_mail=contact_mail
        )

        events.append(event)

    return events


class FfbizCrawler(AbstractCrawler):
    """
    Crawls events posted on https://www.urania.de/
    """

    url = f"https://ffbiz.de/aktivitaeten/veranstaltungen"

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
        download_site(logger, workspace_path, self.url, "ffbiz.html", clean, quiet)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "ffbiz.html", clean, quiet):
            # Generate image for event
            generate_image(logger, workspace_path, uploads_path, event)

            # Add image bucket URL
            if event.image != "":
                event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

            # Generate content for event
            generate_content(logger, content_path, event)

