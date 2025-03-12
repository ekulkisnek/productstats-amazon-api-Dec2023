# Imports
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import logging
from werkzeug.utils import secure_filename
import pandas as pd
import keepa
import json
import time

# Configuration
SETTINGS_FILE = 'settings.json'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
PASSCODE_ENABLED = False  # Set this to True to enable the passcode

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Global variable to store the Keepa API object
keepa_api = None
status = "Idle"  # Global status variable

# Utility Functions
def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {'rank': 0, 'monthly_sales': 0, 'sales_price': 0, 'email': '', 'text': ''}


def get_keepa_api():
    global keepa_api
    if keepa_api is None:
        api_key = os.getenv('KEEPA_API_KEY')  # Use environment variable
        if not api_key:
            logger.error("Keepa API key is missing or invalid.")
            return None
        try:
            keepa_api = keepa.Keepa(api_key)
        except Exception as e:
            logger.error(f"Error initializing Keepa API: {e}")
            keepa_api = None
            return None
    return keepa_api


def wait_for_tokens(tokens_per_minute=10):
    time.sleep(60 / tokens_per_minute)



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_file(uploaded_file):
    if not allowed_file(uploaded_file.filename):
        raise ValueError("Invalid file type. Please upload a CSV file.")
    filename = secure_filename(uploaded_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    uploaded_file.save(file_path)
    logger.info(f'File {filename} saved successfully')
    return filename, file_path

def process_csv_data(csv_path):
    api = get_keepa_api()
    if api is None:
        raise ValueError("Keepa API key is missing or invalid.")
    try:
        df = pd.read_csv(csv_path)
        results = []
        for index, row in df.iterrows():
            product_id = str(row.get('productId')).strip()  # Ensure product ID is a string
            if product_id:
                keepa_data = process_product_data(product_id, api)
                if keepa_data:
                    results.append({**row, **keepa_data})
                if index % 10 == 0:  # Save results every 10 products
                    save_results(results)
                wait_for_tokens()  # Wait to manage token limits
        save_results(results)  # Save final results
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise






def process_product_data(product_id, api, retries=3):
    attempt = 0
    while attempt < retries:
        try:
            products = api.query(product_id)
            if products:
                return extract_keepa_data(products[0])
        except Exception as e:
            attempt += 1
            logger.error(f"Error querying Keepa for product ID {product_id}, attempt {attempt}: {e}")
            time.sleep(2)  # Wait before retrying
    return None




def extract_keepa_data(product_data):
    try:
        product = product_data[0]  # Assuming single product response
        rank = product.get('salesRanks', {}).get('current', None)
        price = product.get('stats', {}).get('current', None)
        sales = calculate_monthly_sales(product.get('salesRanks', {}).get('day30', []))
        return {'rank': rank, 'price': price, 'monthly_sales': sales}
    except Exception as e:
        logger.error(f"Error extracting data from Keepa response: {e}")
        return None

def calculate_monthly_sales(sales_data):
    if not sales_data:
        return 0
    return sum(sales_data) // len(sales_data)

def save_results(results):
    results_df = pd.DataFrame(results)
    results_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results.csv')
    results_df.to_csv(results_path, index=False)
    logger.info(f'Results saved to {results_path}')

def filter_for_recent(results):
    return [result for result in results if 'recent' in result.get('date', '')]  # Replace with actual criteria

def filter_for_hits(results):
    return [result for result in results if result.get('sales', 0) > 100]  # Replace with actual criteria

def sort_results_data(results, sort_option):
    return sorted(results, key=lambda x: x.get('rank', 0), reverse=(sort_option == 'desc'))

# HTML Templates as Strings
common_style = '''
<style>
    body {
        font-family: 'Helvetica', sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
    }
    .container {
        width: 80%;
        text-align: center;
    }
    input[type="submit"], input[type="file"] {
        margin: 10px;
    }
</style>
'''

login_html = common_style + '''
<div class="container">
    <form method="post">
        Passcode: <input type="password" name="passcode"><br>
        <input type="submit" value="Login">
    </form>
</div>
'''

dashboard_html = common_style + '''
<div class="container">
    <h2>Dashboard</h2>
    <p id="statusMessage">{{ message }}</p>
    <a href="/settings">Settings</a> | <a href="/results">Results</a> | <a href="/history">History</a>
    <form action="/" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv">
        <input type="submit" value="Upload">
    </form>
</div>
'''

settings_html = common_style + '''
<div class="container">
    <h2>Settings</h2>
    <p id="statusMessage">{{ message }}</p>
    <form method="post">
        Keepa API Thresholds:<br>
        Rank: <input type="number" name="rank" min="0" value="{{ settings.rank }}"><br>
        Monthly Sales: <input type="number" name="monthly_sales" min="0" value="{{ settings.monthly_sales }}"><br>
        Sales Price: <input type="number" name="sales_price" min="0" value="{{ settings.sales_price }}"><br>
        Notification Settings:<br>
        Email: <input type="email" name="email" value="{{ settings.email }}"><br>
        Text: <input type="text" name="text" value="{{ settings.text }}"><br>
        <input type="submit" value="Save Settings">
    </form>
    <a href="/">Back to Dashboard</a>
</div>
'''

results_html = common_style + '''
<div class="container">
    <h2>Results</h2>
    <button onclick="showAll()">All</button>
    <button onclick="showRecentHits()">Recent Hits</button>
    <button onclick="showAllHits()">All Hits</button>
    <select id="sortSelect" onchange="sortResults()">
        <option value="asc">Ascending</option>
        <option value="desc">Descending</option>
    </select>
    <div id="resultsContent">
        <!-- Dynamic results will be loaded here -->
    </div>
    <a href="/">Back to Dashboard</a>
    <script>
    async function fetchData(url) {
        const response = await fetch(url);
        const data = await response.json();
        document.getElementById('resultsContent').innerHTML = generateTable(data);
    }

    function generateTable(data) {
        if (data.length === 0) {
            return '<p>No results found.</p>';
        }
        let table = '<table border="1"><tr>';
        for (let key in data[0]) {
            table += '<th>' + key + '</th>';
        }
        table += '</tr>';
        data.forEach(row => {
            table += '<tr>';
            for (let key in row) {
                table += '<td>' + row[key] + '</td>';
            }
            table += '</tr>';
        });
        table += '</table>';
        return table;
    }

    function showAll() {
        fetchData('/results/all');
    }

    function showRecentHits() {
        fetchData('/results/recent');
    }

    function showAllHits() {
        fetchData('/results/hits');
    }

    function sortResults() {
        const sortOption = document.getElementById('sortSelect').value;
        fetchData('/results/sort/' + sortOption);
    }

    showAll(); // Initial load
    </script>
</div>
'''




history_html = common_style + '''
<div class="container">
    <h2>History</h2>
    <!-- Display History Here -->
</div>
'''

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        passcode = request.form.get('passcode')
        if passcode == '1234':  # Replace '1234' with your desired passcode
            session['passcode'] = passcode
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(login_html, error='Invalid passcode')
    return render_template_string(login_html)

    status = "Idle"  # Global status variable

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    logger.info('Accessing dashboard')

    if not authenticate('1234'):
        logger.warning('Authentication failed')
        return redirect(url_for('login'))

    message = ''
    if request.method == 'POST':
        file = request.files.get('file')
        try:
            if file:
                filename, file_path = process_file(file)
                process_csv_data(file_path)
                message = "File processed successfully!"
            else:
                message = "No file uploaded."
        except ValueError as ve:
            message = f"Error: {str(ve)}"
            logger.error(f"Error processing file: {ve}")
        except Exception as e:
            message = f"Error: {str(e)}"
            logger.error(f"Error processing file: {e}")

    return render_template_string(dashboard_html, message=message)

# Add a route to check the current status
@app.route('/status')
def get_status():
    return jsonify({"status": status})




# Settings Route
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not authenticate('1234'):
        return redirect(url_for('login'))

    message = ''
    if request.method == 'POST':
        try:
            settings = {
                'rank': int(request.form.get('rank')),
                'monthly_sales': int(request.form.get('monthly_sales')),
                'sales_price': float(request.form.get('sales_price')),
                'email': request.form.get('email'),
                'text': request.form.get('text')
            }
            save_settings(settings)
            message = "Settings updated successfully!"
            logger.info('Settings updated')
        except Exception as e:
            message = f"Error updating settings: {e}"
            logger.error(f"Error updating settings: {e}")

    settings = load_settings()
    return render_template_string(settings_html, message=message, settings=settings)



@app.route('/history')
def history():
    if not authenticate('1234'):
        return redirect(url_for('login'))

    files = os.listdir(app.config['UPLOAD_FOLDER'])
    files_list = ''.join(f'<li>{file}</li>' for file in files)
    return render_template_string(history_html + '<ul>' + files_list + '</ul>')

@app.route('/results')
def results():
    results_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results.csv')
    try:
        if os.path.exists(results_path) and os.path.getsize(results_path) > 0:
            results_df = pd.read_csv(results_path)
            results_data = results_df.to_dict(orient='records')
        else:
            results_data = []
    except pd.errors.EmptyDataError:
        logger.error("No data found in results file.")
        results_data = []

    return render_template_string(results_html, results=results_data)

@app.route('/results/all')
def results_all():
    results_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results.csv')
    try:
        if os.path.exists(results_path):
            results_df = pd.read_csv(results_path)
            results_data = results_df.to_dict(orient='records')
        else:
            results_data = []
    except pd.errors.EmptyDataError:
        logger.error("No data found in results file.")
        results_data = []
    return jsonify(results_data)



@app.route('/results/recent')
def results_recent():
    results_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results.csv')
    if os.path.exists(results_path):
        results_df = pd.read_csv(results_path)
        results_data = filter_for_recent(results_df.to_dict(orient='records'))
    else:
        results_data = []
    return jsonify(results_data)

@app.route('/results/hits')
def results_hits():
    results_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results.csv')
    if os.path.exists(results_path):
        results_df = pd.read_csv(results_path)
        results_data = filter_for_hits(results_df.to_dict(orient='records'))
    else:
        results_data = []
    return jsonify(results_data)

@app.route('/results/sort/<sort_option>')
def results_sort(sort_option):
    results_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results.csv')
    if os.path.exists(results_path):
        results_df = pd.read_csv(results_path)
        results_data = sort_results_data(results_df.to_dict(orient='records'), sort_option)
    else:
        results_data = []
    return jsonify(results_data)

# Helper function for authentication
def authenticate(passcode):
    if not PASSCODE_ENABLED:
        return True
    return passcode and session.get('passcode') == passcode

# ------------------------
# Main
# ------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)