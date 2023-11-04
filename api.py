from datetime import datetime

from fastapi import FastAPI, Response

app = FastAPI()

data = [
    {
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
]


@app.get("/{id}")
async def read_item(id: str, response: Response):
    response.headers["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    for payload in data:
        if payload["id"] == id:
            return payload
