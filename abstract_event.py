from datetime import datetime


class AbstractEvent:
    """
    Represents an event
    """

    def __init__(self, identifier, title, subtitle, description, image, image_bucket, start_date, end_date, place,
                 category, languages, fees, url, contact_person, contact_phone, contact_mail):
        self.type = "event"
        self.identifier = identifier.replace("amp;", "").replace("--", "-")
        self.title = title.replace("amp;", "&")
        self.subtitle = subtitle.replace("amp;", "&")
        self.description = description.replace("amp;", "&").replace("\"", "")
        self.image = image.replace("amp;", "&")
        self.image_bucket = image_bucket
        self.start_date = start_date
        self.end_date = end_date
        self.place = place
        self.category = category
        self.languages = languages
        self.fees = fees
        self.url = url
        self.contact_person = contact_person
        self.contact_phone = contact_phone
        self.contact_mail = contact_mail

        self.updated = datetime.today().strftime('%Y-%m-%dT%H:%M:%S.000')

