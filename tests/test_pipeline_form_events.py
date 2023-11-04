import json
import unittest
from dataclasses import dataclass

import apache_beam as beam
import requests_mock
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

from form_etl.pipeline.form_events import (
    EnrichEventDataWithFormAPI,
    ExtractEnrichFields,
    convert_kafka_record_to_dict,
    dict_normalize,
    remove_fields,
)


# Our input data, which will make up the initial PCollection.
@dataclass
class FormEvent:
    value: bytes  # 'a' has no default value
    timestamp: int


FORM_ID = "abcde"

FORM_EVENTS_EVENT_VALUE_JSON = {
    "form_id": "abcde",
    "form_title": "my_test_form",
    "event_happened_at": "2022-10-02 13:00:15",
    "event_type": "created",
}

FORM_EVENTS_EVENT = FormEvent(
    value=json.dumps(FORM_EVENTS_EVENT_VALUE_JSON).encode("utf8"),
    timestamp=1699022085920,
)

FORM_EVENTS_DICT = {
    **FORM_EVENTS_EVENT_VALUE_JSON,
    **{"kafka_timestamp": "2023-11-03 14:34:45"},
}

FORM_RESPONSE_DICT = {
    "id": "abcde",
    "type": "quiz",
    "title": "my test form",
    "settings": {
        "language": "en",
        "progress_bar": "proportion",
        "show_time_to_complete": True,
        "show_number_of_submissions": False,
        "redirect_after_submit_url": "https://www.google.com",
    },
    "fields": [
        {
            "id": "Auxd6Itc4qgK",
            "title": "What is your name?",
            "reference": "01FKQZ2EK4K7SZS388XF5GA945",
            "validations": {"required": False},
            "type": "open_text",
            "attachment": {
                "type": "image",
                "href": "https://images.typeform.com/images/WMALzu59xbXQ",
            },
        },
        {
            "id": "KFKzcZmvZfxn",
            "title": "What is your phone number?",
            "reference": "9e5ecf29-ee84-4511-a3e4-39805412f8c6",
            "properties": {"default_country_code": "us"},
            "validations": {"required": False},
            "type": "phone_number",
        },
    ],
}

FORM_RESPONSE_HEADERS = {"date": "Wed, 21 Oct 2015 07:28:00 GMT"}

FORM_DICT = {
    **FORM_RESPONSE_DICT,
    **{"retrieved_timestamp": FORM_RESPONSE_HEADERS["date"]},
    **{
        "event_happened_at": FORM_EVENTS_EVENT_VALUE_JSON["event_happened_at"],
        "event_type": FORM_EVENTS_EVENT_VALUE_JSON["event_type"],
    },
}

FORM_WITHOUT_FIELDS_DICT = {
    "id": FORM_RESPONSE_DICT["id"],
    "type": FORM_RESPONSE_DICT["type"],
    "title": FORM_RESPONSE_DICT["title"],
    "settings": FORM_RESPONSE_DICT["settings"],
    "retrieved_timestamp": FORM_RESPONSE_HEADERS["date"],
    "event_happened_at": FORM_EVENTS_EVENT_VALUE_JSON["event_happened_at"],
    "event_type": FORM_EVENTS_EVENT_VALUE_JSON["event_type"],
}

FIELD_DICTS = [
    {**field, **{f"form_{k}": v for k, v in FORM_WITHOUT_FIELDS_DICT.items()}}
    for field in FORM_RESPONSE_DICT["fields"]
]

FORM_WITHOUT_FIELDS_NORMALIZED_DICT = {
    "id": FORM_RESPONSE_DICT["id"],
    "type": FORM_RESPONSE_DICT["type"],
    "title": FORM_RESPONSE_DICT["title"],
    **{f"settings_{k}": v for k, v in FORM_RESPONSE_DICT["settings"].items()},
    "retrieved_timestamp": FORM_RESPONSE_HEADERS["date"],
    "event_happened_at": FORM_EVENTS_EVENT_VALUE_JSON["event_happened_at"],
    "event_type": FORM_EVENTS_EVENT_VALUE_JSON["event_type"],
}


class ConvertKafkaRecordToDictTest(unittest.TestCase):
    def test_has_kafka_timestamp(self):
        output = convert_kafka_record_to_dict(FORM_EVENTS_EVENT)
        assert "kafka_timestamp" in output.keys()

    def test_has_expected_output(self):
        expected_output = [FORM_EVENTS_DICT]
        with TestPipeline() as p:
            input = p | beam.Create([FORM_EVENTS_EVENT])
            output = input | beam.Map(convert_kafka_record_to_dict)
            assert_that(output, equal_to(expected_output), label="CheckOutput")


class EnrichEventDataWithFormAPITest(unittest.TestCase):
    @requests_mock.Mocker()
    def test_has_expected_output(self, m):
        expected_output = [FORM_DICT]
        m.get(
            f"http://internal.forms/{FORM_ID}",
            json=FORM_RESPONSE_DICT,
            headers=FORM_RESPONSE_HEADERS,
        )
        with TestPipeline() as p:
            input = p | beam.Create([FORM_EVENTS_DICT])
            output = input | beam.ParDo(
                EnrichEventDataWithFormAPI("http://internal.forms/")
            )
            assert_that(output, equal_to(expected_output), label="CheckOutput")


class ExtractEnrichFieldsTest(unittest.TestCase):
    def test_has_expected_output(self):
        expected_output = FIELD_DICTS
        with TestPipeline() as p:
            input = p | beam.Create([FORM_DICT])
            output = input | beam.ParDo(ExtractEnrichFields())
            assert_that(output, equal_to(expected_output), label="CheckOutput")


class RemoveFieldsTest(unittest.TestCase):
    def test_has_expected_output(self):
        expected_output = [FORM_WITHOUT_FIELDS_DICT]
        with TestPipeline() as p:
            input = p | beam.Create([FORM_DICT])
            output = input | beam.Map(remove_fields)
            assert_that(output, equal_to(expected_output), label="CheckOutput")


class DictNormalizeTest(unittest.TestCase):
    def test_has_expected_output_form(self):
        expected_output = [FORM_WITHOUT_FIELDS_NORMALIZED_DICT]
        with TestPipeline() as p:
            input = p | beam.Create([FORM_WITHOUT_FIELDS_DICT])
            output = input | beam.Map(dict_normalize)
            assert_that(output, equal_to(expected_output), label="CheckOutput")

    # TODO: Test with fields data
