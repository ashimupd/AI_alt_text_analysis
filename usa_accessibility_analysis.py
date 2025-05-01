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
shouldSendContext = False  # Set to True to include webpage context in alt-text generation
openai_api_key = ""

websites = [
    "https://www.nih.gov",
    "https://www.cdc.gov",
    "https://www.fda.gov",
    "https://www.webmd.com",
    "https://www.mayoclinic.org",
    "https://healthy.kaiserpermanente.org",
    "https://www.uhc.com",
    "https://www.drugs.com",
    "https://www.cvs.com",
    "https://www.athenahealth.com",
]
# Set up OpenAI client
client = OpenAI(api_key=openai_api_key)

# OUTPUT FILES
csv_filename = "image_alt_text_report_context.csv" if shouldSendContext else "image_alt_text_report.csv"
html_filename = "image_alt_text_report_context.html" if shouldSendContext else "image_alt_text_report.html"

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


from bs4 import NavigableString, Tag

def get_image_context(soup, img_element=None, image_url=None):
    """
    Extract relevant context around an image (without using the existing alt).
    Returns a string of collected context suitable for alt-text generation.
    """

    if img_element is None and image_url:
        for attr in ['src', 'data-src', 'srcset']:
            img_element = soup.find('img', {attr: image_url})
            if img_element:
                break
        if not img_element:
            for img in soup.find_all('img'):
                srcset = img.get('srcset', '')
                if image_url in srcset:
                    img_element = img
                    break
        if not img_element:
            return "Image not found in the document."

    if not img_element:
        return "No image element or URL provided."

    context = []

    # 1. Title attribute
    title = img_element.get('title', '')
    if title:
        context.append(f"Title: {title}")

    # 2. Figcaption if available
    figure = img_element.find_parent('figure')
    if figure:
        figcaption = figure.find('figcaption')
        if figcaption:
            context.append(f"Caption: {figcaption.get_text(strip=True)}")

    # 3. Headings nearby (within 3 parent levels and previous siblings)
    def find_nearest_heading(el):
        heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        max_levels = 3
        for _ in range(max_levels):
            if not el:
                break
            for sibling in el.find_previous_siblings():
                if sibling.name in heading_tags:
                    return sibling.get_text(strip=True)
            el = el.parent
        return None

    # Forward heading search
    def find_forward_heading(el):
        for sibling in el.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                return sibling.get_text(strip=True)
            for desc in sibling.descendants:
                if isinstance(desc, Tag) and desc.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    return desc.get_text(strip=True)
        return None

    heading = find_nearest_heading(img_element)
    if heading:
        context.append(f"Nearby heading: {heading}")
    else:
        forward_heading = find_forward_heading(img_element)
        if forward_heading:
            context.append(f"Forward heading: {forward_heading}")

    # 4. Container/parent text (within 2 levels up)
    valid_containers = ['div', 'article', 'section', 'figure', 'p']
    current = img_element
    for _ in range(2):
        if not current.parent:
            break
        current = current.parent
        if current.name in valid_containers:
            text_parts = [t.strip() for t in current.strings if isinstance(t, NavigableString) and t.strip()]
            if text_parts:
                container_text = ' '.join(text_parts[:3])
                context.append(f"Container text: {container_text}")
            break

    # 5. Nearby text siblings
    def get_nearby_text(el, direction='prev', limit=3):
        texts = []
        count = 0
        sibling = el.previous_sibling if direction == 'prev' else el.next_sibling
        while sibling and count < limit:
            if isinstance(sibling, NavigableString) and sibling.strip():
                texts.append(sibling.strip())
                count += 1
            elif isinstance(sibling, Tag) and sibling.name in ['p', 'span', 'div', 'li']:
                txt = sibling.get_text(strip=True)
                if txt:
                    texts.append(txt)
                    count += 1
            sibling = sibling.previous_sibling if direction == 'prev' else sibling.next_sibling
        return texts

    prev_texts = get_nearby_text(img_element, 'prev')
    next_texts = get_nearby_text(img_element, 'next')
    if prev_texts:
        context.append("Previous text: " + ' '.join(prev_texts))
    if next_texts:
        context.append("Next text: " + ' '.join(next_texts))

    # 6. Nearby paragraphs (within 2 ancestors)
    def find_nearby_paragraphs(img, limit=2):
        paragraphs = []
        for parent in img.parents:
            if not parent or parent.name in ['body', 'html']:
                break
            ps = parent.find_all('p')
            for p in ps:
                if p and p.get_text(strip=True):
                    paragraphs.append(p.get_text(strip=True))
            if paragraphs:
                break
        return paragraphs[:limit]

    paragraphs = find_nearby_paragraphs(img_element)
    for i, para in enumerate(paragraphs):
        context.append(f"Nearby paragraph {i + 1}: {para}")

    # 7. ARIA or semantic hints
    if 'aria-label' in img_element.attrs:
        context.append(f"ARIA label: {img_element['aria-label']}")
    if 'aria-labelledby' in img_element.attrs:
        label_id = img_element['aria-labelledby']
        label_el = soup.find(id=label_id)
        if label_el:
            context.append(f"ARIA labelledby: {label_el.get_text(strip=True)}")

    # 8. Image link
    parent_link = img_element.find_parent('a')
    if parent_link:
        link_text = parent_link.get_text(strip=True)
        href = parent_link.get('href', '')
        if href:
            context.append(f"Linked URL: {href}")
        if link_text:
            context.append(f"Link text: {link_text}")

    # 9. DOM label hints (class/id)
    def get_dom_label_hints(el):
        for _ in range(3):
            if not el or el.name in ['body', 'html']:
                break
            if el.has_attr('id'):
                return f"Container ID: {el['id']}"
            if el.has_attr('class'):
                return f"Container class: {' '.join(el['class'])}"
            el = el.parent
        return None

    dom_hint = get_dom_label_hints(img_element)
    if dom_hint:
        context.append(dom_hint)

    # 10. Nearby list items
    def find_nearby_list_items(el):
        ul = el.find_parent(['ul', 'ol'])
        if ul:
            items = ul.find_all('li')
            texts = [li.get_text(strip=True) for li in items if li.get_text(strip=True)]
            return texts[:3]
        return []

    list_items = find_nearby_list_items(img_element)
    if list_items:
        context.append("List context: " + ' | '.join(list_items))

    # 11. Nearby table cells
    def find_nearby_table_cells(el):
        table = el.find_parent('table')
        if table:
            cells = table.find_all(['td', 'th'])
            texts = [c.get_text(strip=True) for c in cells if c.get_text(strip=True)]
            return texts[:4]
        return []

    table_cells = find_nearby_table_cells(img_element)
    if table_cells:
        context.append("Table context: " + ' | '.join(table_cells))

    # 12. Fallback if context is too sparse
    if not context:
        context.append("No clear textual context found. Consider examining closest headings or surrounding DOM structure for hints.")

    return '\n'.join(context[:12])[:1500]



def generate_alt_text(image_url, image_bytes, webpage_content=None):
    try:
        base_prompt = """Generate alt text for accessibility purposes. The alt text should:
1. Don't provide additional information in the the alt-text other than that conveyed by the image, but still consider the context
2. Provide context on how the image relates to the page content
3. Be accurate and equivalent in representing content and function
4. Be succinct - typically only a few words are necessary, though rarely a short sentence or two may be appropriate. Content (if any) and function (if any) should be presented as succinctly as possible, without sacrificing accuracy.
5. Not be redundant with nearby text
6. Not include phrases like "image of..." or "graphic of..."
"""
        context_prompt = ""
        if shouldSendContext and webpage_content:
            soup = BeautifulSoup(webpage_content, 'html.parser')
            img_element = soup.find('img', src=image_url)
            if img_element:
                try:
                    context = get_image_context(soup, img_element)
                    print('context:', context)
                    context_prompt = f"\nHere is the relevant context around the image:\n{context}\nPlease generate appropriate alt text for the image considering this context.\n"
                except Exception as e:
                    print('exception when processing context:', e)
                    context_prompt = ""

        full_prompt = base_prompt + context_prompt

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
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
        return response.choices[0].message.content.strip(), full_prompt
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
                            {"type": "text", "text": full_prompt},
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
            return response.choices[0].message.content.strip(), full_prompt
        except Exception as fallback_error:
            print(f"Base64 fallback also failed: {fallback_error}")
            return "API_ERROR", base_prompt
        else:
            return "No image bytes could be retrieved.", base_prompt


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
            ai_alt, prompt_used = generate_alt_text(img_url, image_bytes, homepage if shouldSendContext else None)
            time.sleep(5)
        else:
            print("image download failed, skipped")
            with open('image_download_failed.txt', 'a') as f:
                f.write(img_url + "\n")
            continue

        has_alt = 'Yes' if existing_alt is not None else 'No'

        result = {
            'page_url': site_url,
            'image_url': img_url,
            'existing_alt': existing_alt if existing_alt else "",
            'ai_generated_alt': ai_alt,
            'alt_present': has_alt,
            'prompt_used': prompt_used
        }
        all_results.append(result)

# WRITE CSV
with open(csv_filename, mode='w', newline='', encoding='utf-8') as csv_file:
    fieldnames = ['page_url', 'image_url', 'existing_alt', 'ai_generated_alt', 'alt_present', 'prompt_used']
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
.prompt { 
    max-width: 500px; 
    word-wrap: break-word;
    white-space: pre-wrap;
    font-family: monospace;
    font-size: 12px;
    max-height: 300px;
    overflow-y: auto;
    background-color: #f5f5f5;
    padding: 10px;
}
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
<th>Prompt Used</th>
</tr>
"""

for entry in all_results:
    # Escape HTML special characters in the prompt
    escaped_prompt = entry['prompt_used'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    html_content += f"""
    <tr>
        <td><a href="{entry['page_url']}" target="_blank">{entry['page_url']}</a></td>
        <td><img src="{entry['image_url']}" alt="Image"></td>
        <td>{entry['existing_alt']}</td>
        <td>{entry['ai_generated_alt']}</td>
        <td>{entry['alt_present']}</td>
        <td class="prompt">{escaped_prompt}</td>
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
