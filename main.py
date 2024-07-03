import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import schedule
import socket
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv
from win10toast import ToastNotifier
import time
from getpass import getpass

load_dotenv()

global USERNAME, PASSWORD
USERNAME = None
PASSWORD = None
LOGIN_URL = "https://neosia.unhas.ac.id/login"  
MEMORY_FILE = "initial_sks.txt"

def check_sks_update(url, initial_sks):
    print(f"Starting SKS check process...")
    driver = None
    try:
        # Set up web driver
        service = Service(ChromeDriverManager().install())
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        

        print(f"Navigating to login page: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        
        try:
            username_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = driver.find_element(By.ID, "password")
            submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            print("Login form loaded successfully")
            
            username_field.send_keys(USERNAME)
            password_field.send_keys(PASSWORD)
            submit_button.click()
            print("Login form submitted")
            
            # Wait for redirect to home page
            WebDriverWait(driver, 30).until(
                EC.url_to_be("https://neosia.unhas.ac.id/")
            )
            print("Successfully logged in and redirected to home page")
            
            
            print(f"Navigating to transcript page: {url}")
            driver.get(url)
            
            # Wait for the transcript page to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Transcript page loaded")

            time.sleep(10)

            # Try to find the SKS element
            try:
                sks_element = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Total SKS dilulusi')]"))
                )
                print(f"SKS element found: {sks_element.text}")
                
                sks_text = sks_element.text.split()[-1]
                try:
                    current_sks = int(sks_text)
                    print(f"Current SKS: {current_sks}")
                    if current_sks != initial_sks:
                        print("SKS has changed!")
                        return current_sks
                    else:
                        print("SKS has not changed.")
                except ValueError:
                    print(f"Error converting SKS text to integer: {sks_text}")
            except TimeoutException:
                print("Timeout waiting for SKS element to load")
                print(f"Current URL: {driver.current_url}")
        
        except TimeoutException:
            print("Timeout waiting for login form to load")
            print(f"Current URL: {driver.current_url}")
        
    except WebDriverException as e:
        print(f"WebDriver error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    finally:
        # Close the browser if it was created
        if driver:
            try:
                driver.quit()
                print("Browser closed successfully")
            except Exception as e:
                print(f"Error closing browser: {e}")
    
    return None

def send_windows_notification(new_sks):
    toaster = ToastNotifier()
    
    print(f"Sending Windows notification for SKS update: {new_sks}")
    
    try:
        toaster.show_toast(
            "SKS Update",
            f"Your total SKS has been updated to {new_sks}",
            duration=10,
            icon_path=None,
            threaded=True
        )
        # Wait for threaded notification to finish
        while toaster.notification_active():
            time.sleep(0.1)
        print("Windows notification sent successfully.")
    except Exception as e:
        print(f"Error sending Windows notification: {e}")

def send_notification(new_sks):
    send_windows_notification(new_sks)

def get_initial_data():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            lines = f.readlines()
            if len(lines) == 3:
                return lines[0].strip(), lines[1].strip(), int(lines[2].strip())
    return None, None, None

def save_initial_data(username, password, sks):
    with open(MEMORY_FILE, 'w') as f:
        f.write(f"{username}\n{password}\n{sks}")

def is_internet_available():
    try:
        # Attempt to connect to a reliable server (Google's DNS)
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False 
    


def get_next_hour():
    singapore_tz = pytz.timezone('Asia/Singapore')
    now = datetime.now(singapore_tz)
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return next_hour

def main():
    global USERNAME, PASSWORD
    url = "https://neosia.unhas.ac.id/transkrip-nilai"
    username, password, initial_sks = get_initial_data()
    
    print("Starting SKS monitoring program...")
    print(f"Monitoring URL: {url}")
    
    if initial_sks is None:
        print("First-time run detected. Please enter your credentials.")
        USERNAME = input("Enter your username: ")
        PASSWORD = getpass("Enter your password: ")  # Make sure to import getpass
        print("Checking initial SKS...")
        initial_sks = check_sks_update(url, 0)
        if initial_sks:
            print(f"Initial SKS: {initial_sks}")
            save_initial_data(USERNAME, PASSWORD, initial_sks)
        else:
            print("Failed to get initial SKS. Exiting.")
            return
    else:
        USERNAME = username
        PASSWORD = password
    
    print(f"Initial SKS: {initial_sks}")
    
    def job():
        nonlocal initial_sks
        if is_internet_available():
            print("\nChecking for SKS updates...")
            new_sks = check_sks_update(url, initial_sks)
            if new_sks and new_sks != initial_sks:
                print(f"New SKS detected: {new_sks}")
                send_notification(new_sks)
                initial_sks = new_sks
                save_initial_data(USERNAME, PASSWORD, new_sks)
            else:
                print("No SKS update found.")
        else:
            print("No internet connection. Skipping check.")

    # Run the job immediately
    job()

    # Schedule the job to run at the top of every hour
    next_hour = get_next_hour()
    time_until_next_hour = (next_hour - datetime.now(pytz.timezone('Asia/Singapore'))).total_seconds()
    
    print(f"Next check scheduled for: {next_hour}")
    
    time.sleep(time_until_next_hour)
    schedule.every().hour.at(":00").do(job)

    #is internet avaliable?
    while True:
        if is_internet_available():
            schedule.run_pending()
        else:
            print("No internet connection. Waiting...")
        time.sleep(60)

# run main program
main()