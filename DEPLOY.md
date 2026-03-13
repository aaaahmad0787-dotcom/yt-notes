# YTNotes.ai — Deploy Guide (15 minute mein live!)

## Files structure
```
yt-notes-v2/
├── app.py           (Python Flask backend)
├── index.html       (Frontend)
├── requirements.txt (Python packages)
├── Procfile         (Railway ke liye)
└── DEPLOY.md        (yeh file)
```

---

## Step 1 — Apne laptop pe test karo (5 min)

```bash
# Terminal kholo, folder mein jao
cd yt-notes-v2

# Python packages install karo
pip install -r requirements.txt

# Backend chalaao
python app.py
```

Browser mein jao: http://localhost:5000/health
"YTNotes backend chal raha hai!" dikhega — matlab sab theek hai!

---

## Step 2 — GitHub pe daalo (3 min)

```bash
# Agar Git nahi hai toh: https://git-scm.com/downloads

git init
git add .
git commit -m "YTNotes first commit"
```

1. github.com pe jao → New Repository
2. Naam daalo: "yt-notes"
3. Public rakho
4. Yeh commands chalaao:
```bash
git remote add origin https://github.com/TERA_USERNAME/yt-notes.git
git push -u origin main
```

---

## Step 3 — Railway pe Backend Deploy karo (5 min)

1. railway.app pe jao
2. GitHub se login karo
3. "New Project" → "Deploy from GitHub repo"
4. Apna "yt-notes" repo select karo
5. Railway automatically detect karega Python app
6. Deploy button dabao
7. Thodi der mein URL milega — jaise: https://yt-notes-production.up.railway.app

### Railway pe Environment Variables set karo (optional but good):
Settings → Variables → Add:
- PORT = 5000

---

## Step 4 — Frontend mein Railway URL update karo

index.html kholo, line dhundho:
```js
const BACKEND = 'http://localhost:5000';
```

Isko badlo:
```js
const BACKEND = 'https://TERA-RAILWAY-URL.up.railway.app';
```

---

## Step 5 — Frontend Vercel pe deploy karo (2 min)

1. vercel.com pe jao, GitHub se login karo
2. "New Project" → "yt-notes" repo select karo
3. Root directory mein sirf index.html hai → Deploy
4. Done! Tera tool live hai.

---

## Done! Abhi yeh karo:

1. Tool open karo
2. Koi bhi YouTube lecture URL daalo
3. Groq API key daalo (console.groq.com se free)
4. "Notes Banao" dabao
5. SCREEN RECORD karo
6. Instagram reel banao: "Maine 18 saal mein yeh banaya" 🔥

---

## Common Errors aur Fix

**"ModuleNotFoundError"** → pip install -r requirements.txt dobara chalaao

**"Port already in use"** → python app.py --port 5001

**CORS error browser mein** → app.py mein CORS(app) already hai, theek hai

**Railway build fail** → requirements.txt check karo, sab packages hain?
