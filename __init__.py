import re
import sys
from datetime import datetime
from json.decoder import JSONDecodeError
from typing import List, Dict, Tuple, Sequence

import pytz
import requests

OUT_FILE = 'aaj_tak.txt'

IST = pytz.timezone('Asia/Kolkata')
PST = pytz.timezone('America/Los_Angeles')
WRITE_STEP = 5
URL = 'https://www.aajtak.in/ajax/search?id={}&type=all&path=/topic/hathras&key=hathras&site=aajtak'
DATETIME_OUT_FORMAT = r'%m-%d-%Y %H:%M'
LOWEST_VALID_TS = datetime(2020, 9, 25, 8, 26, tzinfo=IST)

"""Example:
<li> <a  title="हाथरस: पुलिस के साथ रात में जाने से पीड़ित परिवार का इनकार, अब सुबह लखनऊ के लिए होंगे रवाना" href="https://www.aajtak.in/india/uttar-pradesh/story/hathras-update-victim-family-to-leave-for-lucknow-tomorrow-morning-denies-going-with-police-at-night-1143761-2020-10-11" >
<div class="newimg"><img    title="हाथरस में पीड़ित परिवार के घर पर तैनात पुलिस (फोटो-पीटीआई)"    
class="lazyload "    src="https://akm-img-a-in.tosshub.com/aajtak/resource/img/default.png" data-src="https://akm-img-a-in.tosshub.com/aajtak/images/story/202010/up_police_0-sixteen_nine.jpg" alt="हाथरस में पीड़ित परिवार के घर पर तैनात पुलिस (फोटो-पीटीआई)" /></div> <div class="newcon-main"> <h2>हाथरस: पुलिस के साथ रात में जाने से पीड़ित परिवार का इनकार, अब सुबह लखनऊ के लिए होंगे रवाना</h2> <div class="newcon-main_innner_sec"> 
<ul> <li>Aaj Tak</li> <li>11 अक्टूबर 2020,</li> <li>अपडेटेड 17:40 IST</li> </ul> </div> </div> </a> </li>
"""
PATTERN = re.compile(
    (r'\s*(.*?)" href="https://www.aajtak.in/.*/(.*?)-\d*-(\d{4})-(\d*)-(\d*)" >.*?<ul> <li>Aaj Tak</li> <li>'
     r'\d*? .*? \d{4},</li> <li>अपडेटेड (\d\d):(\d\d) IST</li> </ul> </div> </div> </a> </li>'))
URL_PATTERN = re.compile(r'href="(.*)" >')


def title_filter(title: str) -> bool:
    english_keywords: List[str] = ['hathras']
    for keyword in english_keywords:
        if re.search(keyword, title, re.IGNORECASE):
            return True
    return False


def process_article(article: str) -> Tuple[datetime, str, str]:
    groups: Sequence[str] = PATTERN.match(article).groups()
    year = int(groups[2])
    month = int(groups[3])
    day = int(groups[4])
    hour = int(groups[5])
    minute = int(groups[6])
    timestamp: datetime = datetime(year, month, day, hour, minute, tzinfo=IST).astimezone(IST)
    title_en: str = groups[1]
    url = URL_PATTERN.search(article).group(1)
    # title_hi = groups[0]
    return timestamp, title_en, url


def process_page(search_id: int, lowest_valid_ts: datetime) -> Dict[datetime, Tuple[str, str]]:
    _datetime_to_title: Dict[datetime, Tuple[str, str]] = {}
    page = requests.get(URL.format(search_id)).json()['html_content']
    prefix = r'<li> <a  title="'
    for article in list(map(lambda _x: _x.strip(), page.split(prefix))):
        if article is None or len(article) == 0:
            continue
        ts, title, url = process_article(article)
        # Remove True form next condition to apply filtering
        if ts < lowest_valid_ts:
            continue
        if True or title_filter(title):
            _datetime_to_title[ts] = (title, url)
    return _datetime_to_title


def write_to_file(file_handle, _datetime_to_article):
    print("Writing {} articles to file".format(len(_datetime_to_article)))
    for date_time in sorted(_datetime_to_article, reverse=True):
        time_output = date_time.strftime(DATETIME_OUT_FORMAT)
        article = _datetime_to_article[date_time]
        file_handle.write("%s, %s, %s\n" % (time_output, article[0], article[1]))
    file_handle.flush()


f = open(OUT_FILE, 'w')
datetime_to_article: Dict[datetime, Tuple[str, str]] = {}
try:
    for x in range(sys.maxsize):
        new_articles = process_page(x, LOWEST_VALID_TS)
        datetime_to_article.update(new_articles)
        print("Finished processing of page {}. Found {} new articles leading to total {} articles.".format(x, len(
            new_articles), len(datetime_to_article)))
        if x % WRITE_STEP == 0:
            write_to_file(f, datetime_to_article)
except JSONDecodeError as e:
    print("JSONDecodeError: {0}".format(e))
write_to_file(f, datetime_to_article)
