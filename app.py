from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import requests
import re
import os
from datetime import datetime, date
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# API keys from environment variables
GROQ_API_KEY     = os.environ.get('GROQ_API_KEY')
SUPADATA_API_KEY = os.environ.get('SUPADATA_API_KEY')

# Rate limiting — 3 free notes per IP per day
usage_tracker = defaultdict(lambda: {'count': 0, 'date': str(date.today())})
FREE_LIMIT = 3

def check_rate_limit(ip):
    user = usage_tracker[ip]
    today = str(date.today())
    if user['date'] != today:
        user['count'] = 0
        user['date'] = today
    if user['count'] >= FREE_LIMIT:
        return False
    return True

def increment_usage(ip):
    usage_tracker[ip]['count'] += 1

def get_remaining(ip):
    user = usage_tracker[ip]
    today = str(date.today())
    if user['date'] != today:
        return FREE_LIMIT
    return max(0, FREE_LIMIT - user['count'])

def get_video_id(url):
    url = url.split('?si=')[0].split('&si=')[0]
    patterns = [
        r'(?:v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'(?:shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def fetch_transcript(video_id):
    url = f"https://api.supadata.ai/v1/youtube/transcript?videoId={video_id}&text=true"
    headers = {"x-api-key": SUPADATA_API_KEY}
    res = requests.get(url, headers=headers, timeout=30)

    if res.status_code == 404:
        raise Exception("Is video ka transcript nahi mila — dusri video try karo.")
    if res.status_code == 401:
        raise Exception("Supadata API error. Admin se contact karo.")
    if res.status_code != 200:
        raise Exception(f"Transcript fetch nahi hua. Dobara try karo.")

    data = res.json()
    transcript = data.get('content', '')
    if not transcript:
        raise Exception("Transcript empty hai — dusri video try karo.")
    return transcript

def get_prompt(style, transcript):
    prompts = {
        'bullet': """Create clear bullet-point study notes from this transcript.
Format:
## Topic
### Key Concepts
• Point 1
• Point 2
### Summary
2-3 line summary""",
        'detailed': """Create detailed study notes with explanations, definitions, examples, and key takeaways.
Use clear headings and paragraphs.""",
        'exam': """Create exam-ready notes.
Format:
## Topic
### Must Remember
• Critical points
### Definitions
### Formulas/Rules
### Likely Exam Questions
Q: ... A: ...
### Quick Revision""",
        'hinglish': """Hinglish mein notes banao — jaise dost samjha raha ho.
Format:
## Topic kya hai
### Main Points
• Simple explanation
### Yaad rakhne wali cheezein
### Ek line mein summary"""
    }
    style_prompt = prompts.get(style, prompts['bullet'])
    return f"{style_prompt}\n\nTRANSCRIPT:\n{transcript[:6000]}\n\nNotes:"

@app.route('/api/notes', methods=['POST'])
def generate_notes():
    try:
        # Get user IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        # Check rate limit
        if not check_rate_limit(ip):
            return jsonify({
                'error': 'limit_reached',
                'message': f'Aaj ke 3 free notes use ho gaye! Kal wapas aao ya Pro plan lo.',
                'remaining': 0
            }), 429

        data   = request.get_json()
        url    = data.get('url', '').strip()
        style  = data.get('style', 'bullet')

        if not url:
            return jsonify({'error': 'YouTube URL daalo!'}), 400

        video_id = get_video_id(url)
        if not video_id:
            return jsonify({'error': 'Valid YouTube URL nahi hai!'}), 400

        if not GROQ_API_KEY or not SUPADATA_API_KEY:
            return jsonify({'error': 'Server configuration error. Admin se contact karo.'}), 500

        # Fetch transcript
        transcript = fetch_transcript(video_id)

        # Generate notes
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert study notes creator. Make clear, well-structured, student-friendly notes."},
                {"role": "user", "content": get_prompt(style, transcript)}
            ],
            max_tokens=1500,
            temperature=0.4
        )

        notes = completion.choices[0].message.content

        # Increment usage
        increment_usage(ip)
        remaining = get_remaining(ip)

        return jsonify({
            'notes': notes,
            'success': True,
            'remaining': remaining
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usage', methods=['GET'])
def get_usage():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    return jsonify({'remaining': get_remaining(ip), 'limit': FREE_LIMIT})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'running', 'message': 'YTNotes backend chal raha hai!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)