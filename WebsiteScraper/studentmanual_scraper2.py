import os
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import re
from typing import Dict, List, Optional

class UChicagoManualParser:
    def __init__(self, base_url: str = "https://studentmanual.uchicago.edu/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.disallowed_paths = ["/admin/", "/limit.html", "/offline.html"]  # Paths to skip

    def is_allowed_url(self, url: str) -> bool:
        """Check if the URL is allowed."""
        return not any(disallowed in url for disallowed in self.disallowed_paths)

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage, ensuring it's allowed."""
        if not self.is_allowed_url(url):
            print(f"Skipping disallowed URL: {url}")
            return None
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None

    def extract_navigation(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract navigation links from the sidebar, skipping disallowed links."""
        nav_items = []
        sidebar = soup.find('div', class_='subnav')
        if sidebar:
            links = sidebar.find_all('a')
            for link in links:
                full_url = urljoin(self.base_url, link.get('href', ''))
                if self.is_allowed_url(full_url):  # Check if allowed before adding
                    nav_items.append({'title': link.text.strip(), 'url': full_url})
        return nav_items
    
    def download_pdfs(self, url: str, pdf_folder: str = "pdfs"):
        """Download all PDFs from the given URL and store them in a subfolder."""
        
        # Ensure the folder exists
        os.makedirs(pdf_folder, exist_ok=True)

        soup = self.fetch_page(url)
        if not soup:
            return

        # Find all PDF links (handling variations in href attributes)
        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href:  # Checks if the href contains '.pdf' anywhere
                full_url = urljoin(url, href)
                pdf_links.append(full_url)

        if not pdf_links:
            print("No PDFs found on the page.")
            return

        print(f"Found {len(pdf_links)} PDFs. Downloading...")

        for pdf_url in pdf_links:
            pdf_name = os.path.join(pdf_folder, os.path.basename(pdf_url.split("?")[0]))  # Strip URL params

            # Download the PDF
            try:
                response = self.session.get(pdf_url, stream=True)
                response.raise_for_status()
                with open(pdf_name, 'wb') as pdf_file:
                    for chunk in response.iter_content(1024):
                        pdf_file.write(chunk)
                print(f"Downloaded: {pdf_name}")
            except Exception as e:
                print(f"Error downloading {pdf_url}: {e}")

    def extract_main_content(self, soup: BeautifulSoup) -> Dict:
        """Extract main content from the page."""
        content = {
            'title': '',
            'breadcrumbs': [],
            'content_text': '',
            'sections': []
        }
        
        # Extract title
        title_elem = soup.find('h1')
        if title_elem:
            content['title'] = title_elem.text.strip()

        # Extract breadcrumbs
        breadcrumbs = soup.find('div', id='breadcrumbs')
        if breadcrumbs:
            content['breadcrumbs'] = [crumb.text.strip() for crumb in breadcrumbs.find_all(['a', 'span'])]

        # Extract main content
        main_content = soup.find('div', class_='main-content')
        if main_content:
            content['content_text'] = ' '.join([p.text.strip() for p in main_content.find_all(['p', 'li'])])
            
            # Extract sections with headers
            current_section = None
            for elem in main_content.find_all(recursive=False):  # Use recursive=False to avoid nested parsing issues
                if elem.name in ['h2', 'h3', 'h4']:
                    if current_section:
                        content['sections'].append(current_section)
                    current_section = {
                        'header': elem.text.strip(),
                        'content': '',
                        'level': int(elem.name[1])
                    }
                elif current_section and elem.name in ['p', 'ul', 'ol']:
                    current_section['content'] += ' ' + elem.text.strip()
            
            if current_section:
                content['sections'].append(current_section)

        return content

    def process_section(self, url: str) -> Dict:
        """Process a main section page and its subsections."""
        result = {
            'url': url,
            'title': '',
            'overview': '',
            'subsections': []
        }

        soup = self.fetch_page(url)
        if not soup:
            return result

        # Extract basic page info
        main_content = self.extract_main_content(soup)
        result['title'] = main_content['title']
        result['overview'] = main_content['content_text']

        # Get subsection links
        nav_items = self.extract_navigation(soup)
        
        # Process each subsection
        for nav_item in nav_items:
            subsection_soup = self.fetch_page(nav_item['url'])
            if subsection_soup:
                subsection_content = self.extract_main_content(subsection_soup)
                result['subsections'].append({
                    'url': nav_item['url'],
                    'title': subsection_content['title'],
                    'content': subsection_content['content_text'],
                    'sections': subsection_content['sections']
                })

        return result

    def generate_rag_documents(self, section_url: str) -> List[Dict]:
        """Generate RAG-suitable documents from a section."""
        documents = []
        # Download PDFs if section is disciplinary reports
        if "disciplinary-reports" in section_url:
            self.download_pdfs(section_url)
            return documents
        
        section_data = self.process_section(section_url)
        
        # Create document for main section overview
        if section_data['overview']:
            documents.append({
                'id': re.sub(r'[^\w\-_]', '-', section_data['url']),  # Fix regex
                'url': section_data['url'],
                'title': section_data['title'],
                'content': section_data['overview'],
                'type': 'overview',
                'metadata': {
                    'section': section_data['title'],
                    'subsection': None
                }
            })
        
        # Create documents for each subsection
        for subsection in section_data['subsections']:
            # Main subsection content
            documents.append({
                'id': re.sub(r'[^\w\-_]', '-', subsection['url']),
                'url': subsection['url'],
                'title': subsection['title'],
                'content': subsection['content'],
                'type': 'subsection',
                'metadata': {
                    'section': section_data['title'],
                    'subsection': subsection['title']
                }
            })
            
            # Individual sections within subsection
            for i, section in enumerate(subsection.get('sections', [])):
                # Precompute the cleaned URL to avoid backslash issues in f-string
                cleaned_url = re.sub(r"[^\w\-_]", "-", subsection["url"])

                # Then use it inside the f-string safely
                documents.append({
                    'id': f"{cleaned_url}-section-{i}",
                    'url': subsection['url'],
                    'title': f"{subsection['title']} - {section['header']}",
                    'content': section['content'],
                    'type': 'section',
                    'metadata': {
                        'section': section_data['title'],
                        'subsection': subsection['title'],
                        'section_header': section['header'],
                        'section_level': section['level']
                    }
                })
        return documents

def main():
    parser = UChicagoManualParser()
    
    # List of main section URLs to process
    sections = [
        "https://studentmanual.uchicago.edu/university-policies/",
        "https://studentmanual.uchicago.edu/academic-policies/",
        "https://studentmanual.uchicago.edu/administrative-policies/",
        "https://studentmanual.uchicago.edu/student-life-conduct/",
        "https://studentmanual.uchicago.edu/disciplinary-reports/"
    ]
    
    all_documents = []
    
    # Process each main section
    for section_url in sections:
        documents = parser.generate_rag_documents(section_url)
        all_documents.extend(documents)
        
        # Save individual section documents
        section_name = section_url.rstrip('/').split('/')[-1]
        with open(f'{section_name}.json', 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
    
    # Save all documents combined
    with open('all_manual_documents.json', 'w', encoding='utf-8') as f:
        json.dump(all_documents, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
