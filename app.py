from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from groq import Groq
import re

app = Flask(__name__)
CORS(app)  # Frontend se requests allow karne ke liye

def get_video_id(url):
    # si parameter hata do pehle
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
    # Pehle English try karo, phir Hindi, phir jo bhi milega
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Auto-generated ya manual — jo bhi mile
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except:
            try:
                transcript = transcript_list.find_transcript(['hi'])
            except:
                # Koi bhi pehli language le lo
                transcript = next(iter(transcript_list))

        data = transcript.fetch()
        text = ' '.join([item['text'] for item in data])
        return text.strip()

    except TranscriptsDisabled:
        raise Exception("Is video mein captions completely disabled hain.")
    except NoTranscriptFound:
        raise Exception("Koi transcript nahi mila is video ke liye.")
    except Exception as e:
        raise Exception(f"Transcript error: {str(e)}")

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
        data = request.get_json()
        url     = data.get('url', '').strip()
        api_key = data.get('apiKey', '').strip()
        style   = data.get('style', 'bullet')

        # Basic validations
        if not url:
            return jsonify({'error': 'YouTube URL daalo bhai!'}), 400
        if not api_key:
            return jsonify({'error': 'Groq API key daalo!'}), 400
        if not api_key.startswith('gsk_'):
            return jsonify({'error': 'Sahi Groq API key daalo (gsk_ se shuru hogi)'}), 400

        video_id = get_video_id(url)
        if not video_id:
            return jsonify({'error': 'Valid YouTube URL nahi hai!'}), 400

        # Step 1: Transcript fetch karo
        transcript = fetch_transcript(video_id)
        if len(transcript) < 100:
            return jsonify({'error': 'Transcript bahut short hai, koi aur video try karo.'}), 400

        # Step 2: Groq se notes banao
        client = Groq(api_key=api_key)
        prompt = get_prompt(style, transcript)

        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert study notes creator. Make clear, well-structured, student-friendly notes."
                },
                {"role": "user", "content": prompt}
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
    app.run(debug=True, port=5000)
