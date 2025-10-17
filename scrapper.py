import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

class MALegislatureScraper:
    def __init__(self):
        self.base_url = "https://malegislature.gov"
        self.session = requests.Session()
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_bills_page(self, page_number=1):
        """Scrape a single page of bills"""
        url = f"https://malegislature.gov/Bills/Search"
        params = {
            'SearchTerms': '',
            'Page': page_number,
            'Refinements[lawsgeneralcourt]': '3139347468202843757272656e7429%2C3139337264202832303233202d203230323429%2C3139326e64202832303231202d203230323229%2C3139317374202832303139202d203230323029%2C3139307468202832303137202d203230313829%2C3138397468202832303135202d203230313629%2C3138387468202832303133202d203230313429%2C3138377468202832303131202d203230313229'
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            bills = []
            
            # Find bill rows - adjust selector based on actual page structure
            bill_rows = soup.select('.bill-item, tr.bill-row, .search-result-item')
            
            for row in bill_rows:
                bill_data = self.extract_bill_data(row)
                if bill_data:
                    bills.append(bill_data)
            
            return bills
            
        except requests.RequestException as e:
            print(f"Error scraping page {page_number}: {e}")
            return []
    
    def extract_bill_data(self, row):
        """Extract data from a single bill row"""
        try:
            # These selectors may need adjustment based on the actual HTML structure
            bill = {}
            
            # Bill number and title
            bill_link = row.select_one('a[href*="/Bills/"]')
            if bill_link:
                bill['number'] = bill_link.text.strip()
                bill['url'] = self.base_url + bill_link['href']
                bill['title'] = bill_link.get('title', '').strip()
            
            # Sponsor information
            sponsor_elem = row.select_one('.sponsor, .author')
            if sponsor_elem:
                bill['sponsor'] = sponsor_elem.text.strip()
            
            # Status information
            status_elem = row.select_one('.status, .state')
            if status_elem:
                bill['status'] = status_elem.text.strip()
            
            # Date information
            date_elem = row.select_one('.date, .filed-date')
            if date_elem:
                bill['filed_date'] = date_elem.text.strip()
            
            return bill if bill else None
            
        except Exception as e:
            print(f"Error extracting bill data: {e}")
            return None
    
    def scrape_multiple_pages(self, start_page=1, end_page=5, delay=1):
        """Scrape multiple pages with delay between requests"""
        all_bills = []
        
        for page in range(start_page, end_page + 1):
            print(f"Scraping page {page}...")
            bills = self.scrape_bills_page(page)
            all_bills.extend(bills)
            
            # Be respectful - delay between requests
            time.sleep(delay)
            
            # Stop if no more bills found
            if not bills:
                print(f"No bills found on page {page}, stopping.")
                break
        
        return all_bills
    
    def save_to_csv(self, bills, filename="ma_legislature_bills.csv"):
        """Save scraped data to CSV"""
        df = pd.DataFrame(bills)
        df.to_csv(filename, index=False)
        print(f"Saved {len(bills)} bills to {filename}")

# Usage example
if __name__ == "__main__":
    scraper = MALegislatureScraper()
    
    # Scrape first 3 pages
    bills = scraper.scrape_multiple_pages(start_page=1, end_page=3)
    
    # Save results
    scraper.save_to_csv(bills)
    
    # Print summary
    print(f"Scraped {len(bills)} bills")
    for bill in bills[:5]:  # Show first 5 bills
        print(f"Bill: {bill.get('number')} - {bill.get('title')}")