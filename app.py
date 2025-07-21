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
import undetected_chromedriver as uc

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
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service("chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def process_state(filepath, state):    
    driver = get_driver()

    wait = WebDriverWait(driver, 20)

    with open(filepath, "r") as f:
        rego_list = [line.strip() for line in f if line.strip()]

    output_rows = []
   
    if state == 'act':
        output_rows.append([
            "Plate Number", "Make", "Model", "Colour", "Manufacture Date",
            "VIN", "Engine Number", "GVM", "Tare Mass", "Stolen VIN",
            "CO2 Emissions", "Stolen Plate", "Stolen Engine", "Reg Status",
            "No. of Operators"])
        driver.get("https://rego.act.gov.au/regosoawicket/public/reg/FindRegistrationPage?0")

        for rego in rego_list:
            try:
                input_box = wait.until(EC.presence_of_element_located((By.ID, "plateNumber")))
                input_box.clear()
                input_box.send_keys(rego)
                wait.until(EC.element_to_be_clickable((By.ID, "privacyCheck"))).click()
                wait.until(EC.element_to_be_clickable((By.ID, "id3"))).click()
                time.sleep(2)

                try:
                    vehicle_option = wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'HOLDEN')]")))
                    vehicle_option.click()
                except:
                    output_rows.append([rego] + ["-"] * 14)
                    driver.get("https://rego.act.gov.au/regosoawicket/public/reg/FindRegistrationPage?0")
                    continue

                def get_val(id):
                    try:
                        return driver.find_element(By.ID, id).get_attribute("value").strip()
                    except:
                        return "-"

                output_rows.append([
                    get_val("plateNumber"), get_val("vehicleMake"), get_val("vehicleModel"),
                    get_val("vehicleColour"), get_val("manufacturingDate"), get_val("vinNumber"),
                    get_val("engineNumber"), get_val("gvm"), get_val("tareMass"), get_val("stolenIndicator"),
                    get_val("gvRating"), get_val("stolenPlateIndicator"), get_val("stolenEngineIndicator"),
                    get_val("regStatus"), get_val("operators")])

                driver.get("https://rego.act.gov.au/regosoawicket/public/reg/FindRegistrationPage?0")

            except:
                output_rows.append([rego] + ["-"] * 14)

    elif state == 'qld':
        output_rows.append(["Registration Number", "VIN", "Description", "Purpose", "Status", "Expiry"])
        driver.get("https://www.service.transport.qld.gov.au/checkrego/application/TermAndConditions.xhtml")

        for rego in rego_list:
            try:
                try:
                    wait.until(EC.element_to_be_clickable((By.ID, "tAndCForm:confirmButton"))).click()
                    time.sleep(1)
                except:
                    pass

                wait.until(EC.presence_of_element_located((By.ID, "vehicleSearchForm:plateNumber"))).send_keys(rego)
                wait.until(EC.element_to_be_clickable((By.ID, "vehicleSearchForm:confirmButton"))).click()
                wait.until(EC.presence_of_element_located((By.ID, "j_id_61")))

                def get_info(label):
                    try:
                        dt_element = driver.find_element(By.XPATH, f"//dt[normalize-space(text())='{label}']")
                        dd_element = dt_element.find_element(By.XPATH, "following-sibling::dd[1]")
                        return dd_element.text.strip()
                    except:
                        return "-"

                output_rows.append([
                    get_info("Registration number"),
                    get_info("Vehicle Identification Number (VIN)"),
                    get_info("Description"),
                    get_info("Purpose of use"),
                    get_info("Status"),
                    get_info("Expiry")])

                again_btn = wait.until(EC.element_to_be_clickable((By.ID, "j_id_61:searchAgain")))
                again_btn.click()
            except:
                output_rows.append([rego] + ["-"] * 5)

    elif state == 'nsw':
        output_rows.append([
            "Plate", "Description", "VIN", "Expiry", "Make", "Model", "Variant", "Colour",
            "Shape", "Manufacture Year", "Tare Weight", "GVM", "Concession", "Condition Codes"])
        driver.get("https://check-registration.service.nsw.gov.au/frc?isLoginRequired=true")

        for rego in rego_list:
            try:
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
                    desc = driver.find_element(By.XPATH, "//p[contains(text(),'VIN/Chassis')]/preceding-sibling::p[1]").text.strip()
                    vin = driver.find_element(By.XPATH, "//p[contains(text(),'VIN/Chassis')]").text.split(":")[-1].strip()
                    expiry_el = driver.find_element(By.XPATH, "//strong[contains(text(),'Registration expires')]").text
                    expiry = expiry_el.replace("Registration expires:", "").strip()
                except:
                    plate = rego
                    desc = vin = expiry = "-"

                def get_info(label):
                    try:
                        return driver.find_element(By.XPATH, f"//div[text()='{label}']/following-sibling::div[1]").text.strip()
                    except:
                        return "-"

                output_rows.append([
                    plate, desc, vin, expiry,
                    get_info("Make"), get_info("Model"), get_info("Variant"),
                    get_info("Colour"), get_info("Shape"), get_info("Manufacture year"),
                    get_info("Tare weight"), get_info("Gross vehicle mass"),
                    get_info("Registration concession"), get_info("Condition codes")])

                driver.get("https://check-registration.service.nsw.gov.au/frc?isLoginRequired=true")
            except:
                output_rows.append([rego] + ["-"] * 13)

    elif state == 'wa':
        output_rows.append(["Plate", "Make", "Model", "Year", "Colour", "Expiry"])
        driver.get("https://online.transport.wa.gov.au/webExternal/registration/?0")

        for rego in rego_list:
            try:
                wait.until(EC.presence_of_element_located((By.ID, "id1"))).send_keys(rego)
                wait.until(EC.element_to_be_clickable((By.ID, "id4"))).click()
                time.sleep(3)

                def get_cell(label):
                    try:
                        return driver.find_element(By.XPATH, f"//td[text()='{label}']/following-sibling::td/span").text.strip()
                    except:
                        return "-"

                output_rows.append([
                    rego,
                    get_cell("Make"),
                    get_cell("Model"),
                    get_cell("Year"),
                    get_cell("Colour"),
                    get_cell("This vehicle licence expires on")])
            except:
                output_rows.append([rego] + ["-"] * 5)
    
    elif state == 'nt':
        output_rows.append(["Input Rego", "Plate", "Status", "Expiry", "Make", "Model"])
        driver.get("https://nt.gov.au/driving/rego/existing-nt-registration/rego-check")

        for rego in rego_list:
            try:
                input_box = wait.until(EC.presence_of_element_located((By.ID, "rego")))
                input_box.clear()
                input_box.send_keys(rego)

                search_btn = wait.until(EC.element_to_be_clickable((By.ID, "search")))
                search_btn.click()

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

                output_rows.append([rego, plate, status, expiry, make, model])

            except:
                output_rows.append([rego, rego, "-", "-", "-", "-"])


    driver.quit()

    result_file = os.path.join(OUTPUT_FOLDER, f"result_{uuid.uuid4().hex}.csv")
    with open(result_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(output_rows)

    return result_file

@app.route('/')
def index():
    return render_template('index.html')

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

def process_with_progress(filepath, state, task_id):
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        total = len(lines)

        buffer = io.StringIO()
        header_written = False

        for i, line in enumerate(lines):
            temp_file = os.path.join(UPLOAD_FOLDER, f"{task_id}_temp.csv")
            with open(temp_file, "w") as sf:
                sf.write(line + "\n")

            result_file = process_state(temp_file, state)
            with open(result_file, "r") as rf:
                rows = rf.readlines()
                if not header_written:
                    buffer.write(rows[0])
                    header_written = True
                if len(rows) > 1:
                    buffer.write(rows[1])

            progress_map[task_id] = int(((i + 1) / total) * 100)
            time.sleep(0.1)

        result_buffer_map[task_id] = buffer.getvalue()
        buffer.close()
        progress_map[task_id] = 100

    except Exception as e:
        print(f"Error: {e}")
        progress_map[task_id] = 100

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)