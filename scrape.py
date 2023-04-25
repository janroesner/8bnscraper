import argparse
import json
import requests
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import openai
import re
import time
import xml.etree.ElementTree as ET
import webbrowser
import subprocess

FILTER_THRESHOLD = 0.60
NUMBER_OF_PAGES = 10

# Replace with your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

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
    tags = [
    "retrocomputing",
    "retrogaming",
    "80s",
    "70s",
    "8-bit",
    "16-bit",
    "microcomputers",
    "programming languages",
    "BASIC",
]

    tag_sentence = ', '.join(tags)
    threshold = FILTER_THRESHOLD
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
            article["score"] = score
            filtered_articles.append(article)

    return filtered_articles

def filter_articles(articles):
    prompt = f"Filter the following articles to include only those that most probably belong to at least one of the following topics[retrocomputing, retrogaming, commodore, atari, sinclair, arcade, 80s].\n\n{json.dumps(articles)}\n\nFiltered articles:"
    response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=1024, n=1, stop=None, temperature=0.5)
    filtered_articles = sanitize_api_response(response.choices[0].text)
    print("filtering done")

    return filtered_articles

def find_newest_run_directory():
    data_dir = "data"
    run_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)) and d.startswith("run_")]
    run_dirs.sort(reverse=True)
    return os.path.join(data_dir, run_dirs[0]) if run_dirs else None

def load_results(run_directory):
    results_path = os.path.join(run_directory, "results.json")
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            return json.load(f)
    return []

def save_results(directory, results):
    with open(f"{directory}/results.json", "w") as f:
        json.dump(results, f)

    # Create an RSS feed from the results
    rss = ET.Element("rss", {"xmlns:g": "http://base.google.com/ns/1.0", "version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Filtered Hacker News Articles"
    ET.SubElement(channel, "link").text = "https://news.ycombinator.com/"
    ET.SubElement(channel, "description").text = "Filtered Hacker News articles based on specified keywords."

    for result in results:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = result["title"]
        ET.SubElement(item, "link").text = result["url"]
        if "summary" in result:
            ET.SubElement(item, "description").text = result["summary"]

    # Save the RSS feed as an XML file
    rss_tree = ET.ElementTree(rss)
    with open(f"{directory}/results.rss", "wb") as f:
        rss_tree.write(f, encoding="utf-8", xml_declaration=True)

def extract_content_from_url(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    body = soup.find("body") or soup.find("main")
    if body:
        content = ' '.join([p.get_text() for p in body.find_all("p")])
        return content
    return ""

def summarize_content(content):
    prompt = f"Please summarize the following content in no more than 10 sentences:\n\n{content}\n\nSummary:"
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=200,
        n=1,
        stop=None,
        temperature=0.5
    )
    summary = response.choices[0].text.strip()
    return summary

def summarize_articles(run_directory):
    results_file = os.path.join(run_directory, "results.json")

    # Load existing results
    with open(results_file, "r") as f:
        results = json.load(f)

    # Iterate through the articles and summarize their content
    for entry in results:
        url = entry["url"]
        if "summary" not in entry:
            content = extract_content_from_url(url)
            if content:
                summary = summarize_content(content)
                entry["summary"] = summary
                print(f"Summary for {url}: {summary}")
            else:
                print(f"Unable to extract content from {url}")
            time.sleep(2)  # To avoid making too many requests in a short period of time

    # Save the updated results with summaries
    with open(results_file, "w") as f:
        json.dump(results, f)

def open_rss_in_browser(run_directory):
    rss_path = os.path.abspath(os.path.join(run_directory, "results.rss"))
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    if not os.path.isfile(rss_path):
        print(f"RSS file not found at '{rss_path}'")
        return

    if not os.path.isfile(chrome_path):
        print(f"Google Chrome not found at '{chrome_path}'. Please ensure it is installed and the path is correct.")
        return

    try:
        subprocess.run([chrome_path, f"file://{rss_path}"])
    except Exception as e:
        print(f"Error opening RSS file in Google Chrome: {e}")

def main():
    parser = argparse.ArgumentParser(description="Scrape and filter Hacker News articles.")
    parser.add_argument("-n", "--new", action="store_true", help="Create a new run directory.")
    parser.add_argument("-s", "--summarize", action="store_true", help="Summarize the articles in the newest run directory.")
    parser.add_argument("-o", "--open", action="store_true", help="Open the RSS feed in the newest run directory.")
    args = parser.parse_args()

    if args.open:
        run_directory = find_newest_run_directory()
        if run_directory:
            open_rss_in_browser(run_directory)
        else:
            print("No run directories found.")
        return

    if args.summarize:
        run_directory = find_newest_run_directory()
        if run_directory:
            summarize_articles(run_directory)
        else:
            print("No run directories found.")
        return

    new_run = args.new

    if new_run:
        run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_directory = f"data/run_{run_timestamp}"
        os.makedirs(run_directory, exist_ok=True)
    else:
        run_directory = find_newest_run_directory()
        if not run_directory:
            run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            run_directory = f"data/run_{run_timestamp}"
            os.makedirs(run_directory, exist_ok=True)

    scrape_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    scrape_directory = f"{run_directory}/scrape_{scrape_timestamp}"
    os.makedirs(scrape_directory, exist_ok=True)

    all_articles = []
    existing_results = load_results(run_directory)

    for i in range(1, NUMBER_OF_PAGES + 1):
        articles = scrape_hackernews_page(i)
        with open(f"{scrape_directory}/articles_{i}.json", "w") as f:
            json.dump(articles, f)

        filtered_articles = []
        for article in articles:
            if not any(result["url"] == article["url"] for result in existing_results):
                filtered_article = filter_articles_using_similarity([article])
                if filtered_article:
                    filtered_articles.extend(filtered_article)

        all_articles.extend(filtered_articles)

    unique_articles = []
    for article in all_articles:
        if not any(result["url"] == article["url"] for result in existing_results):
            unique_articles.append(article)

    unique_articles.sort(key=lambda article: article["score"], reverse=True)

    # Merge existing_results and unique_articles, and sort the combined list by score in descending order
    combined_results = sorted(existing_results + unique_articles, key=lambda article: article["score"], reverse=True)

    save_results(run_directory, existing_results + unique_articles)
    print(f"Scraping and filtering complete. Check the '{run_directory}' directory for results.")

if __name__ == "__main__":
    main()
