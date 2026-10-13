# How to Connect Lovable App (`queue-wiz-home.lovable.app`) to the Backend

Follow these 3 simple steps to connect your Lovable web app to your Python or Java backend:

---

### Step 1: Run or Deploy Your Backend

#### Option A: Running Locally with ngrok (Quickest for Testing)
1. Run the Python backend:
   ```powershell
   cd C:\Users\Asus\.gemini\antigravity\scratch\bank_queue_backend\python_backend
   py run_server.py
   ```
2. In a second terminal, open a public HTTPS tunnel with ngrok (or localtunnel):
   ```bash
   ngrok http 8000
   ```
   Copy the public URL (e.g., `https://abcd-1234.ngrok-free.app`).

#### Option B: Deploy Free to Cloud (Render / Railway)
- Push `bank_queue_backend/python_backend` or `java_backend` to GitHub.
- Deploy to Render as a Web Service:
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `python run_server.py`
  - You will get a free URL like: `https://bank-queue-api.onrender.com`.

---

### Step 2: Copy-Paste this Prompt into Lovable

Open your Lovable project dashboard (`https://lovable.dev/projects/...` for `queue-wiz-home.lovable.app`) and paste this prompt:

```text
Connect our frontend application to our REST API backend running at:
[INSERT YOUR BACKEND URL, e.g. https://bank-queue-api.onrender.com]

Please update the following components to use real backend API calls:

1. Services Page & Dropdowns (/services & /get-token):
   - Fetch available services from GET /api/v1/services
   - Populate service list dynamically with id, name, estimated time, and prefix.

2. Book Token Form (/get-token):
   - On submit, send POST to /api/v1/tokens/book with:
     { customer_name, customer_phone, customer_email, customer_account_number, service_id, booking_date, time_slot }
   - Show booking confirmation modal with the returned token_number, assigned desk_label, estimated_wait_minutes, and recommended_arrival_time.

3. Live Queue Page (/live-queue):
   - Fetch live queue status from GET /api/v1/queue/live
   - Display real counters with current serving token, waiting count, and recent update ticker.
   - Poll every 5 seconds or connect to WebSocket at /ws for live updates.

4. Check Token Page (/check-token):
   - On entering token number (e.g., A108), call GET /api/v1/tokens/track/{token_number}
   - Display real-time position, people ahead, counter assigned, estimated wait, and arrival notice.

5. Contact Page (/contact):
   - On submit, POST { name, email, message } to /api/v1/contact.

Please enable full error handling and loading indicators on all forms.
```

---

### Step 3: Done!
Lovable will automatically update the code to make live fetch calls to your backend API.
Tokens booked from home on Lovable will now persist in the database, calculate live wait times, and update the Live Queue in real time!
