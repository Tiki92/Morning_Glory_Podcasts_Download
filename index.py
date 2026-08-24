import os
import time
import re
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib.request
try:
    import requests
    from tqdm import tqdm
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# URL of the main podcast page
main_url = "https://www.rockfm.ro/podcast/9/morning-glory-cu-razvan-exarhu/67/2024"

# Romanian month names used by the podcast metadata
ROMANIAN_MONTHS = {
    "ianuarie": "01",
    "februarie": "02",
    "martie": "03",
    "aprilie": "04",
    "mai": "05",
    "iunie": "06",
    "iulie": "07",
    "august": "08",
    "septembrie": "09",
    "octombrie": "10",
    "noiembrie": "11",
    "decembrie": "12",
}

# Function to add a canonical date to a podcast title
def add_date_to_title(title, date_text):
    date_match = re.search(
        r"(\d{1,2})\s+([a-zăâîșț]+)\s+(\d{4})",
        date_text.lower(),
    )
    if not date_match:
        return title

    day, month_name, year = date_match.groups()
    month = ROMANIAN_MONTHS.get(month_name)
    if not month:
        return title
    title_without_date = re.sub(
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b|\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b",
        "",
        title,
    )
    title_without_date = re.sub(
        r"^\s*(?:Morning Glory|MG)\s*[-:]?\s*",
        "",
        title_without_date,
        flags=re.IGNORECASE,
    )
    title_without_date = re.sub(r"\s+-\s*$", "", title_without_date).strip()
    date = f"{year}.{month}.{day.zfill(2)}"
    if title_without_date:
        return f"Morning Glory - {date} - {title_without_date}"
    return f"Morning Glory - {date}"

def podcast_cache_has_dates():
    with open('podcast_urls.txt', 'r', encoding='utf-8') as f:
        titles = [line.strip().split('|', 1)[0] for line in f if line.strip()]
    return all(re.match(r"^Morning Glory - \d{4}\.\d{2}\.\d{2}\b", title) for title in titles)

# Check if podcast URLs are already saved
if os.path.exists('podcast_urls.txt') and podcast_cache_has_dates():
    podcast_data = []
    with open('podcast_urls.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '|' in line:
                title, url = line.split('|', 1)
                podcast_data.append((title, url))
            else:
                # Fallback for old format (just URL)
                podcast_data.append(("Unknown Title", line))
    print("Loaded podcast data from file.")
else:
    # Set up Selenium WebDriver for Firefox
    firefox_options = Options()
    firefox_options.add_argument('--headless')  # Run in headless mode
    driver = webdriver.Firefox(options=firefox_options)  # Make sure you have geckodriver installed
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
    podcast_data = []

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
    # print("Show soup content loaded.")
    # print(soup.prettify())  # Print the parsed HTML for debugging
    
    # Find the podcast item list div
    podcast_list = soup.find('div', class_='aw-podcast-item-list')
    # if podcast_list:
    #     print("Found podcast list div:", podcast_list.prettify())
    # else:
    #     print("Podcast list div not found.")
    
    # print("Finished loading all podcasts.")
    # print(podcast_list.prettify() if podcast_list else "No podcast list to display.")
    driver.quit()

    # Find all podcast links
    for link in podcast_list.find_all('a', class_='aw-one-podcast-meta', href=True):
        print("Found podcast link:", link)
        href = link['href']
        title = link.find('h3')
        if title:
            title_text = title.text.strip()
        else:
            title_text = "No title found"

        metadata_date = link.find("h5")
        if metadata_date:
            date_span = metadata_date.find("span")
            if date_span:
                title_text = add_date_to_title(title_text, date_span.get_text(strip=True))
        print(f"Podcast title: {title_text}")
        if href.startswith('/podcast-episode'):
            full_url = urljoin(main_url, href)
            podcast_data.append((title_text, full_url))

    # Save the podcast URLs to file
    with open('podcast_urls.txt', 'w', encoding='utf-8') as f:
        for title, url in podcast_data:
            f.write(f"{title}|{url}\n")
    print("Saved podcast data to file.")

# Print all podcast links
print("Found podcast links:")
for idx, (title, url) in enumerate(podcast_data, start=1):
    print(f"{idx}: {title} - {url}")

# Create the "podcasts" directory if it does not exist
os.makedirs("podcasts", exist_ok=True)

# Function to sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '', filename).strip()

def podcast_save_path(title, occurrence):
    safe_title = sanitize_filename(title)
    suffix = f" ({occurrence})" if occurrence > 1 else ""
    return os.path.join("podcasts", f"{safe_title}{suffix}.mp3")

# Function to download podcast
def download_podcast(download_url, save_path):
    print(f"Starting download from {download_url} to {save_path}")
    if HAS_REQUESTS:
        try:
            # Try HEAD request to get content-length
            head_response = requests.head(download_url)
            head_response.raise_for_status()
            total_size = int(head_response.headers.get('content-length', 0))
            
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                if total_size == 0:
                    total_size = int(r.headers.get('content-length', 0))  # Fallback to GET headers
                with open(save_path, 'wb') as f, tqdm(
                    desc=os.path.basename(save_path),
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        size = f.write(chunk)
                        bar.update(size)
            print(f"Downloaded: {save_path}")
        except Exception as e:
            print(f"Failed to download {download_url}. Error: {e}")
    else:
        total_size = 0
        try:
            with urllib.request.urlopen(download_url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
        except:
            pass
        print(f"Total size: {total_size}")  # Debug

        def progress_hook(block_num, block_size, reported_total):
            read_so_far = block_num * block_size
            if total_size > 0:
                percent = read_so_far * 100 / total_size
                s = f"\r{percent:5.1f}% {read_so_far / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB"
                sys.stderr.write(s)
                if read_so_far >= total_size:
                    sys.stderr.write('\n')
            else:
                s = f"\rDownloaded {read_so_far / 1024:.2f} KB"
                sys.stderr.write(s)

        try:
            urllib.request.urlretrieve(download_url, save_path, progress_hook)
            print(f"Downloaded: {save_path}")
        except Exception as e:
            print(f"Failed to download {download_url}. Error: {e}")

# Function to download all podcasts from the given list of podcast data
def download_all_podcasts(podcast_data):
     # Set global page load timeout for all instances created in this function context
    PAGE_LOAD_TIMEOUT = 10 # Seconds
    title_occurrences = {}

    for idx, (title, podcast_url) in enumerate(podcast_data, start=1):
        title_occurrences[title] = title_occurrences.get(title, 0) + 1
        save_path = podcast_save_path(title, title_occurrences[title])

        # Check if file already exists before navigating
        if os.path.exists(save_path):
            print(f"File already exists, skipping: {save_path}")
            continue

        driver = None # Initialize driver variable outside try block
        try:
            # --- Setup WebDriver with timeout options ---
            firefox_options = Options()
            firefox_options.add_argument('--headless')  # Run in headless mode
            # You can add other options here if needed (e.g., headless mode)
            
            driver = webdriver.Firefox(options=firefox_options)
            # CRITICAL: Set the page load timeout here, *before* driver.get()
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            
            # --- Attempt to load the page with timeout logic ---
            try:
                print(f"Attempting to load page {idx}: {podcast_url}")
                driver.get(podcast_url)
                print(f"Page {idx} loaded successfully.")
            except TimeoutException:
                print(f"Page load timeout ({PAGE_LOAD_TIMEOUT}s) reached for page {idx}. Refreshing...")
                driver.refresh() # This might time out again, but it attempts recovery
                time.sleep(2) # Give it a moment after refresh

            print(f"Visiting podcast page {idx}: {podcast_url}")

            print(f"Podcast {idx} title: {title}")

            # Wait for the download button to be clickable
            download_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Descarcă") or contains(text(), "Download")]'))
            )
            download_url = download_button.get_attribute('href')

            download_podcast(download_url, save_path)

        except TimeoutException as e:
            # Catch subsequent timeouts if refresh() also timed out or element waits failed
            print(f"A subsequent timeout occurred on page {idx}: {e}")
        except WebDriverException as e:
            # Catch general Selenium errors like connection lost, browser closed unexpectedly, etc.
            print(f"A WebDriver error occurred on page {idx}: {e}")
        except Exception as e:
            # General catch-all for file system errors, etc.
            print(f"An unexpected error occurred on podcast page {idx}: {e}")
        finally:
            # Ensure the driver quits even if an error occurs
            if driver:
                driver.quit()

# Start downloading podcasts
download_all_podcasts(podcast_data)

print("All podcasts have been processed.")
