import os
import re
import xml.etree.ElementTree as element_tree
from typing import List

import urllib3

from abstract_crawler import AbstractCrawler, download_site, well_form, generate_content, generate_image
from abstract_event import AbstractEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UraniaEvent(AbstractEvent):
    """
    Represents an event posted on https://www.urania.de/
    """


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


def parse_html(logger, workspace_path, html_file_name, clean, quiet) -> List[UraniaEvent]:
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

    feminist_teasers = []

    # Parse page
    for month in root.find('.//div[@class="view-content"]'):
        for day in month.findall('.//div[@class="daywrapper"]'):
            day.remove(day[0])
            for teaser in day:
                teaser_title = teaser.findtext('.//div[@class="field-content serif_bold FSM"]').lower()
                teaser_sub_title = teaser.findtext('.//div[@class="field-content"]').lower()
                if "feminist" in teaser_title or "feminist" in teaser_sub_title:
                    feminist_teasers.append(teaser)
    base_url = "https://www.urania.de"
    for teaser in feminist_teasers:
        link = teaser.find('.//a').attrib['href']
        identifier = re.sub(r'.*/', "", link)
        html_file_name = identifier + ".html"
        xml_file_name = identifier + ".xml"
        download_site(logger, workspace_path, f'{base_url}{link}', html_file_name, clean, quiet)
        transform_html(workspace_path, html_file_name, xml_file_name)

        root = element_tree.parse(os.path.join(workspace_path, xml_file_name)).getroot()

        field_image_url = root.find('.//div[@class="img"]').attrib['style']
        field_image_url = re.sub(r'.*url\(', "", field_image_url)
        field_image_url = re.sub("\);", "", field_image_url)
        field_image_url = re.sub("\?.*", "", field_image_url)

        field_image = field_image_url
        field_title = root.find('.//span[@class="FSXL serif_bold lh12"]')
        field_subtitle = root.find('.//h2[@class="field-content FSL"]')
        field_category = root.find('.//span[@class="field-content"]')
        field_date_time_with_day = root.find('.//span[@class="date-display-single"]').attrib['content']
        field_date_time = root.find('.//span[@class="field--date_time"]')
        field_language = root.find('.//div[@class="field--spoken-language"]/dt')
        field_fee = root.find('.//div[@class="field--spoken-language"]/dd')
        field_content = ""
        for paragraph in root.find('.//div[@class="field-content serif lh14"]'):
            field_content.join(f'{paragraph.text}\n')

        if field_title is not None and field_title.text is not None:
            title = field_title.text.strip()
        else:
            title = ""

        if field_subtitle is not None and field_subtitle.text is not None:
            subtitle = field_subtitle.text.strip()
        else:
            subtitle = ""

        if field_content is not None:
            description = field_content.strip()
        else:
            description = ""

        if field_image is not None:
            image = field_image
        else:
            image = ""

        if field_date_time_with_day is not None and field_date_time_with_day is not None:
            start_date = field_date_time_with_day
            end_date = field_date_time_with_day
        else:
            start_date = ""
            end_date = ""

        place = ""

        if field_category is not None and field_category.text is not None:
            category = field_category.text.split("-")[-1].strip()
        else:
            category = ""

        if field_language is not None and field_language.text is not None:
            languages = [field_language.text.strip()]
        else:
            languages = []

        if field_fee is not None and field_fee.text is not None:
            fees = [field_fee.text.strip()]
        else:
            fees = ""

        url = link
        contact_person = ""
        contact_phone = ""
        contact_mail = ""

        event = UraniaEvent(
            identifier=identifier,
            title=title,
            subtitle=subtitle,
            description=description,
            image=image,
            image_bucket=None,
            start_date=start_date,
            end_date=end_date,
            place=place,
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


class UraniaCrawler(AbstractCrawler):
    """
    Crawls events posted on https://www.urania.de/
    """

    url = f"https://www.urania.de/kalender"

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
        download_site(logger, workspace_path, self.url, "urania.html", clean, quiet)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "urania.html", clean, quiet):
            # Generate image for event
            generate_image(logger, workspace_path, uploads_path, event)

            # Add image bucket URL
            if event.image != "":
                event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

            # Generate content for event
            generate_content(logger, content_path, event)
