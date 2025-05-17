import time
import csv
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class FacebookScraper:
    def __init__(self, email=None, password=None):
        self.email = email
        self.password = password
        self.driver = None
        self.setup_driver()
        
    def setup_driver(self):
        """Set up the Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--start-maximized")
        

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def login(self):
        """Login to Facebook with provided credentials."""
        if not self.email or not self.password:
            print("No login credentials provided. Continuing without login.")
            return False
            
        try:
            self.driver.get("https://www.facebook.com/")
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(string(), 'Accept') or contains(string(), 'Allow') or contains(string(), 'Accepter')]"))
                )
                cookie_button.click()
            except:
                print("No cookie dialog found or already accepted.")
            
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_field.send_keys(self.email)
            password_field = self.driver.find_element(By.ID, "pass")
            password_field.send_keys(self.password)
            
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='navigation']"))
            )
            print("Login successful!")
            return True
            
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    
    def search_hashtag(self, hashtag):
        """Search for posts with the given hashtag."""
        try:
            self.driver.get(f"https://www.facebook.com/hashtag/{hashtag}")
            time.sleep(15)  
            
            self._scroll_page(20)  
            
            return self._parse_posts()
            
        except Exception as e:
            print(f"Error searching hashtag: {str(e)}")
            return []
    
    def _scroll_page(self, scroll_count=3):
        """Scroll down the page to load more content."""
        for i in range(scroll_count):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(5, 8))  # 5-8 seconds between scrolls
            print(f"Scrolled {i+1}/{scroll_count} times")
        
            try:
                see_more_buttons = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'See More') or contains(text(), 'Voir plus')]")
                for button in see_more_buttons[:5]: 
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)
            except:
                pass
    
    def _parse_posts(self):
        """Parse the posts from the current page."""
        posts = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        post_elements = soup.find_all('div', {'class': 'x1yztbdb'})
        
        for post in post_elements:
            try:
                post_text_element = post.find('div', {'data-ad-preview': 'message'})
                post_text = post_text_element.get_text() if post_text_element else "No text found"
                
                date_element = post.find('span', {'class': 'x4k7w5x'})  
                post_date = date_element.get_text() if date_element else "No date found"
                
                author_element = post.find('span', {'class': 'x3nfvp2'}) 
                author = author_element.get_text() if author_element else "No author found"
                
                link_element = post.find('a', {'class': 'x1i10hfl'}) 
                post_url = link_element.get('href') if link_element else "No URL found"
                if post_url.startswith('/'):
                    post_url = 'https://www.facebook.com' + post_url
                
                posts.append({
                    'author': author,
                    'date': post_date,
                    'text': post_text,
                    'url': post_url
                })
                
            except Exception as e:
                print(f"Error parsing post: {str(e)}")
                continue
        
        print(f"Found {len(posts)} posts")
        return posts
    
    def save_to_csv(self, posts, filename="harcelement_posts.csv"):
        """Save the scraped posts to a CSV file."""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['author', 'date', 'text', 'url']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for post in posts:
                    writer.writerow(post)
                    
            print(f"Successfully saved {len(posts)} posts to {filename}")
            
        except Exception as e:
            print(f"Error saving to CSV: {str(e)}")
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")

def main():
    
    email = "tyassin375@gmail.com" 
    password = "58998503"  
    
    scraper = FacebookScraper(email, password)
    
    try:
        if email and password:
            scraper.login()
        
        posts = scraper.search_hashtag("harcèlement")
        
        if posts:
            scraper.save_to_csv(posts)
        else:
            print("No posts found.")
            
    finally:
        scraper.close()

if __name__ == "__main__":
    main()