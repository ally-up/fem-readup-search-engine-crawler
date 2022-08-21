import os
import re
import xml.etree.ElementTree as element_tree
from typing import List

import requests
import urllib3

from event import Event

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BoellEvent(Event):
    """
    Represents an event posted on https://calendar.boell.de/
    """

    def __init__(self, identifier, title, subtitle, description, image, start_date, end_date, place, category,
                 languages, fees, url, contact_person, contact_phone, contact_mail):
        super().__init__(identifier, title, subtitle, description, image, start_date, end_date, place, category,
                         languages, fees, url, contact_person, contact_phone, contact_mail)


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
    Downloads content of a given URL into a file
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
        content = re.sub(r'<br(.*?)>', "", content)
        content = re.sub(r'<img(.*?)>', "", content)
        content = re.sub(r'<input(.*?)>', "", content)
        content = re.sub(r'<meta(.*?)>', "", content)
        content = re.sub(r'data-drupal-messages-fallback', "", content)
        content = re.sub(r'xml:lang="EN-US"', "", content)
        content = re.sub(r'&nbsp;–', "", content)

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

        html_file_name = identifier + ".html"
        xml_file_name = identifier + ".xml"

        download_site(logger, workspace_path, link, html_file_name, clean, quiet)
        transform_html(workspace_path, html_file_name, xml_file_name)

        root = element_tree.parse(os.path.join(workspace_path, xml_file_name)).getroot()

        field_title = root.find('.//h1[@class="event--title"]')
        field_subtitle = root.find('.//h1[@class="event--subtitle"]')
        field_category = root.find('.//span[@class="field--event_type"]')
        field_date_day = root.find('.//span[@class="field--date_date"]')
        field_date_day_only = root.find('.//span[@class="field--date_date day-only"]')
        field_date_time = root.find('.//span[@class="field--date_time"]')
        field_language = root.find('.//div[@class="field--spoken-language"]/dt')
        field_fee = root.find('.//div[@class="field--spoken-language"]/dd')
        field_content = root.findall('.//div[@class="event--content"]/div[@class="column"]/div')

        if field_title is not None and field_title.text is not None:
            title = field_title.text.strip()
        else:
            title = ""

        if field_subtitle is not None and field_subtitle[0].text is not None:
            subtitle = field_subtitle.text.strip()
        else:
            subtitle = ""

        if field_content is not None and field_content[0].text is not None:
            description = field_content[0].text.strip()
        else:
            description = ""

        image = ""

        if field_date_day is not None and field_date_time is not None:
            start_date = f"{field_date_day.text.strip()} {field_date_time.text.strip().split(' ')[0]}"
            end_date = f"{field_date_day.text.strip()} {field_date_time.text.strip().split(' ')[1]}"
        elif field_date_day_only is not None:
            start_date = f"{field_date_day_only.text.strip()}"
            end_date = f"{field_date_day_only.text.strip()}"
        else:
            start_date = ""
            end_date = ""

        place = ""

        if field_category is not None and field_category.text is not None:
            category = field_category.text.strip()
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

        url = ""
        contact_person = ""
        contact_phone = ""
        contact_mail = ""

        event = BoellEvent(
            identifier=identifier,
            title=title,
            subtitle=subtitle,
            description=description,
            image=image,
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


def generate_content(logger, results_path, event: BoellEvent):
    file_name = f"{event.identifier}.md"
    file_path = os.path.join(results_path, file_name)

    values = {}
    values_contact = {}

    languages = []

    if os.path.exists(file_path):

        # Read existing file
        with open(file_path, 'r') as file:
            for line in file.readlines():
                if "=" in line:
                    key = line.split("=")[0].strip().replace("\"", "").replace("'", "")
                    value = line.split("=")[1].strip().replace("\"", "").replace("'", "")
                    value = str(value)

                    if key == "contact_person" or key == "contact_phone" or key == "contact_mail":
                        values_contact[key] = value
                    elif key == "languages":
                        languages_list = value.removeprefix("'").removesuffix("'").replace("[", "").replace("]", "")
                        if len(languages_list) > 0:
                            types = languages_list.split(",")
                        pass
                    else:
                        values[key] = value

    # Update values
    if len(event.title) > 0:
        values["title"] = event.image
    if len(event.subtitle) > 0:
        values["subtitle"] = event.subtitle
    if len(event.description) > 0:
        values["description"] = event.description
    if len(event.image) > 0:
        values["image"] = event.image
    if len(event.start_date) > 0:
        values["start_date"] = event.start_date
    if len(event.end_date) > 0:
        values["end_date"] = event.end_date
    if len(event.place) > 0:
        values["place"] = event.place
    if len(event.category) > 0:
        values["category"] = event.category
    if len(event.languages) > 0:
        values["languages"] = event.languages
    if len(event.fees) > 0:
        values["fees"] = event.fees
    if len(event.url) > 0:
        values["url"] = event.url

    if len(event.languages) > 0:
        for language in event.languages:
            languages.append(language)
            languages = list(dict.fromkeys(types))

    if len(event.contact_person) > 0:
        values_contact["contact_person"] = event.contact_person
    if len(event.contact_phone) > 0:
        values_contact["contact_phone"] = event.contact_phone
    if len(event.contact_mail) > 0:
        values_contact["contact_mail"] = event.contact_mail

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
    content += "\n+++"

    # Clean up
    content = content.replace(",]", "]")

    with open(file_path, 'w') as file:
        logger.log_line(f"✓ Generate {file_name}")
        file.write(content)


class BoellCrawler:
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

    def run(self, logger, workspace_path, results_path, clean=False, quiet=False):
        """
        Runs crawler
        :param logger:
        :param workspace_path:
        :param results_path:
        :param clean:
        :param quiet:
        :return:
        """
        # Make results path
        os.makedirs(os.path.join(workspace_path), exist_ok=True)

        # Download overview site
        download_site(logger, workspace_path, self.url, "boell.html", clean, quiet)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "boell.html", clean, quiet):
            # Generate content for event
            generate_content(logger, results_path, event)
