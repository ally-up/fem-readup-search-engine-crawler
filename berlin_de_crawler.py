import os
import re
import xml.etree.ElementTree as element_tree
from typing import List

import urllib3

from abstract_crawler import AbstractCrawler, download_site, well_form, format_title, format_identifier, \
    format_date_time, format_date_times, format_date, generate_content, generate_image
from abstract_event import AbstractEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BerlinDeEvent(AbstractEvent):
    """
    Represents an event posted on https://www.berlin.de/
    """

    def __init__(self, identifier, url, title, subtitle, description, image, image_bucket, start_date, end_date,
                 category, languages, organizer, fees, contact_person, contact_phone, contact_mail, location_street,
                 location_city):
        source = "Berlin.de"

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
        content = re.sub(r'.*<div class="ticketing-events"', '<div class="ticketing-events"', content)
        content = re.sub(r'<div class="ticketing-pager".*', '', content)
        content = content.strip()
        content = re.sub("Seminare/Workshops/Führungen</a>", "Seminare/Workshops/Führunge", content)

        content = well_form(content)

    with open(os.path.join(workspace_path, xml_file_name), "w") as xml_file:
        xml_file.write(content)


def transform_sub_page_html(workspace_path, html_file_name, xml_file_name):
    """
    Transforms an html file into a well-formed xml file by removing tags and attributes
    :param workspace_path:
    :param html_file_name:
    :param xml_file_name:
    :return:
    """
    with open(os.path.join(workspace_path, html_file_name), "r") as html_file:
        content = " ".join(html_file.read().splitlines())

        content = re.sub(r'.*<div id="ems-main"', '<div id="ems-main"', content)
        content = re.sub(r'<hr.*', '', content)
        content = content.strip()
        content = re.sub("Seminare/Workshops/Führungen</a>", "Seminare/Workshops/Führunge", content)
        content = re.sub(r'<aside(.*?)/aside>', "", content)
        content = content.replace('loading="lazy"', "")

        content = well_form(content)

    with open(os.path.join(workspace_path, xml_file_name), "w") as xml_file:
        xml_file.write(content)


def parse_html(logger, workspace_path, html_file_name, clean, quiet) -> List[BerlinDeEvent]:
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
    for event_view in root.findall('.//article'):
        field_image = event_view.find('.//img')
        if field_image is not None:
            field_image = field_image.attrib['src']
        field_title = event_view.find('.//h3/a')

        field_url = event_view.find('.//h3/a').attrib['href']
        field_category = event_view.find('.//div[@class="teaser__meta text--meta"]/ul/li/a')
        field_date_time = event_view.find('.//dl/dd[1]/a').text.strip()
        field_location = event_view.find('.//dl/dd[3]/a')
        field_organizer = event_view.find('.//dl/dd[2]/a')

        if field_url is not None:
            identifier = format_identifier(re.sub(r'.*/', ".", field_url[:-1]))
            identifier = re.sub(
                r'-[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$',
                "", identifier)
            html_file_name = identifier + ".html"
            xml_file_name = identifier + ".xml"

            download_site(logger, workspace_path, field_url, html_file_name, clean, quiet)
            transform_sub_page_html(workspace_path, html_file_name, xml_file_name)

            root = element_tree.parse(os.path.join(workspace_path, xml_file_name)).getroot()
            field_content = ""
            intro_text = root.find('.//p')
            if intro_text is not None and intro_text.text is not None:
                field_content = f'{intro_text.text.strip()}\n'
            if root.find('.//div[@class="hb-paragraph"]') is not None:
                for paragraph in root.findall('.//div[@class="js-block-limit-height"]/div/div'):
                    if paragraph.text is not None:
                        field_content += f'{paragraph.text.strip()}\n'
            else:
                field_content = root.find('.//div[@class="js-block-limit-height"]/div').text.strip()

            field_subtitle = root.find('.//h2')

            field_date_time = format_date_time(field_date_time.split(",")[1],
                                               field_date_time.split(",")[2].replace(":", "."))

            title = format_title(field_title.text) if field_title is not None and field_title.text is not None else ""
            subtitle = field_subtitle.text.strip() if field_subtitle is not None and field_subtitle.text is not None else ""
            description = field_content.strip() if field_content is not None else ""
            image = field_image if field_image is not None else ""

            start_date = field_date_time if field_date_time is not None else ""
            end_date = field_date_time if field_date_time is not None else ""

            category = field_category.text.strip() if field_category is not None and field_category.text is not None else ""

            languages = []

            location = field_location.text.strip() if field_location is not None and field_location.text is not None else ""
            organizer = field_organizer.text.strip() \
                if field_organizer is not None and field_organizer.text is not None else ""
            fees = ""

            contact_person = ""
            contact_phone = ""
            contact_mail = ""

            location_street = location.split(",")[0]
            location_city = location.split(",")[1]

            event = BerlinDeEvent(
                identifier=identifier,
                url=field_url,
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
        else:
            pass

    return events


class BerlinDeCrawler(AbstractCrawler):
    """
    Crawls events posted on https://www.berlin.de/
    """

    url = f"https://www.berlin.de/tickets/suche/?q=feminis&date=&order_by=score#ems-searchresults-anchor"

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
        download_site(logger, workspace_path, self.url, "berlin_de.html", clean, quiet)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "berlin_de.html", clean, quiet):
            # Generate image for event
            generate_image(logger, workspace_path, uploads_path, event)

            # Add image bucket URL
            if event.image != "":
                event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

            # Generate content for event
            generate_content(logger, content_path, event)
