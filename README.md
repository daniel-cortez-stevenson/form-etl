# form-etl

A locally tested Apache Beam pipeline that extracts messages from a Kafka topic, enriches them with an external API, models the data, and writes it to S3.

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
# Start Kafka locally
docker-compose up -d

# Start the API locally
poetry run uvicorn api:app --reload

# Install Python dependencies
poetry install --with api

# Run the Beam app
# This might not behave properly if --max_num_records is None due to DirectRunner limitations with unbounded sources
poetry run python app.py \
    --runner=DirectRunner \
    --max_num_records=1 \
    --bootstrap_servers=localhost:9092 \
    --api_uri=http://localhost:8000
    # Uncomment the below for writing to S3!
    # --form_field_output_path=s3://$BUCKET/form_field/form_field \
    # --form_event_output_path=s3://$BUCKET/form_event/form_event \
    # --s3_region_name=$AWS_REGION \
    # --s3_access_key_id=$AWS_ACCESS_KEY_ID \
    # --s3_secret_access_key=$AWS_SECRET_ACCESS_KEY

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

Execute `ls` in the console to see the two output Avro files, which contain the same data as the JSON printed to the terminal.

```console
...
form_event-00000-of-00001.avro
form_field-00000-of-00001.avro
...
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
