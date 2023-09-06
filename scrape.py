import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import openai
import re

# Replace with your OpenAI API key

def scrape_hackernews_page(page_number):
    url = f"https://news.ycombinator.com/?p={page_number}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr", class_="athing")

    articles = []
    for row in rows:
        titleline = row.find("span", class_="titleline")
        a_tag = titleline.find("a")
        title = a_tag.text
        url = a_tag["href"]
        articles.append({"title": title, "url": url})

    return articles


def sanitize_api_response(response_text):
    response_text = response_text.strip()
    json_objects = re.findall(r'\{[^}]*\}', response_text)
    valid_json_objects = []

    for json_object in json_objects:
        try:
            valid_json_objects.append(json.loads(json_object))
        except json.JSONDecodeError:
            pass

    return valid_json_objects

def filter_articles_using_similarity(articles):
#    tags = ['retrocomputing', 'retrogaming', 'commodore', 'atari', 'sinclair', 'arcade', '80s']
    tags = [
    "retrocomputing",
    "retrogaming",
    "commodore",
    "atari",
    "sinclair",
    "arcade",
    "80s",
    "70s",
    "8-bit",
    "16-bit",
    "microcomputers",
    "apple",
    "TRS-80",
    "amiga",
    "ZX Spectrum",
    "BBC Micro",
    "MSX",
    "Texas Instruments",
    "Tandy",
    "Acorn",
    "game consoles",
    "Atari 2600",
    "Atari 5200",
    "Atari 7800",
    "Intellivision",
    "Colecovision",
    "Odyssey",
    "DIY machines",
    "breadboard electronics",
    "programming languages",
    "assembly",
    "BASIC",
    "COBOL",
    "FORTRAN",
    "Pascal",
    "LISP",
    "Logo",
    "Ada",
    "Modula-2",
    "Smalltalk",
]

    tag_sentence = ', '.join(tags)
    threshold = 0.65
    filtered_articles = []

    for article in articles:
        title = article["title"]
        prompt = f"Given the following topics: {tag_sentence}. Please rate the relevance of the article \"{title}\" to these topics on a scale from 0 to 1."
        response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=10, n=1, stop=None, temperature=0.5)
        
        # Extract the float value from the response
        score_text = response.choices[0].text.strip()
        match = re.search(r"[-+]?\d*\.\d+|\d+", score_text)
        if match:
            score = float(match.group())
        else:
            print(f"Warning: No score found for article '{title}'. Skipping this article.")
            continue

        if score >= threshold:
            filtered_articles.append(article)

    return filtered_articles


#def filter_articles_using_similarity(articles):
#    tags = ['retrocomputing', 'retrogaming', 'commodore', 'atari', 'sinclair', 'arcade', '80s']
#    tag_sentence = ', '.join(tags)
#    threshold = 0.7
#    filtered_articles = []
#
#    for article in articles:
#        title = article["title"]
#        prompt = f"Given the following topics: {tag_sentence}. Please rate the relevance of the article \"{title}\" to these topics on a scale from 0 to 1."
#        response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=10, n=1, stop=None, temperature=0.5)
#        
#        # Extract the float value from the response
#        score_text = response.choices[0].text.strip()
#        score = float(re.search(r"[-+]?\d*\.\d+|\d+", score_text).group())
#
#        if score >= threshold:
#            filtered_articles.append(article)
#
#    return filtered_articles


#def filter_articles_using_similarity(articles):
#    tags = ['retrocomputing', 'retrogaming', 'commodore', 'atari', 'sinclair', 'arcade', '80s']
#    tag_sentence = ', '.join(tags)
#    threshold = 0.7
#    filtered_articles = []
#
#    for article in articles:
#        title = article["title"]
#        prompt = f"Given the following topics: {tag_sentence}. Please rate the relevance of the article \"{title}\" to these topics on a scale from 0 to 1."
#        response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=10, n=1, stop=None, temperature=0.5)
#        score = float(response.choices[0].text.strip())
#
#        if score >= threshold:
#            filtered_articles.append(article)
#
#    return filtered_articles


def local_filter_articles(articles):
    tags = ['retrocomputing', 'retrogaming', 'commodore', 'atari', 'sinclair', 'arcade', '80s']
    filtered_articles = []

    for article in articles:
        title = article["title"].lower()
        if any(tag in title for tag in tags):
            filtered_articles.append(article)

    return filtered_articles


def filter_articles(articles):
    prompt = f"Filter the following articles to include only those that most probably belong to at least one of the following topics[retrocomputing, retrogaming, commodore, atari, sinclair, arcade, 80s].\n\n{json.dumps(articles)}\n\nFiltered articles:"
    response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=1024, n=1, stop=None, temperature=0.5)
    filtered_articles = sanitize_api_response(response.choices[0].text)
    print("filtering done")

    return filtered_articles


def main():
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = f"scrape-{timestamp}"
    os.makedirs(directory, exist_ok=True)

    all_articles = []
    for i in range(1, 11):
        articles = scrape_hackernews_page(i)
        with open(f"{directory}/articles_{i}.json", "w") as f:
            json.dump(articles, f)

        filtered_articles = filter_articles_using_similarity(articles)
        all_articles.extend(filtered_articles)

    with open(f"{directory}/results.json", "w") as f:
        json.dump(all_articles, f)

    print(f"Scraping and filtering complete. Check the '{directory}' directory for results.")

if __name__ == "__main__":
    main()

