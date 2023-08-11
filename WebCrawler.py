# Import libraries
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
import time

# Set up Chrome driver options with headless mode
driver_options = Options()
driver_options.add_argument("-headless")
driver = webdriver.Chrome(options=driver_options)
driver.implicitly_wait(10)

# Define the target website to crawl
site = "https://www.carilionclinic.org"

# Create a dictionary to store error URLs grouped by their original link
error_urls_grouped = {}

# Function to check if a URL is broken and return the error if it is


def check_url(url):
    try:
        response = requests.get(url, timeout=30, allow_redirects=True)
        return response.status_code != 200, response.status_code
    except requests.Timeout:
        return True, "Timeout"
    except requests.RequestException:
        return True, "Error"

# Function to check if a URL points to a valid resource (excluding certain file types)


def is_valid(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=30)
        content_type = response.headers.get('content-type')
        if content_type and 'application' in content_type:
            return False
        if content_type and 'text/csv' in content_type:
            return False
        return True
    except requests.exceptions.RequestException:
        return False

# Function to check if a URL is internal to the target website


def is_internal(url):
    parsed_site = urlparse(site)
    parsed_url = urlparse(url)
    return parsed_url.hostname == parsed_site.hostname

# Function to scroll down the webpage using JavaScript


def scroll():
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

# Function to perform depth-first crawling of the website


def crawl(url, parent_url=None, visited_urls=None):
    if visited_urls is None:
        visited_urls = set()

    visited_urls.add(url)

    try:
        # Check if the current URL is broken
        is_broken, error_code = check_url(url)
        if is_broken:
            if parent_url not in error_urls_grouped:
                error_urls_grouped[parent_url] = []
            error_urls_grouped[parent_url].append((url, error_code))

        # Open the URL in the browser and scroll down
        driver.get(url)
        scroll()

        print(f"Crawling: {url}")
        print(f"Crawled Count: {len(visited_urls)}")

        # Wait until the page is loaded
        time.sleep(10)

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        all_links = soup.find_all("a")

        # Loop through all links on the page
        for link in all_links:
            href = link.get("href")

            # Check if the link is valid and not an anchor link
            if href and not href.startswith("#"):
                absolute_url = urljoin(url, href)
                # Check if the link is internal and not already visited
                if is_internal(absolute_url) and absolute_url not in visited_urls:
                    if is_valid(absolute_url):
                        # Continue crawling recursively for valid internal links
                        crawl(absolute_url, url, visited_urls)
                    else:
                        # If the link is not valid, mark it as "Download" error for the parent URL
                        if url not in error_urls_grouped:
                            error_urls_grouped[url] = []
                        error_urls_grouped[url].append(
                            (absolute_url, "Download"))

    except Exception as e:
        # Handle any errors encountered while crawling a URL
        print(f"Error occurred while crawling {url}:")
        if parent_url not in error_urls_grouped:
            error_urls_grouped[parent_url] = []
        error_urls_grouped[parent_url].append((url, "Error"))

    return visited_urls


# Start crawling the target website
total_crawled_urls = crawl(site)

# Close the browser after the crawling is completed
driver.quit()

# Output error URLs grouped by their original link to a file
with open("WebCrawlerOutput.txt", "w") as file:
    for parent_url, error_urls in error_urls_grouped.items():
        file.write(f"\nOriginal URL: {parent_url}\n")
        for url, error_code in error_urls:
            file.write(f"Error Code: {error_code}, URL: {url}\n")
