from datetime import datetime

"""
Represents an event posted on 
"""

class Event:
    def __init__(self, identifier, title, subtitle, description, image, start_date, end_date, place, category,
                 languages, fees, url, contact_person, contact_phone, contact_mail):
        self.identifier = identifier
        self.title = title
        self.subtitle = subtitle
        self.description = description
        self.image = image
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

        self.updated = datetime.today().strftime('%d-%m-%Y')