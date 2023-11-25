# form-etl

A locally tested Apache Beam streaming pipeline that extracts messages from a Kafka topic, enriches them with an external API, models the data, and writes it to S3.

## Testing

See "Development Environment (MacOS)" to install Python and Poetry.

```zsh
poetry install --with dev
poetry run python -m unittest
```

## Quickstart

You'll need Docker installed and running.

To write to S3, you must have an S3 bucket and configure your access credentials via the CLI.

See "Development Environment (MacOS)" to install Python and Poetry.

```zsh
# Init output S3 bucket
mkdir -p data/output

# Start Kafka & Minio (S3) locally
docker-compose up -d

# Install Python dependencies
poetry install --with api

# Start the API locally
poetry run uvicorn api:app --reload

# Run the Beam app
# This might not behave properly if --max_num_records is None due to DirectRunner limitations with unbounded sources
AWS_REGION='' AWS_ACCESS_KEY_ID=admin AWS_SECRET_ACCESS_KEY=password AWS_ENDPOINT_URL_S3=http://localhost:9000 \
    poetry run python app.py \
      --runner=DirectRunner \
      --max_num_records=1 \
      --bootstrap_servers=localhost:9092 \
      --api_uri=http://localhost:8000 \
      --form_field_output_path=s3://output/form_field/form_field \
      --form_event_output_path=s3://output/form_event/form_event

# Download Kafka
curl https://packages.confluent.io/archive/7.3/confluent-community-7.3.2.tar.gz -o confluent-community-7.3.2.tar.gz
tar -xzf confluent-community-7.3.2.tar.gz

# Produce a message to Kafka topic form.events
echo 'test-key:{"form_id":"abcde","form_title":"my_test_form","event_happened_at":"2022-10-02 13:00:15","event_type":"created"}' | \
./confluent-7.3.2/bin/kafka-console-producer --broker-list localhost:9092 --topic form.events --property "parse.key=true" --property "key.separator=:"
```

You should see an output like this:

```console
...
INFO:root:{'id': 'Auxd6Itc4qgK', 'title': 'What is your name?', 'reference': '01FKQZ2EK4K7SZS388XF5GA945', 'validations_required': False, 'type': 'open_text', 'attachment_type': 'image', 'attachment_href': 'https://images.typeform.com/images/WMALzu59xbXQ', 'form_id': 'abcde', 'form_type': 'quiz', 'form_title': 'my test form', 'form_settings_language': 'en', 'form_settings_progress_bar': 'proportion', 'form_settings_show_time_to_complete': True, 'form_settings_show_number_of_submissions': False, 'form_settings_redirect_after_submit_url': 'https://www.google.com', 'form_retrieved_timestamp': 'Sat, 04 Nov 2023 15:51:50 GMT, Sat, 04 Nov 2023 15:51:51 GMT', 'form_event_happened_at': '2022-10-02 13:00:15', 'form_event_type': 'created'}
INFO:root:{'id': 'KFKzcZmvZfxn', 'title': 'What is your phone number?', 'reference': '9e5ecf29-ee84-4511-a3e4-39805412f8c6', 'properties_default_country_code': 'us', 'validations_required': False, 'type': 'phone_number', 'form_id': 'abcde', 'form_type': 'quiz', 'form_title': 'my test form', 'form_settings_language': 'en', 'form_settings_progress_bar': 'proportion', 'form_settings_show_time_to_complete': True, 'form_settings_show_number_of_submissions': False, 'form_settings_redirect_after_submit_url': 'https://www.google.com', 'form_retrieved_timestamp': 'Sat, 04 Nov 2023 15:51:50 GMT, Sat, 04 Nov 2023 15:51:51 GMT', 'form_event_happened_at': '2022-10-02 13:00:15', 'form_event_type': 'created'}
INFO:root:{'id': 'abcde', 'type': 'quiz', 'title': 'my test form', 'settings_language': 'en', 'settings_progress_bar': 'proportion', 'settings_show_time_to_complete': True, 'settings_show_number_of_submissions': False, 'settings_redirect_after_submit_url': 'https://www.google.com', 'retrieved_timestamp': 'Sat, 04 Nov 2023 15:51:50 GMT, Sat, 04 Nov 2023 15:51:51 GMT', 'event_happened_at': '2022-10-02 13:00:15', 'event_type': 'created'}
...
```

Check the Minio console for the output Avro files.

```zsh
open http://localhost:9000
```

## Data

### Kafka Topic

Kafka Topic `form.events` contains JSON encoded payloads like:

```json
{
    "form_id": "abcde",
    "form_title": "my_test_form",
    "event_happened_at": "2022-10-02 13:00:15",
    "event_type": "created"
}
```

### REST API

The `internal.forms/:id` HTTP API returns JSON encoded payloads like:

```json
{
    "id": "abcde",
    "type": "quiz",
    "title": "my test form",
    "settings": {
        "language": "en",
        "progress_bar": "proportion",
        "show_time_to_complete": true,
        "show_number_of_submissions": false,
        "redirect_after_submit_url": "https://www.google.com",
    },
    "fields": [
        {
            "id": "Auxd6Itc4qgK",
            "title": "What is your name?",
            "reference": "01FKQZ2EK4K7SZS388XF5GA945",
            "validations": {
                "required": false
            },
            "type": "open_text",
            "attachment": {
                "type": "image",
                "href": "https://images.typeform.com/images/WMALzu59xbXQ"
            }
        },
        {
            "id": "KFKzcZmvZfxn",
            "title": "What is your phone number?",
            "reference": "9e5ecf29-ee84-4511-a3e4-39805412f8c6",
            "properties": {
                "default_country_code": "us"
            },
            "validations": {
                "required": false
            },
            "type": "phone_number"
        }
    ]
}
```

## Contributing

Format & lint.

```zsh
poetry install --with dev

poetry run black form_etl/ tests/ app.py api.py
poetry run isort form_etl/ tests/ app.py api.py
poetry run flake8 --max-line-length 119 form_etl/ tests/ app.py api.py
```

### Development Environment (MacOS)

*An opinionated guide to set up your local environment.*

Install [brew](https://github.com/Homebrew/brew).

```zsh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install Python3.8 with [pyenv](https://github.com/pyenv/pyenv). Install [poetry](https://github.com/python-poetry/poetry).

```zsh
brew update
brew install pyenv
pyenv init >> ~/.zshrc
exec zsh -l
pyenv install 3.8
pyenv local 3.8
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
mkdir -p ~/.zfunc
poetry completions zsh > ~/.zfunc/_poetry
exec zsh -l
poetry config virtualenvs.prefer-active-python true
poetry config virtualenvs.in-project true
```

## Discussion

### TLDR

If I had to do this for a production deployment, I would re-write the Apache Beam app as a Flink Job (to use the Flink Iceberg connector) and write to Apache Iceberg formatted tables in S3 (with an AWS Glue metastore) to make data available in real-time without having to write a custom IO connector in Apache Beam. I would write the Flink Job in the Scala or Java language (to take advantage of the [Async IO Flink Operator](https://nightlies.apache.org/flink/flink-docs-release-1.18/docs/dev/datastream/operators/asyncio/), which would be more performant when enriching the event data from the API). I wrote the app as an Apache Beam app in the Python SDK for proof-of-concept and to leverage Apache Beam's more friendly test harness. I might also write the raw data to Apache Iceberg tables in S3 to later write data tests (with DBT) that ensure the modelled tables' data are comparable to the raw data.

### Limitations & Potential Improvements

#### App Architecture

- Error handling in the API enrichment transformation is not implemented yet.
  - Retries with exponential backoff would make the pipeline more stable in the event that the API service is intermittently unavailable.
  - We could write raw event data to a dead-letter queue in the situation that a form with a specific `id` is not available in the data made available by the API.
- No integration with a metastore (Hive, Glue, etc.) is supported yet. The data are written in real-time to S3, but are not available for querying in real-time.
  - We could write a custom Apache Beam I/O connector that would write data via a metastore.
  - We could re-write the application as a Flink Job that writes data with the [Flink Hive connector](https://github.com/apache/flink-connector-hive).
- The data are written in a row-based format (Avro), which will be less performant for read-heavy analytical workloads than a columnar format like Parquet. For example, queries on Avro formatted data can not take advantage of column pruning at query-time.
  - We could either:
    1. Write a custom Apache Beam I/O connector for Iceberg; or,
    2. Re-write the application as a Flink Job that uses the [Flink Iceberg connector](https://iceberg.apache.org/docs/latest/).
  - With Iceberg, we can handle data format conversion from Avro to Parquet more easily without downtime. We might also choose to write to Parquet format and compact many small Parquet files to fewer large Parquet files to analytical improve query performance.
- We consider the test data to include all possible schemas for form and field entity types. If a new field or form contains backwards-compatible schema changes, we do not handle writing the data.
  - We could write data that produces an error on write to a dead-letter queue and write data in S3 to Iceberg format. In the event the dead-letter queue becomes populated, we could make backwards-compatible schema changes to the destination table and then re-run the pipeline for data in the dead-letter queue.
- Enriching the data in a ParDo(DoFn) Apache Beam transformation could create a performance bottleneck.
  - We could write the app as a Scala/Java Flink Job that leverages the Flink AsyncIO Operator, which would reduce the performance hit of many parallel external API calls from the app runtime.

### Design Choices & Reasoning

#### App architecture

- The app is an Apache Beam app written with the Apache Beam Python SDK.
  - Python is probably the most common language used among data engineers.
    - The Python SDK reduces the onboarding time we might incur from onboarding Scala or Java-naive team members.
  - Apache Beam apps can be run in many environments.
    - Easy end-to-end testing.
    - Many production deployment options (like the DataflowRunner, FlinkRunner, SparkRunner, and so on).
  - Apache Beam apps provide a `TestPipeline` for testing pipeline transformations.
    - Easy unit testing.
- The app writes data to Avro, a row-based format.
  - Allows appending to an output file, preventing the many small files problem in a streaming context.
  - Enforces a schema on-write, unlike JSON-lines or CSV writes.

#### Data Modelling

- We write two tables for form and field entity types from the API and enrich the field data with form metadata. Both form and field entity types are enriched with event metadata from form.events, which indicate the type of action that triggered the data update and resulted in the current form or field data.
  - Denormalized "One Big Table"-style modelled data is easier to query for downstream analytics.
  - The field entity type table actually contains all data. The form entity type table is there to reduce the amount of data processed when analytical queries do not need field data to answer questions.
- We 'unnest' nested JSON fields to top-level columns when possible.
  - SELECTing JSON column data in analytical queries is not easily readable or particularly usable for downtream data consumers (and, less importantly, can be a performance issue).
