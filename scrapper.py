# final_working_scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

class FinalMABillScraper:
    def __init__(self):
        self.base_url = "https://malegislature.gov"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_basic_bill_info(self, start_page=1, end_page=2):
        """Get basic bill information from search results"""
        all_bills = []
        
        for page in range(start_page, end_page + 1):
            print(f"📄 Getting basic info from page {page}...")
            
            url = f"https://malegislature.gov/Bills/Search?SearchTerms=&Page=1&Refinements%5Blawsgeneralcourt%5D=3139347468202843757272656e7429%2C3139337264202832303233202d203230323429%2C3139326e64202832303231202d203230323229"
            
            try:
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                table = soup.find('table')
                if not table:
                    continue
                
                rows = table.find_all('tr')
                data_rows = [row for row in rows if row.find('td')]
                
                for row in data_rows:
                    bill_data = self.extract_basic_info(row)
                    if bill_data:
                        all_bills.append(bill_data)
                        print(f"  ✅ {bill_data['number']}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error on page {page}: {e}")
        
        return all_bills
    
    def extract_basic_info(self, row):
        """Extract basic bill info from table row"""
        try:
            cells = row.find_all('td')
            if len(cells) < 5:
                return None
            
            bill = {}
            bill['general_court'] = cells[1].get_text(strip=True)
            
            bill_link = cells[2].find('a', href=True)
            if bill_link:
                bill['number'] = bill_link.get_text(strip=True)
                bill['detail_url'] = self.base_url + bill_link['href']
            else:
                return None
            
            sponsor_link = cells[3].find('a', href=True)
            if sponsor_link:
                bill['sponsor'] = sponsor_link.get_text(strip=True)
            
            title_link = cells[4].find('a', href=True)
            if title_link:
                bill['title'] = title_link.get_text(strip=True)
            
            return bill
            
        except Exception as e:
            print(f"⚠️ Error extracting basic info: {e}")
            return None
    
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
                    print(f"    ✅ Got {len(text)} chars from Print Preview")
                    return bill_info
            
            # Strategy 3: Try PDF link (we'll just record it exists)
            pdf_url = self.find_text_link(soup, 'Download PDF')
            if pdf_url:
                bill_info['full_text'] = f"PDF available at: {pdf_url}"
                bill_info['text_source'] = 'pdf'
                bill_info['text_url'] = pdf_url
                print(f"    📎 PDF available: {pdf_url}")
                return bill_info
            
            # Strategy 4: Fallback to direct page text
            direct_text = self.extract_direct_text(soup)
            if len(direct_text) > 500:
                bill_info['full_text'] = direct_text
                bill_info['text_source'] = 'direct_page'
                print(f"    ✅ Got {len(direct_text)} chars from direct page")
                return bill_info
            
            # If all strategies fail
            bill_info['full_text'] = "Could not extract bill text"
            bill_info['text_source'] = 'failed'
            print(f"    ❌ Could not extract text")
            return bill_info
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            bill_info['full_text'] = f"Error: {str(e)}"
            bill_info['text_source'] = 'error'
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
    
    def scrape_with_text(self, bills, sample_size=None):
        """Get text for bills"""
        if sample_size is None:
            sample_size = len(bills)
        
        print(f"\n🔍 Getting text for {min(sample_size, len(bills))} bills...")
        
        results = []
        successful = 0
        
        for i, bill in enumerate(bills[:sample_size]):
            print(f"  {i+1}/{min(sample_size, len(bills))}: ", end="")
            bill_with_text = self.get_bill_text_final(bill)
            results.append(bill_with_text)
            
            if bill_with_text.get('text_source') in ['view_text', 'print_preview', 'direct_page']:
                successful += 1
            
            time.sleep(1)  # Be respectful
        
        print(f"\n📊 Text extraction results: {successful}/{min(sample_size, len(bills))} successful")
        return results
    
    def save_results(self, bills, filename="ma_bills_final.csv"):
        """Save results to CSV and individual files"""
        if not bills:
            print("No bills to save")
            return
        
        # Create CSV
        df = pd.DataFrame(bills)
        
        # Reorder columns for better readability
        preferred_order = ['number', 'title', 'sponsor', 'general_court', 'text_source', 'text_length']
        existing_columns = [col for col in preferred_order if col in df.columns]
        other_columns = [col for col in df.columns if col not in preferred_order]
        
        df = df[existing_columns + other_columns]
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"💾 Saved {len(bills)} bills to {filename}")
        
        # Save successful extractions to individual files
        successful_bills = [b for b in bills if b.get('full_text') and len(b.get('full_text', '')) > 1000]
        if successful_bills:
            import os
            os.makedirs('bills_text', exist_ok=True)
            for bill in successful_bills:
                filename = f"bills_text/{bill['number'].replace('.', '_')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Bill: {bill['number']}\n")
                    f.write(f"Title: {bill.get('title', '')}\n")
                    f.write(f"Sponsor: {bill.get('sponsor', '')}\n")
                    f.write(f"General Court: {bill.get('general_court', '')}\n")
                    f.write(f"Source: {bill.get('text_source', '')}\n")
                    f.write(f"URL: {bill.get('text_url', bill.get('detail_url', ''))}\n")
                    f.write("="*60 + "\n\n")
                    f.write(bill['full_text'])
            print(f"📁 Saved {len(successful_bills)} full text files to 'bills_text' folder")
        
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

# Run the final scraper
if __name__ == "__main__":
    print("🚀 FINAL MA Legislature Bill Scraper")
    print("Using exact text links found in debug")
    print("=" * 70)
    
    scraper = FinalMABillScraper()
    
    # Get basic bill info
    print("Phase 1: Getting basic bill information...")
    bills = scraper.scrape_basic_bill_info(start_page=1, end_page=2)
    
    if bills:
        print(f"\n✅ Found {len(bills)} bills")
        
        # Get text for all bills
        print("\nPhase 2: Getting full bill text...")
        bills_with_text = scraper.scrape_with_text(bills)
        
        # Save results
        scraper.save_results(bills_with_text)
    else:
        print("❌ No bills found")