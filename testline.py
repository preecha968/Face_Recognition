import requests

LINE_NOTIFY_TOKEN = 'pMKUcLIdvfcH7I9A3tEjGS0MOc3AgdEXHUUtFqwEF8V'

"""Send a notification to LINE with an image."""
url = 'https://notify-api.line.me/api/notify'
headers = {'Authorization': f'Bearer {LINE_NOTIFY_TOKEN}'}

msg="hello world"
req=requests.post(url,headers=headers,data={'message':msg})
print(req)