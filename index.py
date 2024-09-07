import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib.request

# URL of the main podcast page
main_url = "https://www.rockfm.ro/podcast/9/morning-glory-cu-razvan-exarhu/44/2019"

# Set up Selenium WebDriver for Firefox
driver = webdriver.Firefox()  # Make sure you have geckodriver installed
driver.get(main_url)

# Handle cookie consent popup if it exists
try:
    cookie_accept_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Permitere toate")]'))
    )
    cookie_accept_button.click()
    print("Cookie consent accepted.")
except Exception as e:
    print("No cookie consent popup or failed to accept.")
    print(f"Error: {e}")

# Load all podcasts by clicking the "Mai multe podcasturi" button
last_height = driver.execute_script("return document.body.scrollHeight")
podcast_urls = []

while True:
    try:
        # Find the "Mai multe podcasturi" button
        load_more_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//div[contains(@class, "aw-page-header")]//a[contains(text(), "Mai multe podcasturi")]'))
        )
        
        # Scroll the button into view
        driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
        time.sleep(1)  # Wait for the scrolling to complete
        
        # Click the button
        load_more_button.click()
        time.sleep(2)  # Wait for the new content to load

        # Check if the page height has changed to detect if new content is loaded
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("No more podcasts to load or an error occurred.")
            break
        last_height = new_height

    except Exception as e:
        print(f"Error: {e}")
        break

# Parse the loaded page with BeautifulSoup
soup = BeautifulSoup(driver.page_source, 'html.parser')
driver.quit()

# Find all podcast links
podcast_urls = []
for link in soup.find_all('a', class_='aw-one-podcast-meta', href=True):
    href = link['href']
    if href.startswith('/podcast-episode'):
        podcast_urls.append(urljoin(main_url, href))

# Print all podcast links
print("Found podcast links:")
for idx, podcast_link in enumerate(podcast_urls, start=1):
    print(f"{idx}: {podcast_link}")

# Create the "podcasts" directory if it does not exist
os.makedirs("podcasts", exist_ok=True)

# Function to sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '', filename).strip()

# Function to download podcast
def download_podcast(download_url, save_path):
    try:
        urllib.request.urlretrieve(download_url, save_path)
        print(f"Downloaded: {save_path}")
    except Exception as e:
        print(f"Failed to download {download_url}. Error: {e}")

# Function to download all podcasts from the given list of podcast URLs
def download_all_podcasts(podcast_urls):
    for idx, podcast_url in enumerate(podcast_urls, start=1):
        driver = webdriver.Firefox()  # Make sure you have geckodriver installed
        driver.get(podcast_url)
        print(f"Visiting podcast page {idx}: {podcast_url}")

        try:
            # Extract podcast title
            title_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//h2[@style="line-height: 1;"]'))
            )
            title = title_element.text
            # Sanitize title for use in filenames
            safe_title = sanitize_filename(title)
            
            # Wait for the download button to be clickable
            download_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Descarcă") or contains(text(), "Download")]'))
            )
            download_url = download_button.get_attribute('href')
            
            # Define save path with title
            save_path = os.path.join("podcasts", f"{safe_title}.mp3")  # Adjust extension based on file type
            download_podcast(download_url, save_path)
        except Exception as e:
            print(f"Error on podcast page {idx}: {e}")
        finally:
            driver.quit()

# Start downloading podcasts
download_all_podcasts(podcast_urls)

print("All podcasts have been processed.")
