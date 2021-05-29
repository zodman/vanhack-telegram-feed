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
db_file = f"sqlite:///{BASE}/db_relocationjobs.sqlite3"
telegram_conf = "telegram-send-relocationjobs.conf"
baseurl = "https://www.relocationjobs.net/?s=python"
message_tmp = [
        "👉 [$position_name]($url) created at *$post_date*",
        "Description:",
        "    $description",
        "Location: $country $flag #$city",
    ]


def send_message():
    db = dataset.connect(db_file)
    table = db["records"]
    records = table.find(was_sent=False, _limit=3)
    messages = []
    for i in records:
        full_job_msg_tmpl = "\n".join(message_tmp)
        job = i.copy()
        job.update({
            'flag': lookup(i["country"].upper()[0:2]),
            'description':
            textwrap.dedent(textwrap.shorten(job["description"], width=250))
        })
        res = Template(full_job_msg_tmpl).substitute(job)
        messages.append(res)
        i["was_sent"] = True
        table.update(i, ["position_name"])
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
    resp=requests.get(baseurl, timeout=10)
    page = BeautifulSoup(resp.content, features='html.parser')
    results = page.findAll('li',class_='job')
    for b in results:
        node = b.find("a")
        position_name = node.text
        curl = node["href"]
        newpage = BeautifulSoup(requests.get(curl).content, features="html.parser")
        content = newpage.find("div",class_="section_content").text
        data = content.strip().split("\n")
        country = data[0]
        company_name = data[1]
        city = data[2]
        description = "\n".join(data[3:])
        post_date = newpage.find("div", class_="date").text.strip()
        job = dict(position_name=position_name,
                   url=curl,
                   post_date=post_date,
                   city=city,
                   country=country,
                   was_sent=False,
                   description=description)
        table.insert_ignore(job, ['position_name'])


if __name__ == "__main__":
    fetch_jobs()
    send_message()
