import configparser
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
import sys


"""
TODO:
UPDATE> # Read tasks from articles_summary.csv only if are not "done", to know read row[11] for "done" only then add to the tasks list
FEATURE> NEW FUNCIONALLITY TO RUN THE SCRIPT FOREVER AND CHECK EVERY MINUTE IF THERE IS MORE TASKS IN articles_summary.csv THAT NEEDS TO BE ADDED TO tasks variable, make sure to not repeat tasks already loaded.
FEATURE> WHEN THE IMAGE GENERATION PROCESS IS DONE SAVE IN articles_summary.csv

"""

# Configuration variables
TIMEOUT = 9999999999990

# Read credentials from settings.conf
config = configparser.ConfigParser()
config.read("settings-midjourney.conf")
username = config.get("credentials", "username")
password = config.get("credentials", "password")

# Read tasks from articles_summary.csv if are not done
tasks = []
with open("articles_summary.csv", "r", newline="") as csvfile:
    reader = csv.reader(csvfile)
    next(reader, None)  # skip the header
    for row in reader:
        if len(row) >= 2 :  # Check if the row has at least 2 columns
            tasks.append({"title": row[0], "folder": row[1], "img1": row[7], "img2": row[8], "img3": row[9], "midPrompt": row[10]})
            print(tasks)

# Initialize Selenium WebDriver
driver = webdriver.Chrome()
driver.get("https://discord.com/login")

# Log in to Discord
WebDriverWait(driver, TIMEOUT).until(
    EC.element_to_be_clickable((By.NAME, "email"))
).send_keys(username)
driver.find_element(By.NAME, "password").send_keys(password + Keys.ENTER)

    
print("wait 10 after login.. ")
time.sleep(10)
print("end wait, redirigiendo")

# Go to the specified channel URL
channel_url = "https://discord.com/channels/@me/1061967475643789392"
driver.get(channel_url)
print("in position.")
print("roger. 15s wait.")
time.sleep(15)
print("comfirmed. end wait")

# Wait for the chat input to be clickable
chat_input_xpath = '/html/body/div[1]/div[2]/div/div[1]/div/div[2]/div/div[1]/div/div/div[3]/div[2]/main/form/div/div[1]/div/div[3]/div/div[2]'
print("Assigning chat input path.")
chat_input = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, chat_input_xpath)))
print("Roger that. Path assigned.")

# Iterate through tasks and send prompts

for task in tasks:
    time.sleep(5)
    print("sleep 5")
    
    prompt = task["midPrompt"]
    print(prompt)
    print("waiting 5")
    time.sleep(5)
    message = f"/imagine {prompt}"
    for char in message:
        chat_input.send_keys(char)
        time.sleep(0.001)  # Adjust the typing speed by changing the sleep time
    chat_input.send_keys(Keys.ENTER)
    print("Suenito de 20")
    time.sleep(20)
    print("lets go back to work...")

    # Wait for the new message in the chat wrapper
    chat_wrapper_xpath = '/html/body/div[1]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[3]/div[2]/main/div[1]/div/div/ol'
    chat_wrapper = WebDriverWait(driver, sys.maxsize).until(EC.presence_of_element_located((By.XPATH, chat_wrapper_xpath)))
    print("Chat wrapper found.")
    # Wait for the initial message to be deleted and replaced by the bot
    WebDriverWait(driver, sys.maxsize).until(
        lambda driver: len(driver.find_elements(By.XPATH, f"{chat_wrapper_xpath}/li")) > 1)
    # Save the element containing the buttons
    buttons_message_xpath = f"{chat_wrapper_xpath}/li"
    buttons_elements = driver.find_elements(By.XPATH, buttons_message_xpath)
    buttons_element = buttons_elements[-1]

    # Click the 3 buttons one after the other
    for i in range(1, 4):
        button_xpath = f'/html/body/div[1]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[3]/div[2]/main/div[1]/div/div/ol/li[{len(buttons_elements)}]/div/div[2]/div[2]/div[1]/div/button[{i}]'
        WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
        button = driver.find_element(By.XPATH, button_xpath)
        driver.execute_script("arguments[0].click();", button)
        print(f"Pressed button {i}")
        time.sleep(1)  # Add a delay between button clicks

    print("dreaming 10s")
    time.sleep(10)
    print("end dreaming")

    # Keep track of the number of messages in the chat wrapper
    current_messages_count = len(driver.find_elements(By.XPATH, f"{chat_wrapper_xpath}/li"))
    print("current_messages_count")
    print(current_messages_count)

    # Find the last 3 messages containing the image links
    image_urls = []
    for i in range(current_messages_count - 3, current_messages_count):
        link_xpath = f"{chat_wrapper_xpath}/li[{i + 1}]/div/div[3]/div[1]/div/div/div/div/div/a"
        link = driver.find_element(By.XPATH, link_xpath)
        image_url = link.get_attribute("href")
        if image_url not in image_urls:
            image_urls.append(image_url)
            print(f"Found image URL: {image_url}")

    # Save the images in the output folder
    for i, image_url in enumerate(image_urls):
        response = requests.get(image_url)
        if response.status_code == 200:
            image_name = f"{task[f'img{i+1}']}"
            with open(f"{task['folder']}/{image_name}", "wb") as output_file:
                output_file.write(response.content)
            print(f"Image {i + 1} saved as {image_name}")

    print("All tasks completed.")
driver.quit()

