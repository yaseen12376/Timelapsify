from flask import Flask, render_template_string

app = Flask(__name__)

# Copied template from app.py with time inputs added
TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Timelapsify - Generate Timelapse Videos (CORS Test)</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); padding: 40px; max-width: 600px; width: 100%; }
    h1 { color: #333; margin-bottom: 10px; font-size: 32px; text-align: center; }
    .subtitle { color: #666; text-align: center; margin-bottom: 30px; font-size: 14px; }
    .form-group { margin-bottom: 25px; }
    label { display: block; color: #555; font-weight: 600; margin-bottom: 8px; font-size: 14px; }
    input[type="date"], input[type="time"], input[type="number"], select { width: 100%; padding: 12px 16px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 15px; transition: all 0.3s; background: #fafafa; }
    input[type="date"]:focus, input[type="time"]:focus, input[type="number"]:focus, select:focus { outline: none; border-color: #667eea; background: white; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
    .quick-select { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
    .quick-btn { padding: 8px 16px; background: #f0f0f0; border: 1px solid #ddd; border-radius: 8px; cursor: pointer; font-size: 13px; transition: all 0.2s; color: #555; }
    .quick-btn:hover { background: #667eea; color: white; border-color: #667eea; }
    button[type="button"], button[type="submit"] { padding: 12px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; }
    button[type="submit"] { width: 100%; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; transition: transform 0.2s, box-shadow 0.2s; margin-top: 10px; }
    button[type="submit"]:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4); }
    .result { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 12px; border-left: 4px solid #667eea; display: none; }
    .result.show { display: block; animation: slideIn 0.3s ease; }
    .error { color: #dc3545; background: #ffe6e6; padding: 15px; border-radius: 8px; margin-top: 20px; display: none; }
    .error.show { display: block; }
    .loading { display: none; text-align: center; margin-top: 20px; color: #667eea; }
    .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .camera-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; }
    .camera-option { padding: 12px; background: #f8f9fa; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: center; transition: all 0.2s; font-weight: 500; }
    .camera-option.selected { background: #667eea; color: white; border-color: #667eea; }
    input[type="radio"] { display: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🎬 Timelapsify (CORS Test)</h1>
    <p class="subtitle">This runs on port 6000 and calls the main app on port 5000</p>

    <form id="timelapseForm">
      <div class="form-group">
        <label>📅 Date Range</label>
        <div class="quick-select">
          <button type="button" class="quick-btn" onclick="setRange('today')">Today</button>
          <button type="button" class="quick-btn" onclick="setRange('yesterday')">Yesterday</button>
          <button type="button" class="quick-btn" onclick="setRange('last7days')">Last 7 Days</button>
          <button type="button" class="quick-btn" onclick="setRange('last30days')">Last 30 Days</button>
          <button type="button" class="quick-btn" onclick="setRange('thisweek')">This Week</button>
          <button type="button" class="quick-btn" onclick="setRange('lastmonth')">Last Month</button>
        </div>
      </div>

      <div class="form-group">
        <label for="from_date">From Date</label>
        <input type="date" id="from_date" name="from_date" required>
      </div>
      <div class="form-group">
        <label for="from_time">From Time</label>
        <input type="time" id="from_time" name="from_time" value="00:00">
      </div>

      <div class="form-group">
        <label for="to_date">To Date</label>
        <input type="date" id="to_date" name="to_date" required>
      </div>
      <div class="form-group">
        <label for="to_time">To Time</label>
        <input type="time" id="to_time" name="to_time" value="23:59">
      </div>

      <div class="form-group">
        <label for="duration">⏱️ Duration (seconds)</label>
        <input type="number" id="duration" name="duration" min="1" max="300" value="10" required>
      </div>

      <div class="form-group">
        <label>📷 Select Camera</label>
        <div class="camera-grid">
          <label class="camera-option selected" onclick="selectCamera(this, 'camera1')">
            <input type="radio" name="camera" value="camera1" checked>
            camera1
          </label>
          <label class="camera-option" onclick="selectCamera(this, 'camera2')">
            <input type="radio" name="camera" value="camera2">
            camera2
          </label>
          <label class="camera-option" onclick="selectCamera(this, 'camera3')">
            <input type="radio" name="camera" value="camera3">
            camera3
          </label>
        </div>
      </div>

      <button type="submit">Send to Port 5000</button>
    </form>

    <div class="loading" id="loading">
      <div class="spinner"></div>
      <p>Sending request to port 5000...</p>
    </div>

    <div class="result" id="result"></div>
    <div class="error" id="error"></div>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', function() {
      const firstCamera = document.querySelector('.camera-option');
      if (firstCamera) firstCamera.classList.add('selected');
      setRange('today');
    });

    function selectCamera(element, camera) {
      document.querySelectorAll('.camera-option').forEach(opt => opt.classList.remove('selected'));
      element.classList.add('selected');
      element.querySelector('input').checked = true;
    }

    function setRange(range) {
      const today = new Date();
      let fromDate = new Date();
      let toDate = new Date();
      switch(range) {
        case 'today': fromDate = toDate = today; break;
        case 'yesterday': fromDate = toDate = new Date(today.setDate(today.getDate() - 1)); break;
        case 'last7days': fromDate = new Date(today.setDate(today.getDate() - 6)); toDate = new Date(); break;
        case 'last30days': fromDate = new Date(today.setDate(today.getDate() - 29)); toDate = new Date(); break;
        case 'thisweek': const dayOfWeek = today.getDay(); fromDate = new Date(today.setDate(today.getDate() - dayOfWeek)); toDate = new Date(); break;
        case 'lastmonth': fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1); toDate = new Date(today.getFullYear(), today.getMonth(), 0); break;
      }
      document.getElementById('from_date').value = formatDate(fromDate);
      document.getElementById('to_date').value = formatDate(toDate);
      // Reset default times for clarity
      document.getElementById('from_time').value = '00:00';
      document.getElementById('to_time').value = '23:59';
    }

    function formatDate(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }

    document.getElementById('timelapseForm').addEventListener('submit', async function(e) {
      e.preventDefault();
      document.getElementById('result').classList.remove('show');
      document.getElementById('error').classList.remove('show');
      document.getElementById('loading').style.display = 'block';

      const formData = new FormData(this);
      // Include time fields (server may ignore if unsupported)
      formData.append('from_time', document.getElementById('from_time').value);
      formData.append('to_time', document.getElementById('to_time').value);

      try {
        const response = await fetch('http://localhost:5000/generate', {
          method: 'POST',
          body: formData,
          // credentials: 'include' // enable if testing cookies with CORS
        });
        const data = await response.json();
        document.getElementById('loading').style.display = 'none';
        const result = document.getElementById('result');
        if (response.ok) {
          result.textContent = JSON.stringify(data, null, 2);
          result.classList.add('show');
        } else {
          const err = document.getElementById('error');
          err.textContent = data.error || 'An error occurred';
          err.classList.add('show');
        }
      } catch (error) {
        document.getElementById('loading').style.display = 'none';
        const err = document.getElementById('error');
        err.textContent = 'Failed to contact port 5000: ' + error.message;
        err.classList.add('show');
      }
    });
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET"]) 
def index():
  return render_template_string(TEMPLATE)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5001)
