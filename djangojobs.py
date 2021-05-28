import json
import requests
import dataset
from string import Template
import textwrap
from emojiflags.lookup import lookup
import tqdm
import requests
from bs4 import BeautifulSoup
from telegram_send import send
import os

BASE = os.path.dirname(os.path.abspath(__file__))
db_file = f"sqlite:///{BASE}/db_djangojobs.sqlite3"
telegram_conf = "telegram-send-djangojobs.conf"
baseurl = "https://djangojobs.net/jobs/"


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
        conf = os.path.join(BASE,telegram_conf) 
        send(messages=messages, parse_mode="markdown", conf=conf)

def cleanup(arr):
    return [i.strip() for i in arr]

def fetch_jobs():
    db = dataset.connect(db_file)
    db.create_table("records", primary_id="id")
    table = db["records"]
    results = []
    for page in range(10):
        resp=requests.get(url, params={'page': page}, timeout=10).json()
        page = BeautifulSoup(resp.content)
        blockquotes = page.findAll("blockquote")
        for b in blockquotes:
            position_name, company_name = b.text.strip().split('at')
            info = b.find_next_sibling()
            is_remote, relocation,  post_date = cleanup(info.text.split("|"))
            is_relocation, location =  cleanup(relocation.split(' \n\t'))
            city, country = location.split(",")
            skills = []
            description = info.find_next_sibling().text.strip()
            curl = baseurl + info.find_next_sibling().find('a')["href"]
            id = curl.split("/")[2]
            job = dict(position_name=position_name,
                       id = id,
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
