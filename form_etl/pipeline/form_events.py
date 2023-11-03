import json
import logging
from datetime import datetime
from typing import Optional

import apache_beam as beam
import requests
from apache_beam.io import WriteToAvro
from apache_beam.io.kafka import ReadFromKafka
from apache_beam.options.pipeline_options import PipelineOptions
from fastavro.schema import load_schema

FORM_EVENT_SCHEMA = load_schema("./avro/form_event.avsc")
FORM_EVENT_RAW_SCHEMA = load_schema("./avro/form_event_raw.avsc")
FORM_FIELD_SCHEMA = load_schema("./avro/form_field.avsc")


def run(
    bootstrap_servers: str,
    topics: str,
    group_id: str,
    form_event_output_path: str,
    form_field_output_path: str,
    max_num_records: int,
    beam_options: Optional[PipelineOptions] = None,
) -> None:
    """
    1. Read from the form.events Kafka topic
    2. Use the event 'id' to call an API at internal.forms/:id to get the latest form state
        - Add a 'retrieved_timestamp' for identifying when the form was actually returned from the API
    3. Transforms, enrichments for easier querying:
        - Enrich form with event-level data
            - now the resulting form_events table will have more metadata about the form
        - Convert kafka timestamp to datetime string
            - analyses will be similar as those on other timestamps in the data
        - Enrich form fields with form-level data for easier querying
            - avoid a JOIN on the form events table downstream
        - Remove form fields from form
            - potentially unbounded length list would always have to be exploded downstream
        - Normalize nested JSON fields to later become columns in form events and form fields tables
            - queries on JSON make downstream SQL code horrible to read & modern DWH can handle many columns
    4. TODO: Write to Parquet on S3. Currently just logging.
    """
    with beam.Pipeline(options=beam_options) as pipeline:
        form_events = (
            pipeline
            | "Read from Kafka"
            >> ReadFromKafka(
                consumer_config={
                    "bootstrap.servers": bootstrap_servers,
                    "group.id": group_id,
                },
                topics=topics.split(","),
                with_metadata=True,
                max_num_records=max_num_records,
            )
            | "Deserialize" >> beam.Map(convert_kafka_record_to_dict)
        )
        # TODO: Remove these. Just so you see something with the Quickstart
        form_events | "Print form.events" >> beam.Map(logging.info)
        form_events | "Write form.events" >> WriteToAvro(
            form_event_output_path, FORM_EVENT_RAW_SCHEMA, file_name_suffix=".avro"
        )

        form_event_data = form_events | "Get Form Data" >> beam.ParDo(
            EnrichEventDataWithFormAPI()
        )

        form_field_data = form_event_data | "Extract Enrich Fields" >> beam.ParDo(
            ExtractEnrichFields()
        )

        (
            form_field_data
            | "Normalize Form Fields" >> beam.Map(dict_normalize)
            | "Write Form Fields"
            >> WriteToAvro(
                form_field_output_path, FORM_FIELD_SCHEMA, file_name_suffix=".avro"
            )
        )

        (
            form_event_data
            | "Drop Fields" >> beam.Map(remove_fields)
            | "Normalize Form Data" >> beam.Map(dict_normalize)
            | "Write Form Data"
            >> WriteToAvro(
                form_event_output_path, FORM_EVENT_SCHEMA, file_name_suffix=".avro"
            )
        )


def convert_kafka_record_to_dict(record):
    """Takes a Kafka message from source
    `ReadFromKafka(..., with_metadata=True)` and returns the
    message value with the timestamp from when the message was
    produced to Kafka."""
    value_json = json.loads(record.value.decode("utf8"))
    value_json["kafka_timestamp"] = str(
        datetime.utcfromtimestamp(record.timestamp // 1000)
    )
    return value_json


class EnrichEventDataWithFormAPI(beam.DoFn):
    """Call the Typeform forms API to enrich form.events data with
    the latest form state data.
    https://stackoverflow.com/a/66701178/22623325
    """

    def process(self, form_event_data: dict):
        uri = f"http://internal.forms/{form_event_data['form_id']}"
        try:
            res = requests.get(uri)
            res.raise_for_status()
        except requests.HTTPError as error:
            # TODO: implement error handling
            raise error
        form_data = res.json()
        form_data["retrieved_timestamp"] = res.headers["date"]
        form_data["event_happened_at"] = form_event_data["event_happened_at"]
        form_data["event_type"] = form_event_data["event_type"]
        yield form_data


class ExtractEnrichFields(beam.DoFn):
    """Return many fields from a form and include form data."""

    def process(self, form_data: dict):
        fields = form_data["fields"]
        for field in fields:
            field["form_id"] = form_data["id"]
            field["form_type"] = form_data["type"]
            field["form_title"] = form_data["title"]
            field["form_settings"] = form_data["settings"]
            field["form_retrieved_timestamp"] = form_data["retrieved_timestamp"]
            field["form_event_happened_at"] = form_data["event_happened_at"]
            field["form_event_type"] = form_data["event_type"]
            yield field


def remove_fields(form_event_data):
    """Drops the 'fields' key from a dict"""
    out = form_event_data
    del out["fields"]
    return out


def dict_normalize(y):
    """Unnests nested dict, creating top-level keys from nested keys.
    https://towardsdatascience.com/flattening-json-objects-in-python-f5343c794b10
    """
    out = {}

    def unnest(x, name=""):
        if type(x) is dict:
            for a in x:
                unnest(x[a], name + a + "_")
        elif type(x) is list:
            i = 0
            for a in x:
                unnest(a, name + str(i) + "_")
                i += 1
        else:
            out[name[:-1]] = x

    unnest(y)
    return out
