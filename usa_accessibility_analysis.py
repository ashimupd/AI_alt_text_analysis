import http.client
import requests
from bs4 import BeautifulSoup
import csv
import re
import base64
import time
from urllib.parse import urljoin, urlparse
from openai import OpenAI
from datetime import datetime

http.client._MAXHEADERS = 1000  # Set to a higher value like 500 or 1000
# CONFIGURATION
openai_api_key = "test"
websites = [
    "https://www.nih.gov",
    "https://www.cdc.gov",
    "https://www.fda.gov",
    "https://www.healthline.com",
    "https://www.webmd.com",
    "https://www.medicalnewstoday.com",
    "https://www.mayoclinic.org",
    "https://my.clevelandclinic.org/",
    "https://healthy.kaiserpermanente.org",
    "https://www.uhc.com",
    "https://www.cigna.com",
    "https://www.aetna.com",
    "https://www.anthem.com",
    "https://www.drugs.com",
    "https://www.goodrx.com",
    "https://www.cvs.com",
    "https://www.labcorp.com",
    "https://www.questdiagnostics.com",
    "https://www.athenahealth.com",
    "https://www.epic.com",
    "https://www.cerner.com",
    "https://www.zocdoc.com",
]

# Set up OpenAI client
client = OpenAI(api_key=openai_api_key)

# OUTPUT FILES
csv_filename = "image_alt_text_report.csv"
html_filename = "image_alt_text_report.html"

# HELPER FUNCTIONS
def fetch_homepage(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }

        # The key issue: cookies are needed
        cookies = {
            'at_check': 'true',
            'AMCVS_8E391C8B533058250A490D4D@AdobeOrg': '1',
            'AMCV_8E391C8B533058250A490D4D@AdobeOrg': '179643557|MCIDTS|20207|MCMID|76706862582752762032206251736920084397|MCAAMLH-1746417529|7|MCAAMB-1746417529|RKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y|MCOPTOUT-1745819929s|NONE|vVersion|5.5.0',
            # Add other cookies as needed
        }

        session = requests.Session()
        response = session.get(url, headers=headers, cookies=cookies, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to fetch {url}: {str(e)}\n"
        # Write error to file
        with open('homepage_errors.txt', 'a') as f:
            f.write(error_msg)
        return None


def get_images(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    valid_images = []

    supported_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.gif')

    for img in images:
        src = img.get('src')
        if not src:
            continue

        # Normalize and resolve full URL
        full_url = urljoin(base_url, src)

        # Check for supported file types
        if not re.search(r'\.(png|jpg|jpeg|webp|gif)(\?.*)?$', full_url, re.IGNORECASE):
            continue

        # Accessibility checks
        role = img.get('role')
        alt_text = img.get('alt')
        aria_hidden = img.get('aria-hidden')

        if (role in ["presentation", "none"]) or (alt_text == "") or (aria_hidden == "true"):
            continue

        valid_images.append({
            'img_url': full_url,
            'alt_text': alt_text
        })

        if len(valid_images) >= 5:
            break

    return valid_images


def download_image(image_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }

        # The key issue: cookies are needed
        cookies = {
            'at_check': 'true',
            'AMCVS_8E391C8B533058250A490D4D@AdobeOrg': '1',
            'AMCV_8E391C8B533058250A490D4D@AdobeOrg': '179643557|MCIDTS|20207|MCMID|76706862582752762032206251736920084397|MCAAMLH-1746417529|7|MCAAMB-1746417529|RKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y|MCOPTOUT-1745819929s|NONE|vVersion|5.5.0',
            # Add other cookies as needed
        }
        session = requests.Session()
        response = session.get(image_url, headers=headers, cookies=cookies, timeout=15)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Failed to download image {image_url}: {e}")
        return None

def generate_alt_text(image_url, image_bytes):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "`Generate a concise and descriptive alt text for accessibility purposes.`"},
                        {
                            "type": "image_url",
                            "image_url": {
                               "url": image_url,
                                "detail": "low"
                            },
                        }
                ]}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")

    if image_bytes:
        try:
            print("Retrying with base64 encoded image...")
            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Generate a concise and descriptive alt text for accessibility purposes."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "low"
                                },
                            }
                        ]
                    }
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as fallback_error:
            print(f"Base64 fallback also failed: {fallback_error}")
            return "API_ERROR"
        else:
            return "No image bytes could be retrieved."


def safe_filename(url):
    parsed = urlparse(url)
    return parsed.netloc.replace('.', '_')

# MAIN WORK
all_results = []

for site_url in websites:
    print(f"Processing {site_url}...")
    homepage = fetch_homepage(site_url)
    if not homepage:
        continue

    images = get_images(homepage, site_url)

    for img_info in images:
        img_url = img_info['img_url']
        existing_alt = img_info['alt_text']
        image_bytes = download_image(img_url)

        if image_bytes:
            ai_alt = generate_alt_text(img_url, image_bytes)
            time.sleep(5)
        else:
            print("image download failed, skipped")
            with open('image_download_failed.txt', 'a') as f:
                f.write(img_url + "\n");
            continue

        has_alt = 'Yes' if existing_alt is not None else 'No'

        result = {
            'page_url': site_url,
            'image_url': img_url,
            'existing_alt': existing_alt if existing_alt else "",
            'ai_generated_alt': ai_alt,
            'alt_present': has_alt
        }
        all_results.append(result)

# WRITE CSV
with open(csv_filename, mode='w', newline='', encoding='utf-8') as csv_file:
    fieldnames = ['page_url', 'image_url', 'existing_alt', 'ai_generated_alt', 'alt_present']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    for entry in all_results:
        writer.writerow(entry)

print(f"CSV file '{csv_filename}' written successfully.")

# WRITE HTML
html_content = """
<html>
<head>
<title>Image Alt Text Report</title>
<style>
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid black; padding: 8px; text-align: left; }
img { max-width: 200px; height: auto; }
</style>
</head>
<body>
<h1>Image Alt Text Report</h1>
<table>
<tr>
<th>Website</th>
<th>Image</th>
<th>Existing Alt Text</th>
<th>AI-Generated Alt Text (gpt-4.1)</th>
<th>Alt Present</th>
</tr>
"""

for entry in all_results:
    html_content += f"""
    <tr>
        <td><a href="{entry['page_url']}" target="_blank">{entry['page_url']}</a></td>
        <td><img src="{entry['image_url']}" alt="Image"></td>
        <td>{entry['existing_alt']}</td>
        <td>{entry['ai_generated_alt']}</td>
        <td>{entry['alt_present']}</td>
    </tr>
    """

html_content += """
</table>
</body>
</html>
"""

with open(html_filename, 'w', encoding='utf-8') as html_file:
    html_file.write(html_content)

print(f"HTML file '{html_filename}' written successfully.")
