import requests
from bs4 import BeautifulSoup
import json
import os

LIB_FILE = "lib.json"
DOWNLOAD_DIR = "sheets"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def easy_scrape(part_name):
    print(f"--- 🚀 Searching for {part_name} ---")
    
    # 1. Search (predictable URL structure)
    search_url = f"https://www.datasheetcatalog.com/search.php?query={part_name}"
    
    try:
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. Find the first datasheet link
        # It's usually in a table; we look for links containing 'datasheet-pdf'
        link_tag = soup.find('a', href=lambda x: x and 'datasheet-pdf' in x)
        
        if not link_tag:
            print(f"❌ Could not find {part_name}")
            return

        pdf_page_url = link_tag['href']
        
        # 3. Get Description
        # On this site, description is usually in the next <td> or text after the link
        description = link_tag.find_next('td').text.strip() if link_tag.find_next('td') else "Electronic Component"

        # 4. Go to the download page
        res = requests.get(pdf_page_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Look for the direct PDF link
        direct_link = soup.find('a', href=lambda x: x and x.endswith('.pdf'))
        
        if not direct_link:
            print("❌ Could not find direct PDF download link.")
            return

        final_url = direct_link['href']
        
        # 5. Download the PDF
        print(f"📡 Downloading: {final_url}")
        pdf_res = requests.get(final_url)
        
        if pdf_res.status_code == 200:
            local_path = os.path.join(DOWNLOAD_DIR, f"{part_name}.pdf")
            with open(local_path, "wb") as f:
                f.write(pdf_res.content)
            
            # 6. Update your lib.json
            update_json(part_name, description, local_path)
            print(f"✅ Success! Added {part_name}")
        else:
            print("❌ Download failed.")

    except Exception as e:
        print(f"Error: {e}")

def update_json(name, desc, path):
    data = {}
    if os.path.exists(LIB_FILE):
        with open(LIB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[name] = {"desc": desc, "category": "Scraped", "files": [path]}
    with open(LIB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# TEST
easy_scrape("LM358")
easy_scrape("2N2222")
