import base64
import json
import requests

key = 'AIzaSyC7sBdTtPsQ7Zmnh3MUHzXBkSXgdmLlWm8'
url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}'

with open(r'c:\Users\stone\Desktop\workspace\ai_lecture_maker\static\avatar_square.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

prompt = """
This is a square 400x400 image of an English teacher.
Find the pixel coordinates [ymin, xmin, ymax, xmax] normalized from 0 to 1000 for:
1. face (the whole face)
2. mouth (the mouth region)
3. eyes (the eyes region)
4. Describe the teacher appearance.
Respond in JSON:
{
  "face": [ymin, xmin, ymax, xmax],
  "mouth": [ymin, xmin, ymax, xmax],
  "eyes": [ymin, xmin, ymax, xmax],
  "desc": "..."
}
"""

payload = {
    'contents': [{
        'parts': [
            {'text': prompt},
            {'inline_data': {'mime_type': 'image/png', 'data': b64}}
        ]
    }],
    'generationConfig': {'responseMimeType': 'application/json'}
}

res = requests.post(url, json=payload)
data = res.json()
print(data['candidates'][0]['content']['parts'][0]['text'])
