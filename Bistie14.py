from flask import Flask, render_template_string, request
import requests

app = Flask(__name__)

# === CONFIG ===
API_KEYS = [
    "AIzaSyAbH0ipocrxzACCPubbhpSwgRrzXSx1cUs",
    "AIzaSyBAmhbXhUDOBmXsLL4bzbTmyyf7xSN_1fg",
    "AIzaSyCHmDO1_-XE7rKRwD8SwizJXLhLWQIRZdI",
    "AIzaSyChf9LMDwa2TGR_0JQVjZCP6I7E6rjbPvI"
]
CX = "85e8c9ede1eb54ef4"
YOUTUBE_API_KEY = "AIzaSyAbH0ipocrxzACCPubbhpSwgRrzXSx1cUs"

TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>The Future</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(-45deg, #ff9a00, #ffd000, #ff6a00, #ffca28);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
            color: #fff;
        }

        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .navbar {
            background-color: rgba(0, 0, 0, 0.7);
        }

        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }

        .image-grid a {
            display: block;
            width: 100%;
            aspect-ratio: 4 / 3;
            overflow: hidden;
            border-radius: 10px;
            background: #000;
        }

        .image-grid img.thumb {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 10px;
            transition: transform 0.3s ease;
        }

        .image-grid img.thumb:hover {
            transform: scale(1.05);
        }

        .result {
            background-color: rgba(0, 0, 0, 0.3);
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 8px;
        }

        a, h5 {
            color: #fff;
        }

        a:hover {
            color: #ffd000;
        }
    </style>
</head>
<body>
<nav class="navbar navbar-dark">
    <div class="container-fluid">
        <span class="navbar-brand mb-0 h1">🔍 The Future Search</span>
    </div>
</nav>
<div class="container mt-4">
    <form method="POST" class="mb-4">
        <div class="row g-2">
            <div class="col-md-5">
                <input type="text" name="query" class="form-control" placeholder="Search..." required>
            </div>
            <div class="col-md-2">
                <select name="type" class="form-select">
                    <option value="web">Web</option>
                    <option value="image">Images</option>
                    <option value="pdf">PDFs</option>
                    <option value="video">Videos</option>
                </select>
            </div>
            <div class="col-md-3">
                <input type="text" name="site" class="form-control" placeholder="Site (optional)">
            </div>
            <div class="col-md-2">
                <button class="btn btn-dark w-100">Search</button>
            </div>
        </div>
    </form>

    {% if results %}
        <p>{{ results|length }} results found.</p>
        {% if search_type == 'image' %}
            <div class="image-grid">
                {% for item in results %}
                    <a href="{{ item.link }}" target="_blank">
                        <img src="{{ item.image.thumbnailLink }}" class="thumb">
                    </a>
                {% endfor %}
            </div>
        {% elif search_type == 'video' %}
            <div class="row">
                {% for video in results %}
                    <div class="col-md-6 mb-4">
                        <div class="result">
                            <div class="ratio ratio-16x9">
                                <iframe src="https://www.youtube.com/embed/{{ video.id.videoId }}" allowfullscreen></iframe>
                            </div>
                            <h5 class="mt-2">{{ video.snippet.title }}</h5>
                            <p>{{ video.snippet.description }}</p>
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% else %}
            {% for item in results %}
                <div class="result">
                    <h5><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></h5>
                    <p>{{ item.snippet }}</p>
                    <small>{{ item.displayLink }}</small>
                </div>
            {% endfor %}
        {% endif %}
    {% endif %}
</div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    search_type = 'web'
    if request.method == 'POST':
        query = request.form['query']
        search_type = request.form['type']
        site = request.form.get('site', '').strip()

        if site:
            query += f" site:{site}"

        if search_type == 'pdf':
            query += " filetype:pdf"

        if search_type == 'video':
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&maxResults=100&type=video&key={YOUTUBE_API_KEY}"
            r = requests.get(url)
            if r.status_code == 200:
                results = r.json().get('items', [])
        else:
            for start in range(1, 100, 10):
                for api_key in API_KEYS:
                    url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={CX}&key={api_key}&start={start}"
                    if search_type == 'image':
                        url += "&searchType=image"
                    r = requests.get(url)
                    if r.status_code == 200:
                        items = r.json().get('items', [])
                        results.extend(items)
                        break

    return render_template_string(TEMPLATE, results=results, search_type=search_type)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
