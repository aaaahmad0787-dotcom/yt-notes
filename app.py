from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import requests
import re
import os

app = Flask(__name__)
CORS(app)

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

def fetch_transcript(video_id, supadata_key):
    url = f"https://api.supadata.ai/v1/youtube/transcript?videoId={video_id}&text=true"
    headers = {"x-api-key": supadata_key}
    res = requests.get(url, headers=headers, timeout=30)

    if res.status_code == 404:
        raise Exception("Is video ka transcript nahi mila — dusri video try karo.")
    if res.status_code == 401:
        raise Exception("Supadata API key galat hai!")
    if res.status_code != 200:
        raise Exception(f"Transcript fetch nahi hua. Status: {res.status_code}")

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
        data         = request.get_json()
        url          = data.get('url', '').strip()
        groq_key     = data.get('apiKey', '').strip()
        supadata_key = data.get('supadataKey', '').strip()
        style        = data.get('style', 'bullet')

        if not url:
            return jsonify({'error': 'YouTube URL daalo!'}), 400
        if not groq_key:
            return jsonify({'error': 'Groq API key daalo!'}), 400
        if not supadata_key:
            return jsonify({'error': 'Supadata API key daalo!'}), 400

        video_id = get_video_id(url)
        if not video_id:
            return jsonify({'error': 'Valid YouTube URL nahi hai!'}), 400

        transcript = fetch_transcript(video_id, supadata_key)

        client = Groq(api_key=groq_key)
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are an expert study notes creator. Make clear, well-structured, student-friendly notes."},
                {"role": "user", "content": get_prompt(style, transcript)}
            ],
            max_tokens=1500,
            temperature=0.4
        )

        notes = completion.choices[0].message.content
        return jsonify({'notes': notes, 'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'running', 'message': 'YTNotes backend chal raha hai!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)