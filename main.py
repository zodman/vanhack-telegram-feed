import json
import requests
import dataset
from string import Template
import textwrap
from emojiflags.lookup import lookup
import tqdm
import requests
from telegram_send import send
import os

BASE = os.path.dirname(os.path.abspath(__file__))
db_file = f"sqlite:///{BASE}/db.sqlite3"
url = "https://api-vanhack-prod.azurewebsites.net/v1/job/search/full/"


def send_message():
    db = dataset.connect(db_file)
    table = db["records"]
    records = table.find(was_sent=False, _limit=3)
    message_tmp = [
        "👉 [$position_name]($url) created at *$post_date*",
        "$skills",
        "Description:",
        "    $description",
        "Location: #$country $flag #$city",
    ]
    messages = []
    for i in records:
        skills = " ".join([f"#{i}" for i in i.get("skills", []).split(",")])
        full_job_msg_tmpl = "\n".join(message_tmp)
        job = i.copy()
        job.update({
            'skills':
            skills,
            'flag':
            lookup(i["country"].upper()[0:2]),
            'description':
            textwrap.dedent(textwrap.shorten(job["description"], width=250))
        })
        res = Template(full_job_msg_tmpl).substitute(job)
        messages.append(res)
        i["was_sent"] = True
        table.update(i, ["id"])
    fullmessage = "\n".join(messages)
    if messages:
        conf = os.path.join(BASE, "telegram-send.conf")
        send(messages=messages, parse_mode="markdown", conf=conf)


def fetch_jobs():
    db = dataset.connect(db_file)
    db.create_table("records", primary_id="id")
    table = db["records"]
    results = []
    jobs = requests.get(url, params={'maxResultCount': 200}, timeout=10).json()
    for i in jobs.get("result").get("items"):
        id = i.get("id")
        position_name = i.get("positionName")
        description = i.get("description")
        city, country = i.get("city"), i.get("country")
        post_date = i.get("postDate")
        skills = [i.get("name") for i in i.get("mustHaveSkills")]
        u= "andresbernardovargasrodriguezandr"
        curl=f'https://vanhack.com/job/{id}?invite={u}'
        job = dict(position_name=position_name,
                   id=id,
                   url=curl,
                   post_date=post_date,
                   skills=",".join(skills),
                   city=city,
                   country=country,
                   was_sent=False,
                   description=description)
        table.insert_ignore(job, ['id'])


if __name__ == "__main__":
    fetch_jobs()
    send_message()
