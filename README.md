# form-etl

A locally tested Apache Beam pipeline that extracts messages from a Kafka topic, enriches them with an external API, models the data, and writes it to S3.

## Testing

See "Development Environment (MacOS)" to install Python and Poetry.

```zsh
poetry install --with dev
poetry run python -m unittest
```

## Quickstart

You'll need Docker installed and running. You also need the API endpoint available at hostname `internal.forms`, and an AWS S3 bucket with access keys.

See "Development Environment (MacOS)" to install Python and Poetry.

```zsh
# Start Kafka locally
docker-compose up --build -d

# Install Python dependencies
poetry install
# Run the Beam app
# This might not behave properly due to DirectRunner limitations with unbounded sources
poetry run python app.py \
    --runner=DirectRunner \
    --max_num_records=1 \
    --bootstrap_servers=localhost:9092
    # --field_form_output_path=s3://$BUCKET/form_field/ \
    # --form_event_output_path=s3://$BUCKET/form_event/ \
    # --s3_region_name=$AWS_REGION \
    # --s3_access_key_id=$AWS_ACCESS_KEY_ID \
    # --s3_secret_access_key=$AWS_SECRET_ACCESS_KEY
    # Uncomment the above for writing to S3!

# Download Kafka
curl https://packages.confluent.io/archive/7.3/confluent-community-7.3.2.tar.gz -o confluent-community-7.3.2.tar.gz
tar -xzf confluent-community-7.3.2.tar.gz

# Produce a message to Kafka topic form.events
echo 'test-key:{"form_id":"abcde","form_title":"my_test_form","event_happened_at":"2022-10-02 13:00:15","event_type":"created"}' | \
./confluent-7.3.2/bin/kafka-console-producer --broker-list localhost:9092 --topic form.events --property "parse.key=true" --property "key.separator=:"
```

## Data

### Kafka Topic

Kafka Topic `form.events` contains JSON encoded payloads like:

```json
{
    'form_id': 'abcde',
    'form_title': 'my_test_form',
    'event_happened_at': '2022-10-02 13:00:15',
    'event_type': 'created'
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
poetry run black form_etl/ tests/ app.py
poetry run isort form_etl/ tests/ app.py
poetry run flake8 --max-line-length 119 form_etl/ tests/ app.py
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
