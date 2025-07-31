import os
import csv
import time
import uuid
import io
import threading
from flask import Flask, render_template, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor
import traceback
from datetime import datetime


UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

progress_map = {}
result_buffer_map = {}

def get_driver(headless=True):
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")  # Important for containers
    options.add_argument("--disable-dev-shm-usage")  # Important for containers
    options.add_argument("--disable-gpu")  # Optional but recommended in headless containers
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    service = Service(os.environ.get('CHROMEDRIVER_PATH', 'chromedriver'))
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def process_single_rego(rego, state):
    driver = get_driver(headless=True)  
    wait = WebDriverWait(driver, 20)
    output_row = []
    try:
        if state == 'act':
            driver.get("https://rego.act.gov.au/regosoawicket/public/reg/FindRegistrationPage?0")
            input_box = wait.until(EC.presence_of_element_located((By.ID, "plateNumber")))
            input_box.clear()
            input_box.send_keys(rego)
            wait.until(EC.element_to_be_clickable((By.ID, "privacyCheck"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "id3"))).click()
            time.sleep(2)
            try:
                vehicle_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'HOLDEN')]")))
                vehicle_option.click()
            except:
                output_row = [rego] + ["-"] * 14
            if not output_row:
                def get_val(id_):
                    try:
                        return driver.find_element(By.ID, id_).get_attribute("value").strip()
                    except:
                        return "-"
                output_row = [
                    get_val("plateNumber"), get_val("vehicleMake"), get_val("vehicleModel"),
                    get_val("vehicleColour"), get_val("manufacturingDate"), get_val("vinNumber"),
                    get_val("engineNumber"), get_val("gvm"), get_val("tareMass"), get_val("stolenIndicator"),
                    get_val("gvRating"), get_val("stolenPlateIndicator"), get_val("stolenEngineIndicator"),
                    get_val("regStatus"), get_val("operators")]

        elif state == 'qld':
            driver.get("https://www.service.transport.qld.gov.au/checkrego/application/TermAndConditions.xhtml")
            try:
                wait.until(EC.element_to_be_clickable((By.ID, "tAndCForm:confirmButton"))).click()
                time.sleep(1)
            except:
                pass
            input_box = wait.until(EC.presence_of_element_located((By.ID, "vehicleSearchForm:plateNumber")))
            input_box.clear()
            input_box.send_keys(rego)
            wait.until(EC.element_to_be_clickable((By.ID, "vehicleSearchForm:confirmButton"))).click()
            wait.until(EC.presence_of_element_located((By.ID, "j_id_61")))
            def get_info(label):
                try:
                    dt_element = driver.find_element(By.XPATH, f"//dt[normalize-space(text())='{label}']")
                    dd_element = dt_element.find_element(By.XPATH, "following-sibling::dd[1]")
                    return dd_element.text.strip()
                except:
                    return "-"
            output_row = [
                get_info("Registration number"),
                get_info("Vehicle Identification Number (VIN)"),
                get_info("Description"),
                get_info("Purpose of use"),
                get_info("Status"),
                get_info("Expiry")]
            wait.until(EC.element_to_be_clickable((By.ID, "j_id_61:searchAgain"))).click()

        elif state == 'nsw':
            driver.get("https://check-registration.service.nsw.gov.au/frc?isLoginRequired=true")
            try:
                checkbox = wait.until(EC.presence_of_element_located((By.ID, "termsAndConditions")))
                driver.execute_script("arguments[0].click();", checkbox)
                time.sleep(1)
            except:
                pass
            input_box = wait.until(EC.presence_of_element_located((By.ID, "plateNumberInput")))
            input_box.clear()
            input_box.send_keys(rego)
            search_btn = wait.until(EC.element_to_be_clickable((By.ID, "id-2")))
            driver.execute_script("arguments[0].click();", search_btn)
            time.sleep(3)
            try:
                plate = driver.find_element(By.CSS_SELECTOR, "h2.heading-2").text.strip()
            except:
                plate = rego

            def get_info(label):
               try:
                    return driver.find_element(By.XPATH, f"//div[text()='{label}']/following-sibling::div[1]").text.strip()
               except:
                    return "-"

            output_row = [
                plate,
                get_info("Make"), get_info("Model"), get_info("Variant"),
                get_info("Colour"), get_info("Shape"), get_info("Manufacture year"),
                get_info("Tare weight"), get_info("Gross vehicle mass"),
                get_info("Registration concession"), get_info("Condition codes")
          ]


        elif state == 'wa':
            driver.get("https://online.transport.wa.gov.au/webExternal/registration/?0")
            wait.until(EC.presence_of_element_located((By.ID, "id1"))).send_keys(rego)
            wait.until(EC.element_to_be_clickable((By.ID, "id4"))).click()
            time.sleep(3)
            def get_cell(label):
                try:
                    return driver.find_element(By.XPATH, f"//td[text()='{label}']/following-sibling::td/span").text.strip()
                except:
                    return "-"
            output_row = [
                rego,
                get_cell("Make"),
                get_cell("Model"),
                get_cell("Year"),
                get_cell("Colour"),
                get_cell("This vehicle licence expires on")]

        elif state == 'nt':
            driver.get("https://nt.gov.au/driving/rego/existing-nt-registration/rego-check")
            input_box = wait.until(EC.presence_of_element_located((By.ID, "rego")))
            input_box.clear()
            input_box.send_keys(rego)
            wait.until(EC.element_to_be_clickable((By.ID, "search"))).click()
            wait.until(EC.presence_of_element_located((By.ID, "search-result")))
            time.sleep(2)
            def get_text(label):
                try:
                    return driver.find_element(By.XPATH, f"//p[strong[text()='{label}']]/following::p[1]").text.strip()
                except:
                    return "-"
            plate = rego
            make = get_text("Make")
            model = get_text("Model & Year")
            status = get_text("Status")
            expiry = get_text("Expiry")
            output_row = [rego, plate, status, expiry, make, model]

        else:
            output_row = [rego] + ["-"] * 15

    except Exception:
        columns_map = {'act': 14, 'qld': 5, 'nsw': 10, 'wa': 5, 'nt': 5}
        dash_count = columns_map.get(state, 15)
        output_row = [rego] + ["-"] * dash_count
       
    finally:
        driver.quit()

    return output_row

def get_header(state):
    headers = {
        'act': "Plate Number,Make,Model,Colour,Manufacture Date,VIN,Engine Number,GVM,Tare Mass,Stolen VIN,CO2 Emissions,Stolen Plate,Stolen Engine,Reg Status,No. of Operators\n",
        'qld': "Registration Number,VIN,Description,Purpose,Status,Expiry\n",
        'nsw': "Plate,Make,Model,Variant,Colour,Shape,Manufacture Year,Tare Weight,GVM,Concession,Condition Codes\n",
        'wa': "Plate,Make,Model,Year,Colour,Expiry\n",
        'nt': "Input Rego,Plate,Status,Expiry,Make,Model\n"
    }
    return headers.get(state, "")

def safe_process_single_rego(args):
    rego, state = args
    try:
        return process_single_rego(rego, state)
    except Exception:
        columns_map = {'act': 14, 'qld': 5, 'nsw': 13, 'wa': 5, 'nt': 5}
        dash_count = columns_map.get(state, 15)
        return [rego] + ["-"] * dash_count

def process_with_progress(filepath, state, task_id):
    try:
        with open(filepath, 'r') as f:
            regos = [line.strip() for line in f if line.strip()]
        total = len(regos)

        buffer = io.StringIO()
        buffer.write(get_header(state))

        max_workers = 2

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(safe_process_single_rego, [(rego, state) for rego in regos])

            for i, row in enumerate(results, 1):
                buffer.write(",".join(row) + "\n")
                progress_map[task_id] = int((i / total) * 100)
                time.sleep(0.1)

        result_buffer_map[task_id] = buffer.getvalue()
        buffer.close()
        progress_map[task_id] = 100

    except Exception as e:
        print(f"Error in process_with_progress: {e}")
        progress_map[task_id] = 100

@app.route('/')
def index():
    return render_template('index.html', year=datetime.now().year)

@app.route('/progress/<task_id>')
def progress(task_id):
    return jsonify({"progress": progress_map.get(task_id, 0)})

@app.route('/download/<task_id>')
def download(task_id):
    result = result_buffer_map.get(task_id)
    if result:
        return send_file(
            io.BytesIO(result.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='result.csv'
        )
    return "Result not ready", 404

@app.route('/start', methods=['POST'])
def start():
    file = request.files['file']
    state = request.form['state']
    task_id = str(uuid.uuid4())
    progress_map[task_id] = 0

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{file.filename}")
    file.save(filepath)

    thread = threading.Thread(target=process_with_progress, args=(filepath, state, task_id))
    thread.start()

    return jsonify({"task_id": task_id})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
