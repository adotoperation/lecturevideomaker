import urllib.request
import re

url = "https://www.youtube.com/watch?v=XF9ZB0T_q1A"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        m_title = re.search(r"<title>(.*?)</title>", html)
        if m_title:
            print("Title:", m_title.group(1))
        m_desc = re.search(r'"shortDescription":"(.*?)"', html)
        if m_desc:
            print("Description:", m_desc.group(1)[:300])
except Exception as e:
    print("Error:", e)
