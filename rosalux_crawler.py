import os
import re
import xml.etree.ElementTree as element_tree
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

import urllib3

from abstract_crawler import AbstractCrawler, download_site, well_form, format_title, format_identifier, \
    format_date_time, format_date_times, format_date, generate_content, generate_image, format_date_time_start, \
    format_date_time_end
from abstract_event import AbstractEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RosaluxEvent(AbstractEvent):
    """
    Represents an event posted on https://calendar.boell.de/
    """

    def __init__(self, identifier, url, title, subtitle, description, image, image_bucket, start_date, end_date,
                 category, languages, organizer, fees, contact_person, contact_phone, contact_mail, location_street,
                 location_city):
        source = "Rosa Luxemburg Stiftung"

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
        content = content.replace("<BLOCKQUOTE>", "<blockquote>")
        content = content.replace("<HR>", "")

        content = well_form(content)
        content = re.sub(r'id=c\d{5}', "", content)

    with open(os.path.join(workspace_path, xml_file_name), "w") as xml_file:
        xml_file.write(content)


def parse_html(logger, workspace_path, html_file_name, clean, quiet) -> List[RosaluxEvent]:
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

    event_list = root.findall('.//div[@class="elasticsearch__list"]')
    if event_list:

        # Parse page
        for event_view in root.findall('.//div[@class="elasticsearch__list"]')[0]:
            link_element = event_view.find('.//div[@class="teaser teaser--event"]/a')

            if link_element is not None:
                link = link_element.attrib["href"]

                identifier = format_identifier(re.sub(r'.*/', "", link))
                url = f"https://rosalux.de{link}"

                html_file_name = identifier + ".html"
                xml_file_name = identifier + ".xml"

                field_subtitle = event_view.find('.//p[@class="teaser__text"]')
                field_category = event_view.find('.//b[@class="teaser__event-type"]')
                field_title = field_category.tail.strip()

                download_site(logger, workspace_path, url, html_file_name, clean, quiet)
                transform_html(workspace_path, html_file_name, xml_file_name)

                root = element_tree.parse(os.path.join(workspace_path, xml_file_name)).getroot()

                field_image = root.find('.//div[@class="textmedia__image-liner"]/img')
                field_date_time = root.findall('.//p[@class="news__meta-text"]').pop(1)
                # field_spoken_language = root.findall('.//dl[@class="field--spoken-language"]/dd')
                street = root.find('.//span[@itemprop="streetAddress"]')
                postalCode = root.find('.//span[@itemprop="postalCode"]')
                locality = root.find('.//span[@itemprop="addressLocality"]')
                field_location = f"{street.text.strip()} {postalCode.text} {locality.text}"
                field_organizer = "Rosa-Luxemburg-Stiftung"
                # field_fee = root.find('.//div[@class="field--spoken-language"]/dd')
                field_content = ""
                for paragraph in root.find('.//div[@class="textmedia__text"]'):
                    if paragraph.text is not None:
                        field_content += f'{paragraph.text}\n'

                title = format_title(field_title) if field_title is not None and field_title is not None else ""
                subtitle = field_subtitle.text.strip() if field_subtitle is not None and field_subtitle.text is not None else ""
                description = field_content.strip() if field_content is not None and field_content is not None else ""
                image = field_image.attrib["src"].strip() if field_image is not None and \
                                                             field_image.attrib["src"] is not None else ""
                field_contact_name = root.find('.//div[@class="person__column person__column--first"]/h4')
                field_contact_email = root.find(
                    './/div[@class="person__column person__column--second"]/p[@class="person__info person__info--email"]/a')

                if field_date_time is not None and field_date_time.text is not None:

                    start_date_raw = field_date_time.text.strip().split("-")[0]
                    end_date_raw = field_date_time.text.strip().split("-")[1].strip()
                    start_date = format_date_time_start(start_date_raw.split(",")[0].split(".")[2],
                                                        start_date_raw.split(",")[0].split(".")[1],
                                                        start_date_raw.split(",")[0].split(".")[0],
                                                        start_date_raw.split(",")[1], ":")
                    if end_date_raw.__contains__(","):
                        end_date = format_date_time_end(end_date_raw.split(",")[0].split(".")[2],
                                                        end_date_raw.split(",")[0].split(".")[1],
                                                        end_date_raw.split(",")[0].split(".")[0],
                                                        end_date_raw.split(",")[1], ":")
                    else:
                        end_date = format_date_time_end(start_date_raw.split(",")[0].split(".")[2],
                                                        start_date_raw.split(",")[0].split(".")[1],
                                                        start_date_raw.split(",")[0].split(".")[0],
                                                        end_date_raw, ":")

                else:
                    start_date = ""
                    end_date = ""

                category = field_category.text.strip() if field_category is not None and field_category.text is not None else ""

                languages = []

                # location = field_location.text.strip() if field_location is not None and field_location.text is not None
                # else ""
                organizer = field_organizer.strip() \
                    if field_organizer is not None and field_organizer is not None else ""
                fees = ""

                contact_person = field_contact_name
                contact_phone = ""
                contact_mail = field_contact_email

                location_street = street
                location_city = locality

                event = RosaluxEvent(
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
            else:
                pass

    return events


def download_file_with_webdriver(logger, file_path, url, next_month):
    """
    Downloads value of a given URL into a file
    :param logger:
    :param file_path:
    :param url:
    :param next_month:
    :return:
    """
    try:
        op = webdriver.ChromeOptions()
        op.add_argument('headless')
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=op)
        #driver = webdriver.Chrome(options=op)
        # driver = webdriver.Chrome()
        driver.get(url)
        if next_month:
            driver.find_element(By.CSS_SELECTOR, ".calendar__change-month-icon--next > use").click()
        driver.find_element(By.ID, "elasticsearch-dynamic-id-1").click()
        driver.find_element(By.ID, "control-tab-2").click()
        driver.find_element(By.CSS_SELECTOR, "#tab-2 .checkbox:nth-child(2) > .checkbox__label").click()
        driver.find_element(By.ID, "control-tab-1").click()
        driver.find_element(By.ID, "elastic-search-place").click()
        driver.find_element(By.ID, "elastic-search-place").send_keys("Berlin")
        driver.find_element(By.CSS_SELECTOR, ".elasticsearch__form-submit").click()
        data = driver.page_source
        with open(file_path, 'w') as file:
            file.write(data)
        driver.quit()
    except Exception as e:
        logger.log_line(f"✗️ Exception: {str(e)}")
        return None


def download_site_with_webdriver(logger, results_path, url, file_name, clean, quiet, next_month):
    file_path = os.path.join(results_path, file_name)

    # Check if result needs to be generated
    if clean or not os.path.exists(file_path):

        download_file_with_webdriver(
            logger=logger,
            file_path=file_path,
            url=url,
            next_month=next_month
        )

        if not quiet:
            logger.log_line(f"✓ Download {file_path}")
    else:
        logger.log_line(f"✓ Already exists {file_path}")


class RosaluxCrawler(AbstractCrawler):
    """
    Crawls events posted on https://www.rosalux.de/veranstaltungen
    """

    url = "https://www.rosalux.de/veranstaltungen"

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

        # Download overview site for this month
        download_site_with_webdriver(logger, workspace_path, self.url, "rosalux.html", clean, quiet, False)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "rosalux.html", clean, quiet):
            # Generate image for event
            generate_image(logger, workspace_path, uploads_path, event)

            # Add image bucket URL
            if event.image != "":
                event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

            # Generate content for event
            generate_content(logger, content_path, event)

        # Download overview site for next month
        download_site_with_webdriver(logger, workspace_path, self.url, "rosalux-2.html", clean, quiet, True)

        # Parse overview site and iterate over events
        for event in parse_html(logger, workspace_path, "rosalux-2.html", clean, quiet):
            # Generate image for event
            generate_image(logger, workspace_path, uploads_path, event)

            # Add image bucket URL
            if event.image != "":
                event.image_bucket = f"https://storage.googleapis.com/fem-readup.appspot.com/{event.identifier}.webp"

            # Generate content for event
            generate_content(logger, content_path, event)
