# scripts/ma_bill_scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import os
from datetime import datetime

class MABillScraper:
    def __init__(self):
        self.base_url = "https://malegislature.gov"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Set up data directories
        self.data_dir = "data/states/massachusetts"
        self.raw_dir = f"{self.data_dir}/raw"
        self.processed_dir = f"{self.data_dir}/processed"
        
        # Create directories if they don't exist
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(f"{self.processed_dir}/individual_bills", exist_ok=True)
        os.makedirs(f"{self.processed_dir}/text_files", exist_ok=True)
    
    def get_existing_bill_ids(self):
        """Get set of all bill IDs that have already been scraped"""
        existing_ids = set()
        
        if os.path.exists(self.raw_dir):
            for filename in os.listdir(self.raw_dir):
                if filename.endswith('.json'):
                    # Extract bill ID from filename: "194th_H_2212.json" -> "H.2212"
                    match = re.match(r'(\w+)_([HS][D_]?\d+)\.json', filename)
                    if match:
                        session, bill_num = match.groups()
                        # Convert back to original format: "H_2212" -> "H.2212"
                        bill_id = bill_num.replace('_', '.')
                        existing_ids.add(bill_id)
        
        return existing_ids

    def should_scrape_bill(self, bill_data):
        """Check if we should scrape this bill (not already exists)"""
        existing_ids = self.get_existing_bill_ids()
        return bill_data['number'] not in existing_ids

    def load_existing_bills(self):
        """Load all existing bills from raw directory"""
        existing_bills = []
        
        if os.path.exists(self.raw_dir):
            for filename in os.listdir(self.raw_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.raw_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            bill_data = json.load(f)
                            existing_bills.append(bill_data)
                    except Exception as e:
                        print(f"⚠️ Error loading {filename}: {e}")
        
        return existing_bills

    def get_existing_text_files(self):
        """Get set of all bill IDs that already have text files"""
        existing_text = set()
        text_files_dir = f"{self.processed_dir}/text_files"
        
        if os.path.exists(text_files_dir):
            for filename in os.listdir(text_files_dir):
                if filename.endswith('.txt'):
                    # Extract bill ID: "194th_H_2212.txt" -> "H_2212"
                    match = re.match(r'\w+_([HS][D_]?\d+)\.txt', filename)
                    if match:
                        bill_id = match.group(1)  # "H_2212"
                        existing_text.add(bill_id)
        
        return existing_text

    def debug_page_content(self, page_number):
        """Debug what's actually on the page"""
        url = f"https://malegislature.gov/Bills/Search?SearchTerms=&Page={page_number}&Refinements%5Blawsgeneralcourt%5D=3139347468202843757272656e7429"
        
        print(f"🔍 DEBUG: Checking page {page_number}")
        print(f"🔍 URL: {url}")
        
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Save the page for inspection
            with open(f"debug_page_{page_number}.html", 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print(f"💾 Saved page content to debug_page_{page_number}.html")
            
            # Check for tables
            tables = soup.find_all('table')
            print(f"🔍 Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                print(f"🔍 Table {i}: {len(rows)} rows")
                
                # Show first few rows
                for j, row in enumerate(rows[:3]):
                    print(f"🔍 Row {j}: {len(row.find_all(['td', 'th']))} cells")
                    if row.find('td'):
                        cells = row.find_all('td')
                        for k, cell in enumerate(cells):
                            text = cell.get_text(strip=True)
                            links = cell.find_all('a')
                            print(f"🔍   Cell {k}: '{text[:50]}...' - {len(links)} links")
            
            # Check for bill links directly
            bill_links = soup.find_all('a', href=lambda x: x and '/Bills/' in x)
            print(f"🔍 Found {len(bill_links)} bill links")
            
            for link in bill_links[:5]:
                print(f"🔍   Bill link: '{link.get_text(strip=True)}' -> {link['href']}")
                
        except Exception as e:
            print(f"❌ Debug error: {e}")

    def scrape_basic_bill_info(self, start_page=1, end_page=2, skip_existing=True):
        """Get basic bill information from search results - 194th ONLY"""
        all_bills = []
        
        # Get existing bills to skip duplicates
        if skip_existing:
            existing_ids = self.get_existing_bill_ids()
            print(f"🔄 Found {len(existing_ids)} existing bills, skipping duplicates")
        
        for page in range(start_page, end_page + 1):
            print(f"📄 Getting basic info from page {page} (194th session only)...")
            
            url = f"https://malegislature.gov/Bills/Search?SearchTerms=&Page={page}&Refinements%5Blawsgeneralcourt%5D=3139347468202843757272656e7429"
            
            try:
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                table = soup.find('table')
                if not table:
                    print("❌ No table found on page")
                    continue
                
                rows = table.find_all('tr')
                print(f"🔍 Found {len(rows)} total rows in table")
                
                # Process all rows and let extract_basic_info handle filtering
                page_bills = []
                new_bills_count = 0
                skipped_bills_count = 0
                error_count = 0
                
                for i, row in enumerate(rows):
                    bill_data = self.extract_basic_info(row)
                    if bill_data:
                        # Check if we should scrape this bill
                        if skip_existing and not self.should_scrape_bill(bill_data):
                            skipped_bills_count += 1
                            print(f"  ⏭️  Skipping {bill_data['number']} (already exists)")
                            continue
                        
                        # Save each bill immediately
                        self.save_bill_data(bill_data)
                        page_bills.append(bill_data)
                        new_bills_count += 1
                        print(f"  ✅ {bill_data['number']}")
                    else:
                        error_count += 1
                
                all_bills.extend(page_bills)
                # Save progress after each page
                self.save_progress(page, len(page_bills))
                
                print(f"  📊 Page {page}: {new_bills_count} new bills, {skipped_bills_count} skipped, {error_count} errors")
                
                # Stop if no new bills found on page
                if new_bills_count == 0 and skipped_bills_count > 0:
                    print(f"💡 No new bills found on page {page}, you may have reached the end")
                    break
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error on page {page}: {e}")
        
        return all_bills

    def extract_basic_info(self, row):
        """Extract basic bill info from table row"""
        try:
            # Skip header rows
            if row.find('th'):
                return None
                
            cells = row.find_all('td')
            
            if len(cells) < 4:
                return None
            
            bill = {}
            
            # Cell 1: Bill number and link (index 1)
            bill_link = cells[1].find('a', href=True)
            if bill_link:
                bill_number = bill_link.get_text(strip=True)
                if bill_number:  # Make sure it's not empty
                    bill['number'] = bill_number
                    bill['detail_url'] = self.base_url + bill_link['href']
                else:
                    return None
            else:
                return None
            
            # Cell 2: Sponsor (index 2)
            sponsor_link = cells[2].find('a', href=True)
            if sponsor_link:
                bill['sponsor'] = sponsor_link.get_text(strip=True)
            
            # Cell 3: Bill title (index 3)
            title_link = cells[3].find('a', href=True)
            if title_link:
                bill['title'] = title_link.get_text(strip=True)
            
            # Since we're filtering for 194th session only
            bill['general_court'] = "194th (2023-2024)"
            
            return bill
            
        except Exception as e:
            print(f"⚠️ Error extracting basic info: {e}")
            return None

    def save_bill_data(self, bill_data):
        """Save bill data to organized raw data folder"""
        try:
            # Extract session from general_court field
            session_match = re.search(r'(\d+)(?:st|nd|rd|th)', bill_data.get('general_court', ''))
            session = session_match.group(0) if session_match else "unknown_session"
            
            bill_id = bill_data['number'].replace('.', '_')
            filename = f"{self.raw_dir}/{session}_{bill_id}.json"
            
            # Add metadata
            bill_data['metadata'] = {
                'scraped_at': datetime.now().isoformat(),
                'session': session,
                'bill_id': f"MA_{session}_{bill_id}",
                'data_version': '1.0'
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(bill_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved {bill_data['number']} to {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error saving bill data: {e}")
            return None

    def save_progress(self, page, bills_count):
        """Track scraping progress"""
        progress_file = f"{self.data_dir}/progress_log.csv"
        
        # Create progress file if it doesn't exist
        if not os.path.exists(progress_file):
            with open(progress_file, 'w') as f:
                f.write("timestamp,page,bills_scraped\n")
        
        # Log progress
        with open(progress_file, 'a') as f:
            f.write(f"{datetime.now()},{page},{bills_count}\n")
    
    def get_bill_text_final(self, bill_info):
        """Get bill text using the exact links we found in debug"""
        print(f"  📖 Getting text for {bill_info['number']}...")
        
        try:
            # First, get the detail page to find the text links
            response = self.session.get(bill_info['detail_url'])
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Strategy 1: Try "View Text" link first (usually the cleanest)
            view_text_url = self.find_text_link(soup, 'View Text')
            if view_text_url:
                text = self.get_text_from_url(view_text_url)
                if len(text) > 500:
                    bill_info['full_text'] = text
                    bill_info['text_source'] = 'view_text'
                    bill_info['text_url'] = view_text_url
                    bill_info['text_length'] = len(text)
                    print(f"    ✅ Got {len(text)} chars from View Text")
                    return bill_info
            
            # Strategy 2: Try "Print Preview" link
            print_url = self.find_text_link(soup, 'Print Preview')
            if print_url:
                text = self.get_text_from_url(print_url)
                if len(text) > 500:
                    bill_info['full_text'] = text
                    bill_info['text_source'] = 'print_preview'
                    bill_info['text_url'] = print_url
                    bill_info['text_length'] = len(text)
                    print(f"    ✅ Got {len(text)} chars from Print Preview")
                    return bill_info
            
            # Strategy 3: Try PDF link (we'll just record it exists)
            pdf_url = self.find_text_link(soup, 'Download PDF')
            if pdf_url:
                bill_info['full_text'] = f"PDF available at: {pdf_url}"
                bill_info['text_source'] = 'pdf'
                bill_info['text_url'] = pdf_url
                bill_info['text_length'] = 0
                print(f"    📎 PDF available: {pdf_url}")
                return bill_info
            
            # Strategy 4: Fallback to direct page text
            direct_text = self.extract_direct_text(soup)
            if len(direct_text) > 500:
                bill_info['full_text'] = direct_text
                bill_info['text_source'] = 'direct_page'
                bill_info['text_url'] = bill_info['detail_url']
                bill_info['text_length'] = len(direct_text)
                print(f"    ✅ Got {len(direct_text)} chars from direct page")
                return bill_info
            
            # If all strategies fail
            bill_info['full_text'] = "Could not extract bill text"
            bill_info['text_source'] = 'failed'
            bill_info['text_length'] = 0
            print(f"    ❌ Could not extract text")
            return bill_info
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            bill_info['full_text'] = f"Error: {str(e)}"
            bill_info['text_source'] = 'error'
            bill_info['text_length'] = 0
            return bill_info
    
    def find_text_link(self, soup, link_text):
        """Find specific text links like 'View Text', 'Print Preview', 'Download PDF'"""
        for link in soup.find_all('a', href=True):
            if link_text.lower() in link.get_text().lower():
                href = link['href']
                full_url = self.base_url + href if href.startswith('/') else href
                return full_url
        return None
    
    def get_text_from_url(self, url):
        """Get text from a specific URL (View Text, Print Preview, etc.)"""
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Clean the text
            text = self.extract_clean_text(soup)
            return text
            
        except Exception as e:
            print(f"      ⚠️ Error getting text from {url}: {e}")
            return ""
    
    def extract_clean_text(self, soup):
        """Extract and clean text from any bill text page"""
        # Remove scripts and styles
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()
        
        # Try to find the main content area
        content_selectors = [
            '.billDocument', '.legislation', '.document-content',
            '.billText', '.legislation-text', '#billText',
            '.content', '.main-content', '.container', 'body'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator='\n', strip=True)
                if len(text) > 500:
                    return self.clean_text(text)
        
        # Fallback to body text
        body = soup.find('body')
        if body:
            text = body.get_text(separator='\n', strip=True)
            return self.clean_text(text)
        
        return ""
    
    def extract_direct_text(self, soup):
        """Extract text directly from bill detail page as fallback"""
        content = soup.select_one('.content')
        if content:
            text = content.get_text(separator='\n', strip=True)
            return self.clean_text(text)
        return ""
    
    def clean_text(self, text):
        """Clean and format extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove common navigation and header text
        junk_patterns = [
            r'Home\s*›.*?›\s*Bill',
            r'Massachusetts General Court',
            r'Search Bills',
            r'Print this page',
            r'Share this page',
            r'Back to Bill'
        ]
        
        for pattern in junk_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def scrape_with_text(self, bills, sample_size=None, skip_existing=True):
        """Get text for bills, skipping those that already have text"""
        if sample_size is None:
            sample_size = len(bills)
        
        # Check for existing text files
        if skip_existing:
            existing_text_files = self.get_existing_text_files()
            bills_to_process = []
            for bill in bills[:sample_size]:
                bill_id = f"{bill['number'].replace('.', '_')}"
                if bill_id not in existing_text_files:
                    bills_to_process.append(bill)
                else:
                    print(f"  ⏭️  Skipping {bill['number']} (text already exists)")
            
            print(f"🔍 Getting text for {len(bills_to_process)} bills (skipped {sample_size - len(bills_to_process)} with existing text)...")
        else:
            bills_to_process = bills[:sample_size]
            print(f"🔍 Getting text for {len(bills_to_process)} bills...")
        
        results = []
        successful = 0
        
        for i, bill in enumerate(bills_to_process):
            print(f"  {i+1}/{len(bills_to_process)}: ", end="")
            bill_with_text = self.get_bill_text_final(bill)
            results.append(bill_with_text)
            
            if bill_with_text.get('text_source') in ['view_text', 'print_preview', 'direct_page']:
                successful += 1
            
            time.sleep(1)  # Be respectful
        
        print(f"\n📊 Text extraction results: {successful}/{len(bills_to_process)} successful")
        return results
    
    def save_results(self, bills, filename=None):
        """Save results to organized structure"""
        if not bills:
            print("No bills to save")
            return
        
        # Use default filename in processed directory
        if filename is None:
            filename = f"{self.processed_dir}/bills_metadata.csv"
        
        # Create CSV
        df = pd.DataFrame(bills)
        
        # Reorder columns for better readability
        preferred_order = ['number', 'title', 'sponsor', 'general_court', 'text_source', 'text_length']
        existing_columns = [col for col in preferred_order if col in df.columns]
        other_columns = [col for col in df.columns if col not in preferred_order]
        
        df = df[existing_columns + other_columns]
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"💾 Saved {len(bills)} bills to {filename}")
        
        # Save successful extractions to organized text files
        successful_bills = [b for b in bills if b.get('full_text') and len(b.get('full_text', '')) > 1000]
        if successful_bills:
            text_files_dir = f"{self.processed_dir}/text_files"
            os.makedirs(text_files_dir, exist_ok=True)
            
            for bill in successful_bills:
                # Extract session for better organization
                session_match = re.search(r'(\d+)(?:st|nd|rd|th)', bill.get('general_court', ''))
                session = session_match.group(0) if session_match else "unknown"
                
                filename = f"{text_files_dir}/{session}_{bill['number'].replace('.', '_')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Bill: {bill['number']}\n")
                    f.write(f"Title: {bill.get('title', '')}\n")
                    f.write(f"Sponsor: {bill.get('sponsor', '')}\n")
                    f.write(f"General Court: {bill.get('general_court', '')}\n")
                    f.write(f"Source: {bill.get('text_source', '')}\n")
                    f.write(f"URL: {bill.get('text_url', bill.get('detail_url', ''))}\n")
                    f.write("="*60 + "\n\n")
                    f.write(bill['full_text'])
            print(f"📁 Saved {len(successful_bills)} full text files to '{text_files_dir}'")
        
        # Print summary
        self.print_summary(bills)
    
    def print_summary(self, bills):
        """Print a summary of results"""
        print(f"\n📊 FINAL SUMMARY:")
        print(f"   Total bills processed: {len(bills)}")
        
        sources = {}
        for bill in bills:
            source = bill.get('text_source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print(f"   Text sources:")
        for source, count in sources.items():
            print(f"     {source}: {count}")
        
        bills_with_text = [b for b in bills if b.get('full_text') and len(b.get('full_text', '')) > 1000]
        print(f"   Bills with substantial text: {len(bills_with_text)}")
        
        if bills_with_text:
            print(f"\n🎯 First 5 successful bills:")
            for i, bill in enumerate(bills_with_text[:5]):
                print(f"   {i+1}. {bill['number']} ({bill.get('text_source', 'unknown')}): {bill['title'][:70]}...")

# Run the scraper
if __name__ == "__main__":
    print("🚀 MA Legislature Bill Scraper - Smart Data Collection")
    print("=" * 70)
    
    scraper = MABillScraper()
    
    # Check what we already have
    existing_bills = scraper.load_existing_bills()
    print(f"📊 Currently have {len(existing_bills)} bills in database")
    
    # Get basic bill info (with duplicate detection)
    print("\nPhase 1: Getting basic bill information...")
    bills = scraper.scrape_basic_bill_info(start_page=3, end_page=80, skip_existing=True)
    
    if bills:
        print(f"\n✅ Found {len(bills)} new bills")
        
        # Get text for bills (with duplicate detection)
        print("\nPhase 2: Getting full bill text...")
        bills_with_text = scraper.scrape_with_text(bills, skip_existing=True)
        
        # Save results
        scraper.save_results(bills_with_text)
        
        print(f"\n🎉 Data organized in: {scraper.data_dir}")
        print(f"   Raw bills: {scraper.raw_dir}/")
        print(f"   Processed data: {scraper.processed_dir}/")
        
        # Final summary
        all_bills_now = scraper.load_existing_bills()
        print(f"📈 Total bills in database: {len(all_bills_now)}")
    else:
        print("❌ No new bills found")