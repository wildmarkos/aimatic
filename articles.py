import os
import requests
import json
import csv
import datetime
import logging
import re
import shutil


from pathlib import Path
from typing import List, Tuple, Dict



def read_config(file_name):
    with open(file_name, 'r') as f:
        config = json.load(f)
    return config

def read_lines(file_path: str) -> List[str]:
    with open(file_path) as file:
        return [line.strip() for line in file]

def write_lines(file_path: str, lines: List[str]):
    with open(file_path, "w") as file:
        for line in lines:
            file.write(line + "\n")

def get_pending_titles(titles: List[str]) -> List[str]:
    return [title for title in titles if not title.startswith("[done]")]

def mark_title_done(titles: List[str], title: str) -> List[str]:
    return ["[done] " + title if t == title else t for t in titles]


def clean_article_name(article_name: str) -> str:
    # Replace invalid characters
    cleaned_name = re.sub(r"[\/:*?<>|]", "-", article_name)
    cleaned_name = cleaned_name.replace("[", "(").replace("]", ")")
    return cleaned_name

def create_article_folder(article_name: str) -> str:

    # Shorten the article_name to a maximum of 3 words
    #article_name_short = " ".join(article_name.split()[:5])

    # Clean the article_name
    article_name = clean_article_name(article_name)

    # Check existing folders in the "articles" directory
    article_indices = []
    articles_path = Path("articles")
    articles_path.mkdir(parents=True, exist_ok=True)

    for folder in articles_path.iterdir():
        if folder.is_dir():
        #and folder.name.startswith(article_name):
            try:
                index = int(folder.name.split("-")[0])
                article_indices.append(index)
            except ValueError:
                pass

    # Assign a new index based on the last one found +1
    if article_indices:
        article_id = max(article_indices) + 1
    else:
        article_id = 1

    # Create the folder
    folder_path = f"articles/{article_id}"
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    return folder_path, article_id, article_name



def save_article(folder_path: str, article_id: str, article_name: str, content: str, format: str):
    file_path = f"{folder_path}/{article_id}.{format}"
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

def call_valueserp_api(api_key: str, query: str, location: str = None) -> Dict:
    params = {
        "api_key": api_key,
        "q": query,
        "location": location,
    }

    response = requests.get("https://api.valueserp.com/search", params)
    response_json = response.json()
    #print("ValueSERP API response:", json.dumps(response_json, indent=2))  # Add this line to print the response
    return response_json


def call_openai_api(api_key, prompt, model, max_tokens, temperature):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": int(max_tokens),
        "temperature": temperature,
        "n": 1,
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    response_json = response.json()
    
    if response.status_code != 200:
        print(f"API test failed with status code {response.status_code}.")
        print("Error details:")
        print(json.dumps(response_json, indent=2))
        print("API tests failed. Please check your API keys.")

    return response_json

    if response.status_code != 200:
        print(f"StableDiffusion API failed with status code {response.status_code}.")
        print("Error details:")
        print(response.text)
        return []

    response_json = response.json()
    return [img["url"] for img in response_json["data"]]


def extract_related_questions(response: Dict) -> List[str]:
    related_questions_data = response.get("related_questions", [])
    related_questions = [question for question in related_questions_data][:5]
    return related_questions[:max(3, len(related_questions))]


def setup_logging():
    logging.basicConfig(filename="logfile.log", level=logging.DEBUG, format="%(asctime)s %(message)s")
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger("").addHandler(console)

def save_csv_record(csv_path, data):
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline='') as csvfile:
        fieldnames = ["title", "folder", "filename", "start_time", "end_time", "api_tokens_used", "token_cost", "img1", "img2", "img3", "midPrompt","doneImg","uploaded"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)


def main():
    setup_logging()

    general_config = read_config("general.config")
    titles = read_lines("titles.config")
    prompt_config = read_config("prompt.config")

    pending_titles = get_pending_titles(titles)
    csv_path = "articles_summary.csv"

    valueserp_api_key = general_config["valueserp_api_key"]




    for title in pending_titles:
        header=""
        body = "" 
        conclusion = ""
        LOCATION = "United States"
        QUERY = title.replace(" ", "+")
        start_time = datetime.datetime.now()

        print("Titulo>" + title)
        #article_id, article_name = title.split("-", 1)
        folder_path, article_id, article_name = create_article_folder(title)

        # Create Article Content
        header_prompt = prompt_config["prePromptHeader"] 
        #header += "////////////////////////////HEADER////////////////////////////////\n\n"
        prompt = prompt_config["promptHeader"].replace("{title}", title)
        print(prompt)
        response = call_openai_api(
            general_config["openai_api_key"],
            prompt,
            general_config["openai_model"],
            500,
            general_config["openai_temperature"])
        header += response['choices'][0]['message']['content']
        print(response['choices'][0]['message']['content'] + "\n\n")


        # Call the ValueSERP API
        valueserp_response = call_valueserp_api(api_key=valueserp_api_key, query=QUERY, location=LOCATION)
        # Extract related questions
        related_questions = extract_related_questions(valueserp_response)

        # Call OpenAI API with valueserp related questions
        
        prompt = prompt_config["promptBody"].replace("{title}", title)
        print(prompt)
        response= call_openai_api(
                general_config["openai_api_key"],
                prompt,
                general_config["openai_model"],
                general_config["openai_max_tokens"],
                general_config["openai_temperature"])
        body += response['choices'][0]['message']['content']

        for question in related_questions:
            #question_prompt = question["question"] + " Use HTML highlight principal key words with bold with <b> </b> and links in HTML pages that are high verified authorities in certain key references. IMPORTANT: DO NOT SAY THAT YOU ARE A LENGUAJE MODEL IN YOUR RESPONSE. MAKE SURE TO NOT MENTION THAT YOU ARE A LENGUAJE MODEL"
            question_prompt = prompt_config["promptValueSerp"].replace("{question}", question["question"])
            print(f"Question: {question['question']}" )
            body += "<h2>"+ question["question"]+ "</h2>\n"
            response = call_openai_api(
                general_config["openai_api_key"],
                question_prompt,
                general_config["openai_model"],
                general_config["openai_max_tokens"],
                general_config["openai_temperature"])
            print(f"Answer: {response['choices'][0]['message']['content']}")
            #print(response)        
            body += response['choices'][0]['message']['content']+ "\n"

        #conclusion += "////////////////////////////CONCLUSION////////////////////////////////\n\n"

        #+ prompt_config["promptConclusion"]
        prompt = prompt_config["promptConclusion"].replace("{title}", title)
        
        print("conclusion>"+prompt+ "\n\n")
        response = call_openai_api(
            general_config["openai_api_key"],
            prompt,
            general_config["openai_model"],
            general_config["openai_max_tokens"],
            general_config["openai_temperature"])
        
        conclusion += response['choices'][0]['message']['content']
        print(response['choices'][0]['message']['content'])




        #generate midjourney
        imagePromptMidj=""
        response = call_openai_api(

            general_config["openai_api_key"],
            prompt_config["images"],
            general_config["openai_model"],
            general_config["openai_max_tokens"],
            general_config["openai_temperature"])
        print("prompt generado para mmirjourney:")
        print(response['choices'][0]['message']['content'])
        imagePromptMidj = response['choices'][0]['message']['content']
        article_content = header + "\n\n" + body + "\n\n" + conclusion
        
        # Save Article in HTML and Markdown format
        save_article(folder_path, article_id, article_name+"-done", article_content, "html")
        save_article(folder_path, article_id, article_name+"-done", article_content, "md")

        end_time = datetime.datetime.now()

        # Update the CSV summary
        record_data = {
            "title": title, "folder":folder_path,
            "filename":  article_name+"-done.html",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "api_tokens_used": general_config["openai_max_tokens"] * 5,
            "token_cost": (general_config["openai_max_tokens"] * 5) * general_config["token_cost_per_thousand"] / 1000,
            "img1": "1.png", "img2": "2.png", "img3":"3.png", "midPrompt": imagePromptMidj,"doneImg":"","uploaded":""
        }
        save_csv_record(csv_path, record_data)
         # Mark Title as Done
        titles = mark_title_done(titles, title)
        write_lines("titles.config", titles)

        print(f"Article '{title}' has been successfully generated and saved.")

if __name__ == "__main__":
    main()


