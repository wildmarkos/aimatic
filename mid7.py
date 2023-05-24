import configparser
import csv
import time
import os
import sys
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from termcolor import colored


#todo los prints de list task despues de terminar una tarea esta mal, y no se estàn agregando a done,
# elimina la primera linea del csv
# revisar que si se puedan agregar tareas nuevas, se queda atorado en no new task found waiting 10 before checking again


# Set the working directory to the script's location
script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(script_directory)

# VARIABLES SECTION
TIMEOUT = 9999999999990
NUM_BUTTONS_PRESSED = 1
LOGIN_DELAY = 5
WAIT_AFTER_LOGIN = 15
BUTTON_DELAY = 3
WAIT_BETWEEN_PROMPTS = 5
WAIT_FOR_BOT_RESPONSE = 10
CHECK_NEW_TASKS_INTERVAL = 60
runInTerminal = "false"
log_file = "midjourney.log"


def log_to_console_and_file(message, color=None):
    with open(log_file, "a") as log:
        log.write(f"{message}\n")
    if color:
        print(colored(message, color))
    else:
        print(message)

def initialize_webdriver(run_in_terminal, username, password):
    if run_in_terminal == "true":
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
    else:
        driver = webdriver.Chrome()

    log_to_console_and_file("INITIALIZING...", "yellow")
    driver.get("https://discord.com/login")
    log_to_console_and_file("LOGGING...", "cyan")
    login_to_discord(driver, username, password)

    channel_url = "https://discord.com/channels/@me/1061967475643789392"
    log_to_console_and_file("Redirecting to channel.", "cyan")
    driver.get(channel_url)
    log_to_console_and_file("Redirected. 5s wait. to config path", "cyan")
    time.sleep(5)
    chat_input_xpath = '/html/body/div[1]/div[2]/div/div[1]/div/div[2]/div/div[1]/div/div/div[3]/div[2]/main/form/div/div[1]/div/div[3]/div/div[2]'
    chat_input = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, chat_input_xpath)))
    log_to_console_and_file("Chat input path assigned...", "cyan")
    log_to_console_and_file("Done initialization...", "yellow")

    return driver, chat_input

# Read credentials from settings.conf
def read_credentials():
    config = configparser.ConfigParser()
    config.read("settings-midjourney.conf")
    username = config.get("credentials", "username")
    password = config.get("credentials", "password")
    return username, password


# Read tasks from articles_summary.csv if they are not done
def load_tasks(existing_tasks):
    new_tasks = []
    lines = []
    log_to_console_and_file("leyendo tasks de csv file...", "cyan")
    with open(os.path.join(script_directory, "articles_summary.csv"), "r", newline="") as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader, None)  # Store the header

        for row in reader:
            if row == [] or row[11] == "done":
                lines.append(row)
                continue
            else:
                if row[11] == "" or row[11] == "pending":
                    row[11] = "pending"  # Set status to "pending" if it's empty
                new_task = {"title": row[0], "folder": row[1], "img1": row[7], "img2": row[8], "img3": row[9], "midPrompt": row[10], "done": row[11]}
                if not any(existing_task['title'] == new_task['title'] and existing_task['folder'] == new_task['folder'] for existing_task in existing_tasks):
                    new_tasks.append(new_task)
                lines.append(row)
                
                log_to_console_and_file("encontrado... "+ row[0], "cyan")
    lines.insert(0, header)
    # Write back to the CSV file
    with open(os.path.join(script_directory, "articles_summary.csv"), "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(lines)
    return new_tasks

    
def list_tasks(tasks):
    tasks_by_status = {"processing": [], "done": [], "pending": []}
    for task in tasks:
        status = task["done"]
        tasks_by_status[status].append(task["title"])  # Add the title to the appropriate list

    # Print tasks by status with colors, icons, and indices
    for status, task_list in tasks_by_status.items():
        if status == "processing":
            color = "yellow"
            icon = "🔄"
        elif status == "done":
            color = "green"
            icon = "✅"
        else:  # status == "pending"
            color = "red"
            icon = "⏳"

        print(colored(f"{icon} {status.upper()} TASKS:", color))
        for i, task_title in enumerate(task_list, start=1):
            print(colored(f"{i}. {task_title}", color))

    return tasks_by_status

# Log in to Discord
def login_to_discord(driver, username, password):
    driver.get("https://discord.com/login")

    log_to_console_and_file("LOGGIN IN.", "yellow")
    time.sleep(1)
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.NAME, "email"))
    ).send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password + Keys.ENTER)

    log_to_console_and_file(F"LOGGED IN. wait LOGIN_DELAY to continue.. ({LOGIN_DELAY})", "yellow")
    time.sleep(LOGIN_DELAY)
    log_to_console_and_file("DONE...", "yellow")


# Go to the specified channel URL
def go_to_channel(driver, channel_url):
    driver.get(channel_url)
    log_to_console_and_file("in position.", "yellow")
    log_to_console_and_file("roger. 15s wait.", "yellow")
    time.sleep(WAIT_AFTER_LOGIN)
    log_to_console_and_file("comfirmed. end wait", "yellow")
    
    # assign chat wrapper path
    chat_input_xpath = '/html/body/div[1]/div[2]/div/div[1]/div/div[2]/div/div[1]/div/div/div[3]/div[2]/main/form/div/div[1]/div/div[3]/div/div[2]'
    log_to_console_and_file("Assigning chat input path.", "yellow")
    chat_input = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, chat_input_xpath)))
    log_to_console_and_file("Path assigned.", "yellow")

def wait_for_image_url(driver, chat_wrapper_xpath, previous_messages_count):
    while True:
        current_messages_count = len(driver.find_elements(By.XPATH, f"{chat_wrapper_xpath}/li"))
        new_messages_count = current_messages_count - previous_messages_count

        if new_messages_count >= NUM_BUTTONS_PRESSED:
            image_urls = []
            for i in range(current_messages_count - NUM_BUTTONS_PRESSED, current_messages_count):
                link_xpath = f"{chat_wrapper_xpath}/li[{i + 1}]/div/div[3]/div[1]/div/div/div/div/div/a"
                link = driver.find_element(By.XPATH, link_xpath)
                image_url = link.get_attribute("href")
                if image_url not in image_urls:
                    image_urls.append(image_url)
                    log_to_console_and_file(f"Found image URL: {image_url}", "green")
            return image_urls

        time.sleep(1)

def process_tasks(driver, tasks, chat_input, current_task_index):
    # vars
    previous_messages_count = 0
    tasks_completed = 0


    # Iterate through tasks and send prompts
    while True:  # Continue processing while there are tasks in the list
        print("entro en while")

        # Check for new tasks every CHECK_NEW_TASKS_INTERVAL seconds
        log_to_console_and_file(f"Validation: CHECK_NEW_TASKS_INTERVAL: {CHECK_NEW_TASKS_INTERVAL}s ...", "yellow")
        time.sleep(CHECK_NEW_TASKS_INTERVAL)
        log_to_console_and_file("READING TASKS.........................................", "yellow")
        new_tasks = load_tasks(tasks)
        log_to_console_and_file("TASKS READED.........................................", "yellow")

        # If there are new tasks, add them to the list and continue processing
        if len(new_tasks) > 0:
            tasks.extend(new_tasks)
            log_to_console_and_file(f"New tasks found: {len(new_tasks)}. Processing new tasks...", "cyan")
            log_to_console_and_file(f"Total Tasks completed: {tasks_completed}", "green")

        # If there are no tasks to process, skip the rest of the loop
        if current_task_index >= len(tasks):
            log_to_console_and_file("No tasks to process. Waiting for new tasks...", "cyan")
            continue

            
        task = tasks[current_task_index]  # Always process the current task

        log_to_console_and_file("PROCESSING TASKS.................................", "yellow")
#old    for task in tasks:
        log_to_console_and_file("title: "+task["title"], "magenta")
        log_to_console_and_file("prompt: "+task["midPrompt"], "magenta")
        task["done"] = "processing"  # Set status to "processing" when starting the task
        list_tasks(tasks)
    
        
        log_to_console_and_file(f"(WAIT_BETWEEN_PROMPTS) {WAIT_BETWEEN_PROMPTS}", "yellow")
        time.sleep(WAIT_BETWEEN_PROMPTS)

        prompt = task["midPrompt"]
        log_to_console_and_file("waiting 5", "yellow") 
        time.sleep(WAIT_BETWEEN_PROMPTS)
        message = f"/imagine {prompt}"
        
        log_to_console_and_file("writing...", "yellow")
        for char in message:
            chat_input.send_keys(char)
            time.sleep(0.001)  # Adjust the typing speed by changing the sleep time
        time.sleep(1)
        chat_input.send_keys(Keys.ENTER)
        log_to_console_and_file("prompt sent...", "yellow")

        # Wait for the new message in the chat wrapper
        chat_wrapper_xpath = '/html/body/div[1]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[3]/div[2]/main/div[1]/div/div/ol'
        chat_wrapper = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, chat_wrapper_xpath)))
        log_to_console_and_file("Chat wrapper found.", "yellow")
        # Wait for the initial message to be deleted and replaced by the bot
        WebDriverWait(driver, TIMEOUT).until(
            lambda driver: len(driver.find_elements(By.XPATH, f"{chat_wrapper_xpath}/li")) > 1)
        # Save the element containing the buttons
        buttons_message_xpath = f"{chat_wrapper_xpath}/li"
        buttons_elements = driver.find_elements(By.XPATH, buttons_message_xpath)
        buttons_element = buttons_elements[-1]

        # Click the NUM_BUTTONS_PRESSED buttons one after the other
        for i in range(1, NUM_BUTTONS_PRESSED + 1):
            button_xpath = f'/html/body/div[1]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[3]/div[2]/main/div[1]/div/div/ol/li[{len(buttons_elements)}]/div/div[2]/div[2]/div[1]/div/button[{i}]'
            WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
            button = driver.find_element(By.XPATH, button_xpath)
            driver.execute_script("arguments[0].click();", button)
            log_to_console_and_file(f"Pressed button {i}", "green")
            time.sleep(BUTTON_DELAY)  # Add a delay between button clicks

        log_to_console_and_file("dreaming 10s..", "yellow")
        time.sleep(10)
        log_to_console_and_file("end dreaming.", "yellow")

        # Wait for the bot's response containing the image URLs
        log_to_console_and_file("Waiting for the bot's response...", "yellow")
        while True:
            # Keep track of the number of messages in the chat wrapper
            current_messages_count = len(driver.find_elements(By.XPATH, f"{chat_wrapper_xpath}/li"))
            new_messages_count = current_messages_count - previous_messages_count

            # Break the loop when there are enough new messages
            if new_messages_count >= NUM_BUTTONS_PRESSED:
                log_to_console_and_file("Bot's response received.", "green")
                break

            # Wait for a short period before checking again
            time.sleep(1)

        log_to_console_and_file("current_messages_count", "yellow")
        log_to_console_and_file(str(current_messages_count), "yellow")

        
        # Find the last 3 messages containing the image links
        image_urls = []
        for i in range(current_messages_count - NUM_BUTTONS_PRESSED, current_messages_count):
            link_xpath = f"{chat_wrapper_xpath}/li[{i + 1}]/div/div[3]/div[1]/div/div/div/div/div/a"
            link = driver.find_element(By.XPATH, link_xpath)
            image_url = link.get_attribute("href")
            if image_url not in image_urls:
                image_urls.append(image_url)
                log_to_console_and_file(f"Found image URL: {image_url}", "green")

        # Save the images in the output folder
        for i, image_url in enumerate(image_urls):
            response = requests.get(image_url)
            if response.status_code == 200:
                image_name = f"{task[f'img{i+1}']}"
                with open(f"{task['folder']}/{image_name}", "wb") as output_file:
                    output_file.write(response.content)
                log_to_console_and_file(f"Image {i + 1} saved as {image_name}", "green")

            # Mark the task as done in the articles_summary.csv file in the line that was the current task in row[11]
            with open(os.path.join(script_directory, "articles_summary.csv"), "r", newline="") as input_file:
                reader = csv.reader(input_file)
                lines = [line for line in reader]

            for row in lines:
                if row[0] == task['title'] and row[1] == task['folder']:
                    row[11] = "done"

            with open(os.path.join(script_directory, "articles_summary.csv"), "w", newline="") as output_file:
                writer = csv.writer(output_file)
                writer.writerows(lines)

            task["done"] = "done"  # Update the task's status to "done" in the tasks list
            tasks_completed += 1
            log_to_console_and_file(f"Task {task['title']} completed. Total tasks completed: {tasks_completed}.", "green")
        current_task_index += 1  # Move to the next task
    return tasks, current_task_index  # Return the updated task index


if __name__ == "__main__":
    # Load the credentials from the settings-midjourney.conf file
    config = configparser.ConfigParser()
    config.read("settings-midjourney.conf")
    username = config.get("credentials", "username")
    password = config.get("credentials", "password")


    # Initialize the webdriver
    driver, chat_input = initialize_webdriver(runInTerminal, username, password)

   
    tasks = [] # Initialize an empty tasks list
    tasks = load_tasks(tasks) # load tasks from articles_summary.csv for the first time
    current_task_index = 0  # Initialize the current task index outside the function

    # Process the tasks and update the current task index
    tasks, current_task_index = process_tasks(driver, tasks, chat_input, current_task_index)


log_to_console_and_file("All tasks completed.", "green")
driver.quit()
