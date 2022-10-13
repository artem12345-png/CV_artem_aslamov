import httpx


# r = sess.post(zakaz_url, content=jdata.encode('utf-8'))
# jdata = json.dumps(d, ensure_ascii=False)
URL = "https://www.epool/xway/order/update"

# response = httpx.post(url=URL, json=payload)# json=jdata.encode('utf-8'))

with httpx.Client(timeout=40) as cl:
    r = cl.post(URL)
print(r.content)
