from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.expected_conditions import invisibility_of_element_located
import time
import threading
from queue import Queue

max_simultaneous_profiles = 3
metamask_url = "chrome-extension://cfkgdnlcieooajdnoehjhgbmpbiacopjflbjpnkm/home.html#"
chrome_driver_path = Service("C:\\you\\personal\\path\\to\\chromedriver-win-x64.exe")


start_idx = int(input("Enter the starting index of the profile range: "))
end_idx = int(input("Enter the ending index of the profile range: "))

with open("config\\profile_ids.txt", "r") as file:
    profile_ids = [line.strip() for line in file.readlines()]
with open("config\\seed_phrases.txt", "r") as file:
    seed_phrases = [line.strip() for line in file.readlines()]
with open("config\\passwords.txt", "r") as file:
    passwords = [line.strip() for line in file.readlines()]

def click_if_exists(driver, locator, by=By.XPATH):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((by, locator))
            )
            WebDriverWait(driver, 10).until(
                invisibility_of_element_located((By.CSS_SELECTOR, ".loading-overlay"))
            )

            element.click()
            return True
        except TimeoutException:
            return False
        except StaleElementReferenceException:
            attempts += 1
            time.sleep(3)
    return False
def enter_password(driver, password):
    password_input = WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))
    )
    password_input.send_keys(password)

    confirm_password_input = WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="confirm-password"]'))
    )
    confirm_password_input.send_keys(password)
def worker():
    while True:
        idx, profile_id = task_queue.get()
        if profile_id is None:
            break
        seed_phrase = seed_phrases[idx - 1]
        password = passwords[idx - 1]
        process_profile(idx, profile_id, seed_phrase, password)
        task_queue.task_done()
def process_profile(idx, profile_id, seed_phrase, password):

    print(f"Opening ID {idx}: {profile_id}")
    req_url = f'http://localhost:3001/v1.0/browser_profiles/{profile_id}/start?automation=1'
    response = requests.get(req_url)
    response_json = response.json()
    print(response_json)
    port = str(response_json['automation']['port'])
    options = webdriver.ChromeOptions()
    options.debugger_address = f'127.0.0.1:{port}'
    driver = webdriver.Chrome(service=chrome_driver_path, options=options)
    initial_window_handle = driver.current_window_handle

    driver.get(metamask_url)
    try:
        for tab in driver.window_handles:
            if tab != initial_window_handle:
                driver.switch_to.window(tab)
                driver.close()
        driver.switch_to.window(initial_window_handle)
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div/button')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div/div[5]/div[1]/footer/button[2]')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div[2]/div/div[2]/div[1]/button')
        seed_words = seed_phrases[idx - 1].split()
        for i, word in enumerate(seed_words):
            seed_word_input = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="import-srp__srp-word-{i}"]')))
            seed_word_input.send_keys(word)
        enter_password(driver, passwords[idx - 1])
        click_if_exists(driver, '//*[@id="create-new-vault__terms-checkbox"]')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div[2]/form/button')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/button')
        click_if_exists(driver, '/html/body/div[3]/div/div[2]/div/div[1]/button')
        time.sleep(3)
        driver.close()
    except Exception as e:
        print(f"L: {e}")
        driver.quit()

task_queue = Queue(max_simultaneous_profiles)
threads = []

for _ in range(max_simultaneous_profiles):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

for idx, profile_id in zip(range(start_idx, end_idx + 1), profile_ids[start_idx - 1:end_idx]):
    task_queue.put((idx, profile_id))
    time.sleep(5)

task_queue.join()

for _ in range(max_simultaneous_profiles):
    task_queue.put((None, None))

for t in threads:
    t.join()