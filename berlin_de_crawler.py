import math
import os
import re
import datetime
import xml.etree.ElementTree as element_tree
from typing import List

import requests
import urllib3
from lxml import html

from abstract_crawler import AbstractCrawler, download_site, well_form, format_title, format_identifier, \
    format_date_time, format_date_times, format_date, generate_content, generate_image, format_month, format_date_split
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
        content = content.replace("<li>Fotoausstellungen</a>", "<li>Fotoausstellungen")
        content = content.replace("<li>Vorträge</a>", "<li>Vorträge")

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
        content = re.sub("Seminare/Workshops/Führungen</a>", "Seminare/Workshops/Führungen", content)
        content = re.sub(r'<aside(.*?)/aside>', "", content)
        content = content.replace('loading="lazy"', "")
        content = content.replace("<li>Fotoausstellungen</a>", "<li>Fotoausstellungen")
        content = content.replace('<option value="upcoming" selected>', '<option value="upcoming">')

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
        field_date_time = event_view.find('.//dl/dd[1]/a').text.strip() \
            if event_view.find('.//dl/dd[1]/a') is not None else None
        field_location = event_view.find('.//dl/dd[3]/a') if event_view.find('.//dl/dd[3]/a') is not None else None
        field_organizer = event_view.find('.//dl/dd[2]/a') if event_view.find('.//dl/dd[3]/a') is not None else None
        end_date_time = None
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

            if field_date_time is not None:
                if field_date_time.__contains__("bis"):
                    min_time = datetime.time.min
                    if (len(field_date_time.split("bis")[0]) > 0):
                        field_date_start = field_date_time.split(" bis ")[0].split(",")[1].strip().split(".")
                        start_day = format_date_split(field_date_start[2], field_date_start[1], field_date_start[0])
                        field_date_time = f"{start_day}T{min_time}.000"
                        field_date_end = field_date_time.split(" bis ")[1].split(",")[1].strip().split(".")
                        end_day = format_date_split(field_date_end[2], field_date_end[1], field_date_end[0])
                        end_date_time = f"{end_day}T{min_time}.000"
                    else:
                        field_date_start = field_date_time.split("bis")[1].strip().split(".")
                        end_day = format_date_split(field_date_start[2], field_date_start[1], field_date_start[0])
                        end_date_time = f"{end_day}T{min_time}.000"
                        field_date_time = datetime.datetime.now() - datetime.timedelta(days=30)
                        field_date_time = field_date_time.__str__().replace(" ", "T")



                else:
                    field_date_time = format_date_time(field_date_time.split(",")[1],
                                                   field_date_time.split(",")[2].replace(":", ".").strip(" Uhr"))
            else:
                laufzeit = root.find('.//div[@class="js-block-limit-height"]/p').text if root.find('.//div[@class="js-block-limit-height"]/p') is not None and root.find('.//div[@class="js-block-limit-height"]/p').text is not None else ""
                if laufzeit.__contains__("Laufzeit"):
                    min_time = datetime.time.min
                    laufzeit = laufzeit.strip()[9:].strip()
                    if laufzeit.__contains__("bis"):
                        field_date_start = laufzeit.split(" bis ")[0].split(",")[1].strip().split(".")
                        start_day = format_date_split(field_date_start[2], field_date_start[1], field_date_start[0])
                        field_date_time = f"{start_day}T{min_time}.000"
                        field_date_end = laufzeit.split(" bis ")[1].split(",")[1].strip().split(".")
                        end_day = format_date_split(field_date_end[2], field_date_end[1], field_date_end[0])
                        end_date_time = f"{end_day}T{min_time}.000"

                    if laufzeit.__contains__("seit"):
                        field_date_start = laufzeit.split(" ")
                        start_day = format_date_split(field_date_start[2], field_date_start[1], "01")
                        field_date_time = f"{start_day}T{min_time}.000"
                        end_date_time = datetime.datetime.now() + datetime.timedelta(days=90)
                        end_date_time = end_date_time.__str__().replace(" ", "T")







            title = format_title(field_title.text) if field_title is not None and field_title.text is not None else ""
            subtitle = field_subtitle.text.strip() if field_subtitle is not None and field_subtitle.text is not None else ""
            description = field_content.strip() if field_content is not None else ""
            image = field_image if field_image is not None else ""

            start_date = field_date_time if field_date_time is not None else ""
            end_date = end_date_time if end_date_time is not None else field_date_time if field_date_time is not None else ""

            category = field_category.text.strip() if field_category is not None and field_category.text is not None else ""

            languages = []

            location = field_location.text.strip() if field_location is not None and field_location.text is not None else ""
            organizer = field_organizer.text.strip() \
                if field_organizer is not None and field_organizer.text is not None else ""
            fees = ""

            contact_person = ""
            contact_phone = ""
            contact_mail = ""
            location_street = ""
            location_city = ""

            if location is not "" and (location.__contains__(",") is True):
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

    url = f"https://www.berlin.de/tickets/suche/"

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

        current_time = datetime.datetime.now()
        end_time = current_time + datetime.timedelta(days=30)

        search_params = ["feministisch", "feminism", "feminist", "intersektional", "gender"]
        search_string = ""
        for param in search_params:
            search_string = search_string + param + "%20"

        query = f"?order_by=start&q={search_string}&date={current_time.date()}T00%3A00%3A00.000000%2B02%3A00%2C" \
                f"{end_time.date()}T23%3A59%3A59.000000%2B02%3A00"
        full_url = self.url + query

        downloaded_site = requests.get(full_url)
        tree = html.fromstring(downloaded_site.content)

        number_events = tree.xpath("/html/body/div[1]/div/div[3]/div/div/p[2]/b/span")[0].attrib['data-events-count']
        number_pages = math.ceil(int(number_events) / 15)

        for page in range(0, number_pages):
            offset = 15 * page
            paged_url = full_url + f"&offset={offset}"
            html_file_name = f"berlin_de-{page}.html"
            # Download overview site
            download_site(logger, workspace_path, paged_url, html_file_name, clean, quiet)

            # Parse overview site and iterate over events
            for event in parse_html(logger, workspace_path, html_file_name, clean, quiet):
                # Generate image for event
                generate_image(logger, workspace_path, uploads_path, event)

                # Add image bucket URL
                if event.image != "":
                    event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

                # Generate content for event
                generate_content(logger, content_path, event)
