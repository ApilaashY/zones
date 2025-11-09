from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dataclasses import dataclass
from typing import List, Dict, Optional
import time

@dataclass
class InputField:
    element_type: str
    name: str
    id: str
    xpath: str
    value: str
    placeholder: str
    is_visible: bool
    is_enabled: bool
    attributes: Dict[str, str]

class WebScraper:
    def __init__(self, headless: bool = True):
        """
        Initialize the web scraper with Chrome WebDriver
        
        Args:
            headless: Run browser in headless mode (no GUI)
        """
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=self.options
        )
        self.wait = WebDriverWait(self.driver, 10)
    
    def get_page(self, url: str) -> None:
        """Navigate to the specified URL"""
        self.driver.get(url)
        time.sleep(2)  # Allow time for dynamic content to load
    
    def detect_input_fields(self) -> List[InputField]:
        """
        Enhanced detection of all interactive elements on the current page.
        Returns a list of InputField objects containing detailed field information.
        """
        input_fields = []
        
        # Wait for the page to be fully loaded
        try:
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        except:
            print("Warning: Page load not complete, continuing anyway...")
        
        # Define all possible interactive elements to detect
        element_selectors = [
            ('input', 'input'),
            ('textarea', 'textarea'),
            ('select', 'select'),
            ('button', 'button'),
            ('a', 'a[href]'),
            ('div', 'div[role="button"]'),
            ('div', 'div[role="textbox"]'),
            ('div', 'div[contenteditable="true"]'),
            ('div', 'div[role="combobox"]'),
            ('div', 'div[role="search"]'),
            ('div', 'div[role="slider"]'),
            ('div', 'div[role="spinbutton"]')
        ]
        
        for tag, selector in element_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"Found {len(elements)} elements matching: {selector}")
                
                for element in elements:
                    try:
                        # Skip elements that are not visible or not enabled
                        if not element.is_displayed() or not element.is_enabled():
                            continue
                            
                        # Get element properties safely
                        element_type = element.get_attribute('type') or tag
                        name = element.get_attribute('name') or element.get_attribute('id') or 'N/A'
                        element_id = element.get_attribute('id') or 'N/A'
                        value = element.get_attribute('value') or element.text or ''
                        placeholder = element.get_attribute('placeholder') or 'N/A'
                        
                        # Get all attributes
                        attributes = {}
                        try:
                            attrs = self.driver.execute_script(
                                "var items = {}; " +
                                "for (index = 0; index < arguments[0].attributes.length; ++index) { " +
                                "  items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value " +
                                "} " +
                                "return items;", 
                                element
                            )
                            attributes = attrs if attrs else {}
                        except:
                            pass
                        
                        # Get computed styles to check for visibility
                        try:
                            computed_style = self.driver.execute_script(
                                "return window.getComputedStyle(arguments[0])", 
                                element
                            )
                            if computed_style.getPropertyValue('display') == 'none' or \
                               computed_style.getPropertyValue('visibility') == 'hidden':
                                continue
                        except:
                            pass
                        
                        # Get element position and size
                        try:
                            location = element.location
                            size = element.size
                            attributes['position'] = f"x:{location['x']}, y:{location['y']}"
                            attributes['size'] = f"width:{size['width']}, height:{size['height']}"
                        except:
                            pass
                        
                        input_field = InputField(
                            element_type=element_type,
                            name=name,
                            id=element_id,
                            xpath=self._get_element_xpath(element),
                            value=value[:100],  # Limit value length
                            placeholder=placeholder,
                            is_visible=element.is_displayed(),
                            is_enabled=element.is_enabled(),
                            attributes=attributes
                        )
                        
                        # Only add if we have enough identifying information
                        if input_field.name != 'N/A' or input_field.id != 'N/A':
                            input_fields.append(input_field)
                            
                    except Exception as e:
                        print(f"Error processing element: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Error finding elements with selector {selector}: {str(e)}")
                continue
                
        print(f"Total input fields detected: {len(input_fields)}")
        return input_fields
    
    def _get_element_xpath(self, element) -> str:
        """Generate XPath for the given element"""
        return self.driver.execute_script("""
        function getElementXPath(element) {
            if (!element) return '';
            if (element.id) return `//*[@id="${element.id}"]`;
            if (element === document.body) return '/html/body';
            
            let ix = 0;
            const siblings = element.parentNode.childNodes;
            for (let i = 0; i < siblings.length; i++) {
                const sibling = siblings[i];
                if (sibling === element) {
                    return `${getElementXPath(element.parentNode)}/${element.tagName.toLowerCase()}[${ix + 1}]`;
                }
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                    ix++;
                }
            }
            return '';
        }
        return getElementXPath(arguments[0]);
        """, element)
    
    def fill_form(self, field_xpath: str, value: str) -> bool:
        """
        Fill a form field identified by XPath with the given value
        
        Args:
            field_xpath: XPath of the input field
            value: Value to fill in the field
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, field_xpath))
            )
            element.clear()
            element.send_keys(value)
            return True
        except Exception as e:
            print(f"Error filling form: {str(e)}")
            return False
    
    def click_element(self, xpath: str) -> bool:
        """
        Click an element identified by XPath
        
        Args:
            xpath: XPath of the element to click
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            return True
        except Exception as e:
            print(f"Error clicking element: {str(e)}")
            return False
    
    def get_page_source(self) -> str:
        """Get the current page source"""
        return self.driver.page_source
    
    def input_by_id(self, element_id: str, value: str, clear_first: bool = True, submit_form: bool = False) -> bool:
        """
        Input a value into a form field by its ID.
        
        Args:
            element_id: The ID of the input element
            value: The value to input
            clear_first: Whether to clear the field before inputting the value
            submit_form: Whether to submit the form after inputting the value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Wait for the element to be present and visible
            element = self.wait.until(
                EC.visibility_of_element_located((By.ID, element_id))
            )
            
            # Scroll the element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            
            # Clear the field if requested
            if clear_first:
                element.clear()
            
            # Input the value
            element.send_keys(value)
            print(f"Successfully input value into element with ID: {element_id}")
            
            # Submit the form if requested
            if submit_form:
                element.submit()
                print("Form submitted.")
            
            return True
            
        except Exception as e:
            print(f"Error inputting value to element with ID {element_id}: {str(e)}")
            return False
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

def main():
    # Example usage
    url = input("Enter the URL to scrape: ")
    
    # Initialize the scraper
    scraper = WebScraper(headless=False)  # Set to True for headless mode
    
    try:
        # Navigate to the page
        print(f"Navigating to {url}...")
        scraper.get_page(url)
        
        # Detect input fields
        print("\nDetecting input fields...")
        input_fields = scraper.detect_input_fields()
        
        # Print the results
        print(f"\nFound {len(input_fields)} input fields:")
        print("-" * 80)
        
        for i, field in enumerate(input_fields, 1):
            print(f"{i}. Type: {field.element_type}")
            print(f"   Name: {field.name}")
            print(f"   ID: {field.id}")
            print(f"   XPath: {field.xpath}")
            print(f"   Value: {field.value}")
            print(f"   Placeholder: {field.placeholder}")
            print(f"   Visible: {field.is_visible}")
            print(f"   Enabled: {field.is_enabled}")
            print("-" * 80)
        
        # Save results to a file
        with open('input_fields_report.txt', 'w', encoding='utf-8') as f:
            f.write(f"Input Fields Report for {url}\n")
            f.write("=" * 50 + "\n\n")
            
            for i, field in enumerate(input_fields, 1):
                f.write(f"{i}. Type: {field.element_type}\n")
                f.write(f"   Name: {field.name}\n")
                f.write(f"   ID: {field.id}\n")
                f.write(f"   XPath: {field.xpath}\n")
                f.write(f"   Value: {field.value}\n")
                f.write(f"   Placeholder: {field.placeholder}\n")
                f.write(f"   Visible: {field.is_visible}\n")
                f.write(f"   Enabled: {field.is_enabled}\n")
                f.write(f"   Attributes: {field.attributes}\n")
                f.write("-" * 50 + "\n\n")
            
            print("\nReport saved to 'input_fields_report.txt'")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Close the browser
        scraper.close()

if __name__ == "__main__":
    main()
