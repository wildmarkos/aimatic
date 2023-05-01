import os
import glob
import datetime
import requests
from wordpress_xmlrpc import WordPressTerm
from wordpress_xmlrpc.methods.taxonomies import  GetTerm, GetTerms, NewTerm
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost, GetPost, EditPost
from wordpress_xmlrpc.methods.media import UploadFile
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc.methods.posts import GetPosts

openai_api_key = "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"
# (create_wordpress_post, upload_images, upload_image, insert_images, and other functions)


def call_openai_api(api_key, prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50,
        "temperature": 0.7,
        "n": 1,
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    response_json = response.json()
    if response.status_code != 200:
        print(f"API test failed with status code {response.status_code}.")
        print("Error details:")
        print(json.dumps(response_json, indent=2))
    #else:
        #print("API test succeeded.")
    
    return response_json


def create_wordpress_post(username, password, url, title, content, article_path):
    wp = Client(f'{url}/xmlrpc.php', username, password)

    # Upload images and set the featured image
    image_urls, featured_image_id = upload_images(wp, article_path)
    print(featured_image_id)

    # Insert images into the article content
    content = insert_images(content, image_urls)

    # Create a new WordPress post
    post = WordPressPost()
    post.title = title
    post.content = content
    post.post_status = 'draft'  # Set the post status to 'publish' if you want to publish it immediately
    post.thumbnail = featured_image_id  # Set the featured image

    # Manually set the properties to send to the server
    post_struct = {
        'post_title': post.title,
        'post_content': post.content,
        'post_status': post.post_status,
        'post_thumbnail': post.thumbnail,
    }

    # Create the post
    print(post)

    post_id = wp.call(NewPost(post_struct))

    # Assign categories and tags
    post_category, post_tags = assign_categories_and_tags(wp, post, title, content)

    # Set the post's category and tags separately
    post.terms = {'category': [post_category.id], 'post_tag': [tag.id for tag in post_tags]}

    # Update the post_struct with the new terms
    post_struct['terms'] = post.terms

    # Update the post with the new terms
    wp.call(EditPost(post_id, post_struct))

    print(f"Post with ID {post_id} has been created on your WordPress site with the assigned category and tags.")


def upload_images(wp, article_path):
    image_paths = [os.path.join(article_path, f"{index + 1}.jpg") for index in range(2)]
    featured_image_path = os.path.join(article_path, "featured.jpg")

    image_urls = []
    featured_image_id = 0
    for image_path in image_paths:
        image_url = upload_image(wp, image_path)
        image_urls.append(image_url)

    featured_image_id = upload_image(wp, featured_image_path, True)

    return image_urls, featured_image_id


def upload_image(wp, image_path, is_featured=False):
    with open(image_path, 'rb') as img:
        data = {
            'name': os.path.basename(image_path),
            'type': 'image/jpeg',
        }
        data['bits'] = xmlrpc_client.Binary(img.read())
        response = wp.call(UploadFile(data))

    if is_featured:
        return response['id']
    else:
        return response['url']


def insert_images(content, image_urls):
    paragraphs = content.split("\n\n")
    paragraphs.insert(4, f'<img src="{image_urls[1]}" alt="Find jobs image">')
    content = "\n\n".join(paragraphs)
    return content


def assign_category(wp, title, category_names, content):
    #print(f"Given the article content #START-POST-CONTENT '{content}' #END-POST-CONTENT, does it fit any of these categories: '{category_names}'? IF YES RESPOND ONLY WITH THE CATEGORY NAME, NO EXTRA TEXT OR BEFORE THE CATEGORY. CANT BE CATEGORY NAMED 'Uncategorized' OR HAVE THE WORD 'category' on it THIS IS VERY IMPORTANT OR GENERATE A NEW ONE THAT FITS. IF NOT FOUND CATEGORY: Find a new one-word (IMPORTANT) BLOG category for the article POST CONTENT I mentioned.")
    
    response = call_openai_api(
        openai_api_key,
        f"Given the article content #START-POST-CONTENT '{content}' #END-POST-CONTENT, does it fit any of these categories: '{category_names}'? IF YES RESPOND ONLY WITH THE CATEGORY NAME, NO EXTRA TEXT OR BEFORE THE CATEGORY. CANT BE CATEGORY NAMED 'Uncategorized' OR HAVE THE WORD 'category' on it THIS IS VERY IMPORTANT OR GENERATE A NEW ONE THAT FITS. IF NOT FOUND CATEGORY: Find a new one-word (IMPORTANT) BLOG category for the article POST CONTENT I mentioned (text format Capitalized).",
    )
    print("CATEGORIA SELECCIONADA> "+response['choices'][0]['message']['content'])
    category = response['choices'][0]['message']['content'].split()[0].lower()

    #new_category = response['choices'][0]['message']['content'].strip()
    return category



def get_tags_from_openai(content, n_tags=7):
    response = call_openai_api(
        openai_api_key,
        f"Find from MINIMUM 5 to MAX {n_tags} important keywords separated by ',' for the following article: {content}"
    )
    print("tags SELECCIONADos> "+response['choices'][0]['message']['content'])

    tags = [tag.strip() for tag in response['choices'][0]['message']['content'].split(',') if tag.strip()]
    return tags[:n_tags]


def assign_categories_and_tags(wp, post, title, content):
    # Get all existing categories
    categories = wp.call(GetTerms('category'))
    category_dict = {category.name.lower(): category for category in categories}

    # Assign category
    post_category_name = assign_category(wp, title, list(category_dict.keys()), content)
    if post_category_name.lower() not in category_dict:
        # Create a new category if it doesn't exist
        new_category = WordPressTerm()
        new_category.taxonomy = 'category'
        new_category.name = post_category_name
        new_category.id = wp.call(NewTerm(new_category))
        category_dict[post_category_name.lower()] = new_category

    # Get all existing tags
    existing_tags = wp.call(GetTerms('post_tag'))
    tag_dict = {tag.name.lower(): tag for tag in existing_tags}

    # Get suggested tags from OpenAI
    suggested_tags = get_tags_from_openai(content)

    # Select the tags to be used for the post
    selected_tags = []
    for suggested_tag in suggested_tags:
        suggested_tag_lower = suggested_tag.lower()
        if suggested_tag_lower in tag_dict:
            selected_tags.append(tag_dict[suggested_tag_lower])
        else:
            try:
                # Create a new tag if it doesn't exist
                new_tag = WordPressTerm()
                new_tag.taxonomy = 'post_tag'
                new_tag.name = suggested_tag
                new_tag.id = wp.call(NewTerm(new_tag))
                tag_dict[suggested_tag_lower] = new_tag
                selected_tags.append(new_tag)
            except xmlrpc_client.Fault as e:
                if e.faultCode == 500 and "A term with the name provided already exists" in e.faultString:
                    print(f"Tag '{suggested_tag}' already exists, skipping...")
                else:
                    raise e

    # Assign the selected category and tags to the post
    post.terms = {
        'category': [category_dict[post_category_name.lower()]],
        'post_tag': selected_tags
    }
    return category_dict[post_category_name.lower()], selected_tags



def process_articles_folder(articles_folder_path, username, password, url):
    today = datetime.date.today().strftime("%Y%m%d")
    uploaded_tag = f"-uploaded{today}"
    for article_folder in os.listdir(articles_folder_path):
        article_path = os.path.join(articles_folder_path, article_folder)
        if os.path.isdir(article_path):
            print(f"Processing article folder: {article_folder}")
            # Find the HTML file with the "-done" tag
            html_files = glob.glob(os.path.join(article_path, "*-done.html"))
            if not html_files:
                print(f"No HTML file found with the '-done' tag in {article_path}")
                continue

            html_file = html_files[0]
            print(f"Found HTML file: {html_file}")
            
            # Read the HTML file
            with open(html_file, 'r', encoding='utf-8') as content_file:
                content = content_file.read()
            article_folder = article_folder.split("-")[1]
            print(article_folder) 
            
            # Upload the article
            create_wordpress_post(username, password, url, article_folder, content, article_path)

            # Update the HTML file name with the uploaded tag
            new_file_path = os.path.join(f"{os.path.splitext(html_file)[0]}{uploaded_tag}.html")
            os.rename(html_file, new_file_path)




# Replace these with your WordPress username, password, and URL
wordpress_username = 'mark'
wordpress_password = 'Kore123.--'
wordpress_url = 'https://blog.quickjobs.app'

# Replace 'articles' with the path to the folder containing your article folders
articles_folder_path = 'articles'



# Call the function with your parameters
process_articles_folder(articles_folder_path, wordpress_username, wordpress_password, wordpress_url)

