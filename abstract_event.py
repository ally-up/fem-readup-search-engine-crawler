from datetime import datetime


class AbstractEvent:
    """
    Represents an event
    """

    def __init__(self, identifier, source, url, title, subtitle, description, image, image_bucket, start_date, end_date,
                 category, languages, organizer, fees, contact_person, contact_phone, contact_mail,
                 location_street, location_city):
        self.type = "event"

        self.identifier = identifier.replace("amp;", "").replace("--", "-")
        self.source = source
        self.url = url

        self.title = title.replace("amp;", "&")
        self.subtitle = subtitle.replace("amp;", "&")
        self.description = description.replace("amp;", "&").replace("\"", "")
        self.image = image.replace("amp;", "&")
        self.image_bucket = image_bucket
        self.start_date = start_date
        self.end_date = end_date
        self.category = category
        self.languages = languages
        self.organizer = organizer
        self.fees = fees

        self.contact_person = contact_person
        self.contact_phone = contact_phone
        self.contact_mail = contact_mail

        self.location_street = location_street
        self.location_city = location_city

        self.updated = datetime.today().strftime('%Y-%m-%dT%H:%M:%S.000')
