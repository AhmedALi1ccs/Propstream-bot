import streamlit as st
from playwright.sync_api import sync_playwright
import pandas as pd
import time
import os
import re
from datetime import datetime

# Install Playwright browsers (required for deployment)
os.system("playwright install chromium")

# Streamlit App Title
st.title("PropStream Property Data Scraper")
st.write("Upload a CSV file with property addresses to scrape data from PropStream")

# File upload
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    # Read the CSV
    try:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded data:")
        st.dataframe(df.head())
        
        # Check if required column exists
        address_columns = [col for col in df.columns if 'address' in col.lower()]
        
        if not address_columns:
            st.error("No 'address' column found in the CSV. Please ensure your CSV has a column containing property addresses.")
        else:
            # Let user select the address column
            selected_column = st.selectbox("Select the property address column:", address_columns)
            
            # Show processing options
            st.subheader("Processing Options")
            max_properties = st.number_input("Maximum properties to process (0 for all):", min_value=0, value=5)
            debug_mode = st.checkbox("Enable debug mode (shows detailed logs)", value=False)
            headless_mode = st.checkbox("Run browser in background (headless)", value=True)
            
            run_button = st.button("Start Scraping")
            
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
        run_button = False

# PropStream credentials
PROPSTREAM_USERNAME = "noah@goccs.net"
PROPSTREAM_PASSWORD = "Propstream!12345"

def clean_currency_value(value):
    """Clean currency values to a standard format"""
    if not value or str(value).strip().lower() in ['n/a', 'na', '']:
        return 'N/A'
    
    # Extract dollar amount
    match = re.search(r'\$[\d,]+', str(value))
    if match:
        return match.group()
    
    # If no dollar sign, but contains numbers
    match = re.search(r'[\d,]+', str(value))
    if match:
        return f"${match.group()}"
    
    return 'N/A'

def clean_numeric_value(value):
    """Clean numeric values (beds, baths)"""
    if not value or str(value).strip().lower() in ['n/a', 'na', '']:
        return 'N/A'
    
    # Extract numeric value including decimals
    match = re.search(r'\d+\.?\d*', str(value))
    if match:
        return match.group()
    
    return 'N/A'

def check_and_click_proceed_button(page, debug_mode=False):
    """
    Check for and click the 'Proceed' button if it appears
    Returns True if button was found and clicked, False otherwise
    """
    try:
        proceed_selectors = [
            'button:has-text("Proceed")',
            'button[class*="button"]:has-text("Proceed")',
            '.src-components-Button-style__cuWaY__button:has-text("Proceed")',
            'button[type="button"]:has-text("Proceed")'
        ]
        
        for selector in proceed_selectors:
            try:
                proceed_button = page.locator(selector).first
                if proceed_button.is_visible(timeout=2000):
                    if debug_mode:
                        st.info("🔘 Found 'Proceed' button, clicking it...")
                    proceed_button.click()
                    time.sleep(2)  # Wait for any redirect/loading
                    if debug_mode:
                        st.success("✅ 'Proceed' button clicked successfully")
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        if debug_mode:
            print(f"Error checking for proceed button: {str(e)}")
        return False

def wait_for_search_input(page, debug_mode=False, timeout=60):
    """
    Wait for the search input field to become available after login
    Returns True if found, False if timeout
    """
    search_selectors = [
        'input[placeholder*="County" i]',  # "Enter County, City, Zip Code(s) or APN #"
        'input[placeholder*="City" i]',
        'input[placeholder*="Zip Code" i]',
        'input[placeholder*="APN" i]',
        'input[aria-controls*="react-autowhatever"]',  # aria-controls="react-autowhatever-1"
        'input[type="text"][autocomplete="off"]',  # type="text" autocomplete="off"
        'input[aria-autocomplete="list"]',  # aria-autocomplete="list"
        'input[id*="application_id"]',  # id starts with "application_id"
        'input[type="text"]'  # fallback to any text input
    ]
    
    start_time = time.time()
    attempt = 1
    
    while time.time() - start_time < timeout:
        if debug_mode:
            st.info(f"🔍 Attempt {attempt}: Looking for search input field...")
        
        # First check for proceed button
        if check_and_click_proceed_button(page, debug_mode):
            time.sleep(3)  # Wait for page to load after clicking proceed
        
        for i, selector in enumerate(search_selectors):
            try:
                if debug_mode:
                    print(f"Trying selector {i+1}: {selector}")
                
                locator = page.locator(selector).first
                
                # Check if element exists and is visible/enabled
                if locator.count() > 0:
                    try:
                        locator.wait_for(state='visible', timeout=3000)
                        if locator.is_visible() and locator.is_enabled():
                            if debug_mode:
                                st.success(f"✅ Found search input with selector: {selector}")
                            return True
                    except:
                        continue
                        
            except Exception as e:
                if debug_mode:
                    print(f"Selector {selector} failed: {str(e)}")
                continue
        
        # Wait before next attempt
        time.sleep(2)
        attempt += 1
        
        # Update page state
        try:
            page.wait_for_load_state('networkidle', timeout=3000)
        except:
            pass
    
    if debug_mode:
        st.error(f"❌ Could not find search input after {timeout} seconds")
    return False

def find_search_input(page, debug_mode=False):
    """
    Find and return the search input element
    Returns the locator if found, None otherwise
    """
    # First check for proceed button
    check_and_click_proceed_button(page, debug_mode)
    
    search_selectors = [
        'input[placeholder*="County" i]',
        'input[placeholder*="City" i]',
        'input[placeholder*="Zip Code" i]',
        'input[placeholder*="APN" i]',
        'input[aria-controls*="react-autowhatever"]',
        'input[type="text"][autocomplete="off"]',
        'input[aria-autocomplete="list"]',
        'input[id*="application_id"]',
        'input[type="text"]'
    ]
    
    for i, selector in enumerate(search_selectors):
        try:
            if debug_mode:
                print(f"Trying selector {i+1}: {selector}")
            
            locator = page.locator(selector).first
            
            # Wait for the element
            locator.wait_for(state='visible', timeout=5000)
            
            if locator.is_visible() and locator.is_enabled():
                if debug_mode:
                    print(f"✅ Found search input with: {selector}")
                return locator
                
        except Exception as e:
            if debug_mode:
                print(f"Selector failed: {str(e)}")
            continue
    
    return None

def perform_login(page, debug_mode=False):
    """
    Handle the login process to PropStream
    Returns True if successful, False otherwise
    """
    try:
        if debug_mode:
            st.info("🔐 Navigating to PropStream login page...")
        
        # Navigate to login page
        page.goto("https://login.propstream.com/")
        page.wait_for_load_state('networkidle')
        time.sleep(3)
        
        # Wait for login form
        page.wait_for_selector('input[name="username"]', timeout=10000)
        
        # Fill username
        username_input = page.locator('input[name="username"]')
        username_input.fill(PROPSTREAM_USERNAME)
        
        # Fill password  
        password_input = page.locator('input[name="password"]')
        password_input.fill(PROPSTREAM_PASSWORD)
        
        if debug_mode:
            st.info("📝 Credentials entered, submitting login form...")
        
        # Submit form
        password_input.press('Enter')
        
        # Wait for redirect with multiple possible outcomes
        try:
            # Wait for either successful redirect or error
            page.wait_for_function(
                "() => window.location.href.includes('app.propstream.com') || document.querySelector('.error-message, .alert-danger')",
                timeout=15000
            )
            
            # Check if we're on the app page
            if 'app.propstream.com' in page.url:
                if debug_mode:
                    st.success("✅ Successfully logged into PropStream!")
                return True
            else:
                # Check for error messages
                error_selectors = ['.error-message', '.alert-danger', '.error', '[class*="error"]']
                error_found = False
                for selector in error_selectors:
                    try:
                        error_elem = page.locator(selector).first
                        if error_elem.is_visible():
                            error_text = error_elem.inner_text()
                            st.error(f"Login failed: {error_text}")
                            error_found = True
                            break
                    except:
                        continue
                
                if not error_found:
                    st.error("Login failed - unknown error. Please check credentials.")
                return False
                
        except Exception as e:
            st.error(f"Login timeout or error: {str(e)}")
            return False
            
    except Exception as e:
        st.error(f"Failed to find login form: {str(e)}")
        return False

def scrape_propstream_data(addresses_df, address_column, max_properties, debug_mode=False, headless_mode=True):
    """Scrapes property data from PropStream for the given addresses."""
    
    with sync_playwright() as p:
        try:
            # Launch browser with configurable headless mode
            browser = p.chromium.launch(
                headless=headless_mode,
                args=['--no-sandbox', '--disable-dev-shm-usage'] if headless_mode else []
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )
            page = context.new_page()
            
            # Enable debug logging if requested
            if debug_mode:
                page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
                page.on("response", lambda response: print(f"Response: {response.status} {response.url}") if debug_mode else None)
            
            # Perform login
            if not perform_login(page, debug_mode):
                st.error("❌ Login failed. Cannot proceed with scraping.")
                browser.close()
                return None
            
            # Wait for search input to be available instead of hardcoded wait
            st.info("🔍 Waiting for PropStream app to load and search input to become available...")
            
            if wait_for_search_input(page, debug_mode, timeout=60):
                st.success("✅ PropStream app loaded and ready for searching!")
            else:
                st.error("❌ Timeout waiting for search input. PropStream may not have loaded properly.")
                browser.close()
                return None
            
            # Determine how many properties to process
            total_properties = len(addresses_df) if max_properties == 0 else min(max_properties, len(addresses_df))
            
            # Initialize results list
            results = []
            
            # Progress bar
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            
            # Process each property
            for index, row in addresses_df.head(total_properties).iterrows():
                address = str(row[address_column]).strip()
                
                if pd.isna(address) or address == '':
                    continue
                
                status_placeholder.info(f"Processing property {index + 1}/{total_properties}: {address}")
                
                try:
                    # Search for property
                    property_data = search_and_extract_property_data(page, address, debug_mode)
                    
                    if property_data:
                        # Combine original row data with scraped data
                        result_row = row.to_dict()
                        
                        # Add PropStream data with prefixes
                        for key, value in property_data.items():
                            result_row[f'propstream_{key}'] = value
                        
                        results.append(result_row)
                        
                        # Show progress
                        estimated_value = property_data.get('estimated_value', 'N/A')
                        beds = property_data.get('beds', 'N/A')
                        baths = property_data.get('baths', 'N/A')
                        open_mortgages = property_data.get('open_mortgages', 'N/A')
                        estimated_balance = property_data.get('estimated_balance', 'N/A')
                        lender_1 = property_data.get('lender_1_name', 'N/A')
                        
                        st.write(f"✅ {address} - Est. Value: {estimated_value}, Beds: {beds}, Baths: {baths}, Mortgages: {open_mortgages}, Balance: {estimated_balance}, Primary Lender: {lender_1}")
                        
                        if debug_mode:
                            st.json(property_data)  # Show all extracted data in debug mode
                            
                    else:
                        st.write(f"❌ Failed to extract data for: {address}")
                        
                        # Still add the original row with N/A values
                        result_row = row.to_dict()
                        empty_data = {
                            'estimated_value': 'N/A', 'last_sale_public_record': 'N/A',
                            'last_sale_date': 'N/A', 'mls_value': 'N/A', 
                            'document_type': 'N/A', 'beds': 'N/A', 'baths': 'N/A',
                            'open_mortgages': 'N/A', 'estimated_balance': 'N/A',
                            'involuntary_liens': 'N/A', 'involuntary_amount': 'N/A',
                            'lender_1_name': 'N/A', 'lender_1_rate': 'N/A',
                            'lender_2_name': 'N/A', 'lender_2_rate': 'N/A',
                            'lender_3_name': 'N/A', 'lender_3_rate': 'N/A'
                        }
                        for key, value in empty_data.items():
                            result_row[f'propstream_{key}'] = value
                        results.append(result_row)
                        
                except Exception as e:
                    error_msg = f"❌ Error processing {address}: {str(e)}"
                    st.write(error_msg)
                    if debug_mode:
                        st.exception(e)  # Show full stack trace in debug mode
                    
                # Update progress
                progress_bar.progress((index + 1) / total_properties)
                
                # Small delay to be respectful to the server
                time.sleep(2)
            
            browser.close()
            return pd.DataFrame(results) if results else None
            
        except Exception as e:
            st.error(f"Critical error during scraping: {str(e)}")
            return None

# Global debug flag
DEBUG_MODE = False

def debug_print(message):
    """Print debug message if debug mode is enabled"""
    if DEBUG_MODE:
        print(f"DEBUG: {message}")

def search_and_extract_property_data(page, address, debug_mode=False):
    """Search for a property and extract its data"""
    try:
        debug_print(f"Searching for: {address}")
        debug_print(f"Current page: {page.url}")
        
        # Use the helper function to find search input
        search_input = find_search_input(page, debug_mode)
        
        if not search_input:
            debug_print("❌ Could not find search input")
            return None
                
        # Clear and search for the address
        debug_print(f"Entering address: {address}")
        
        # Clear the input
        search_input.click()
        search_input.fill('')
        time.sleep(1)
        
        # Type the address
        search_input.type(address)
        time.sleep(3)  # Wait for suggestions
        
        # Look for and click first suggestion
        suggestion_selectors = [
            'li[role="option"]:first-child',
            '.react-autosuggest__suggestion:first-child', 
            'li[data-suggestion-index="0"]',
            '[class*="suggestion"]:first-child'
        ]
        
        suggestion_clicked = False
        for selector in suggestion_selectors:
            try:
                suggestion = page.locator(selector).first
                if suggestion.is_visible(timeout=3000):
                    suggestion.click()
                    suggestion_clicked = True
                    debug_print(f"✅ Clicked suggestion: {selector}")
                    break
            except:
                continue
        
        if not suggestion_clicked:
            debug_print("No suggestions found, pressing Enter...")
            search_input.press('Enter')
        
        # Wait for property page to load
        time.sleep(5)
        
        # Click Details button and extract data
        if click_details_button(page):
            debug_print("✅ Details button clicked, waiting for popup to load...")
            
            # Wait longer for the Details popup to fully load
            time.sleep(8)  # Increased wait time for popup to load
            
            # Additional wait to ensure all content is loaded
            try:
                # Wait for any element that indicates the popup is loaded
                page.wait_for_selector('[class*="name"]:has-text("Estimated Value"), [class*="label"]', timeout=5000)
                debug_print("✅ Popup content detected")
            except:
                debug_print("⚠️ Popup content not detected, but proceeding...")
            
            data = extract_property_details(page)
            
            # Close popup
            try:
                page.keyboard.press('Escape')
                time.sleep(1)
            except:
                pass
                
            return data
        else:
            debug_print("❌ Could not find Details button")
            return None
        
    except Exception as e:
        debug_print(f"Error in search_and_extract_property_data: {str(e)}")
        return None

def click_details_button(page):
    """Click the Details button"""
    try:
        # Look for Details button
        buttons = page.locator('button, span').all()
        
        for button in buttons:
            try:
                text = button.inner_text().lower()
                if 'details' in text:
                    button.click()
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        print(f"Error clicking details button: {str(e)}")
        return False

def click_mortgage_tab(page, debug_mode=False):
    """
    Click on the Mortgage & Transaction History tab
    Returns True if successful, False otherwise
    """
    try:
        # Look for the Mortgage & Transaction History tab
        tab_selectors = [
            'li[role="tab"]:has-text("Mortgage")',
            'li.react-tabs__tab:has-text("Mortgage")',
            '[data-rttab="true"]:has-text("Mortgage")',
            'li:has-text("Mortgage & Transaction History")',
            '.src-app-Property-Detail-style__adoa___tab:has-text("Mortgage")'
        ]
        
        for selector in tab_selectors:
            try:
                tab_element = page.locator(selector).first
                if tab_element.is_visible(timeout=3000):
                    if debug_mode:
                        st.info("🏠 Clicking Mortgage & Transaction History tab...")
                    tab_element.click()
                    time.sleep(3)  # Wait for tab content to load
                    if debug_mode:
                        st.success("✅ Mortgage tab clicked successfully")
                    return True
            except:
                continue
        
        if debug_mode:
            st.warning("⚠️ Could not find Mortgage & Transaction History tab")
        return False
        
    except Exception as e:
        if debug_mode:
            print(f"Error clicking mortgage tab: {str(e)}")
        return False

def extract_mortgage_data(page, debug_mode=False):
    """
    Extract mortgage data from the AG Grid table
    Returns dictionary with lender names and rates
    """
    try:
        mortgage_data = {}
        
        # Wait for the AG Grid to load
        try:
            page.wait_for_selector('.ag-center-cols-container', timeout=10000)
            time.sleep(2)  # Additional wait for data to populate
        except:
            if debug_mode:
                st.warning("⚠️ Mortgage table not found or didn't load")
            return mortgage_data
        
        # Extract data from AG Grid rows
        rows = page.locator('.ag-row').all()
        
        lender_count = 0
        for row in rows:
            try:
                # Check if this row has mortgage data
                lender_cell = row.locator('[col-id="lenderName"]').first
                rate_cell = row.locator('[col-id="loanInterestRate"]').first
                
                if lender_cell.count() > 0 and rate_cell.count() > 0:
                    lender_name = lender_cell.inner_text().strip()
                    interest_rate = rate_cell.inner_text().strip()
                    
                    # Only add if we have actual data
                    if lender_name and lender_name != '' and interest_rate and interest_rate != '':
                        lender_count += 1
                        mortgage_data[f'lender_{lender_count}_name'] = lender_name
                        mortgage_data[f'lender_{lender_count}_rate'] = interest_rate
                        
                        if debug_mode:
                            st.info(f"📊 Found Lender {lender_count}: {lender_name} at {interest_rate}")
                            
            except Exception as e:
                if debug_mode:
                    print(f"Error processing mortgage row: {str(e)}")
                continue
        
        # If no lenders found using AG Grid, try alternative approach
        if lender_count == 0:
            if debug_mode:
                st.info("🔍 Trying alternative approach to find mortgage data...")
            
            # Look for lender names in cell values
            lender_cells = page.locator('[aria-describedby*="lenderName"]').all()
            rate_cells = page.locator('[aria-describedby*="loanInterestRate"]').all()
            
            for i, (lender_cell, rate_cell) in enumerate(zip(lender_cells, rate_cells), 1):
                try:
                    lender_name = lender_cell.inner_text().strip()
                    interest_rate = rate_cell.inner_text().strip()
                    
                    if lender_name and lender_name != '' and interest_rate and interest_rate != '':
                        mortgage_data[f'lender_{i}_name'] = lender_name
                        mortgage_data[f'lender_{i}_rate'] = interest_rate
                        lender_count += 1
                        
                        if debug_mode:
                            st.info(f"📊 Found Lender {i}: {lender_name} at {interest_rate}")
                            
                except Exception as e:
                    if debug_mode:
                        print(f"Error in alternative approach: {str(e)}")
                    continue
        
        if debug_mode and lender_count == 0:
            st.warning("⚠️ No mortgage data found in table")
        elif debug_mode:
            st.success(f"✅ Successfully extracted data for {lender_count} lenders")
            
        return mortgage_data
        
    except Exception as e:
        if debug_mode:
            print(f"Error extracting mortgage data: {str(e)}")
        return {}

def extract_financial_data(page, field_name):
    """
    Extract financial data from the property details popup
    Looks for the field name and returns the corresponding label value
    """
    try:
        # Look for the specific field name
        name_elements = page.locator(f'text={field_name}').all()
        
        for elem in name_elements:
            try:
                # Check if this is within the financial values section
                parent = elem.locator('xpath=..')
                
                # Look for the label sibling
                label_elem = parent.locator('[class*="label"]').first
                if label_elem.is_visible():
                    value = label_elem.inner_text().strip()
                    if field_name in ["Estimated Balance", "Involuntary Amount"]:
                        return clean_currency_value(value)
                    else:
                        return clean_numeric_value(value)
            except:
                continue
                
        return 'N/A'
        
    except Exception as e:
        print(f"Error extracting {field_name}: {str(e)}")
        return 'N/A'

def extract_property_details(page):
    """Extract property details from the popup"""
    try:
        data = {}
        
        # Extract estimated value
        try:
            estimated_elements = page.locator('text=Estimated Value').all()
            for elem in estimated_elements:
                try:
                    parent = elem.locator('xpath=..')
                    labels = parent.locator('[class*="label"]').all()
                    if labels:
                        data['estimated_value'] = clean_currency_value(labels[0].inner_text())
                        break
                except:
                    continue
        except:
            data['estimated_value'] = 'N/A'
        
        # Extract last sale public record
        try:
            public_record_elements = page.locator('text=Public Record').all()
            for elem in public_record_elements:
                try:
                    parent = elem.locator('xpath=..')
                    labels = parent.locator('[class*="label"]').all()
                    if labels:
                        text = labels[0].inner_text()
                        price_match = re.search(r'\$[\d,]+', text)
                        data['last_sale_public_record'] = price_match.group() if price_match else 'N/A'
                        
                        # Extract date
                        date_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
                        data['last_sale_date'] = date_match.group() if date_match else 'N/A'
                        break
                except:
                    continue
        except:
            data['last_sale_public_record'] = 'N/A'
            data['last_sale_date'] = 'N/A'
        
        # Extract MLS value
        try:
            mls_elements = page.locator('text=MLS').all()
            for elem in mls_elements:
                try:
                    parent = elem.locator('xpath=..')
                    labels = parent.locator('[class*="label"]').all()
                    if labels:
                        data['mls_value'] = labels[0].inner_text().strip()
                        break
                except:
                    continue
        except:
            data['mls_value'] = 'N/A'
        
        # Extract document type
        try:
            doc_elements = page.locator('text=Document Type').all()
            for elem in doc_elements:
                try:
                    parent = elem.locator('xpath=..')
                    labels = parent.locator('[class*="label"]').all()
                    if labels:
                        data['document_type'] = labels[0].inner_text().strip()
                        break
                except:
                    continue
        except:
            data['document_type'] = 'N/A'
        
        # Extract beds
        try:
            bed_elements = page.locator('text=Beds').all()
            for elem in bed_elements:
                try:
                    # Look for sibling spans
                    parent = elem.locator('xpath=..')
                    spans = parent.locator('span').all()
                    for span in spans:
                        text = span.inner_text()
                        if text.isdigit():
                            data['beds'] = text
                            break
                    if 'beds' in data:
                        break
                except:
                    continue
        except:
            data['beds'] = 'N/A'
        
        # Extract baths
        try:
            bath_elements = page.locator('text=Baths').all()
            for elem in bath_elements:
                try:
                    # Look for sibling spans
                    parent = elem.locator('xpath=..')
                    spans = parent.locator('span').all()
                    for span in spans:
                        text = span.inner_text()
                        if re.match(r'\d+\.?\d*', text):
                            data['baths'] = text
                            break
                    if 'baths' in data:
                        break
                except:
                    continue
        except:
            data['baths'] = 'N/A'
        
        # Extract financial/lien data
        data['open_mortgages'] = extract_financial_data(page, 'Open Mortgages')
        data['estimated_balance'] = extract_financial_data(page, 'Estimated Balance')
        data['involuntary_liens'] = extract_financial_data(page, 'Involuntary Liens')
        data['involuntary_amount'] = extract_financial_data(page, 'Involuntary Amount')
        
        # Extract detailed mortgage data by clicking on Mortgage tab
        if click_mortgage_tab(page, DEBUG_MODE):
            mortgage_data = extract_mortgage_data(page, DEBUG_MODE)
            data.update(mortgage_data)  # Add all mortgage data to main data dict
        
        # Set defaults for any missing data
        default_keys = ['estimated_value', 'last_sale_public_record', 'last_sale_date', 
                       'mls_value', 'document_type', 'beds', 'baths',
                       'open_mortgages', 'estimated_balance', 'involuntary_liens', 'involuntary_amount']
        for key in default_keys:
            if key not in data:
                data[key] = 'N/A'
        
        # Ensure we have at least 3 potential lender slots (common scenario)
        for i in range(1, 4):
            if f'lender_{i}_name' not in data:
                data[f'lender_{i}_name'] = 'N/A'
            if f'lender_{i}_rate' not in data:
                data[f'lender_{i}_rate'] = 'N/A'
        
        return data
        
    except Exception as e:
        print(f"Error extracting property details: {str(e)}")
        return {
            'estimated_value': 'N/A', 'last_sale_public_record': 'N/A',
            'last_sale_date': 'N/A', 'mls_value': 'N/A',
            'document_type': 'N/A', 'beds': 'N/A', 'baths': 'N/A',
            'open_mortgages': 'N/A', 'estimated_balance': 'N/A',
            'involuntary_liens': 'N/A', 'involuntary_amount': 'N/A',
            'lender_1_name': 'N/A', 'lender_1_rate': 'N/A',
            'lender_2_name': 'N/A', 'lender_2_rate': 'N/A',
            'lender_3_name': 'N/A', 'lender_3_rate': 'N/A'
        }

# Run Scraper if Button is Pressed
if uploaded_file is not None and 'run_button' in locals() and run_button:
    st.info("Starting the PropStream scraping process...")
    
    # Set global debug flag
    DEBUG_MODE = debug_mode
    
    results_df = scrape_propstream_data(df, selected_column, max_properties, debug_mode, headless_mode)
    
    if results_df is not None and not results_df.empty:
        st.success(f"✅ Scraping completed! Total entries processed: {len(results_df)}")
        st.dataframe(results_df)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'propstream_results_{timestamp}.csv'
        
        # Download button
        st.download_button(
            label="Download Results as CSV",
            data=results_df.to_csv(index=False).encode('utf-8'),
            file_name=filename,
            mime='text/csv'
        )
    else:
        st.warning("No data was successfully extracted. Please check your CSV file and try again.")
        if debug_mode:
            st.info("Enable debug mode and check the console/terminal output for detailed error information.")

# Troubleshooting section
with st.expander("🔧 Troubleshooting"):
    st.markdown("""
    **Common Issues and Solutions:**
    
    **❌ "Locator timeout" errors:**
    - Try unchecking "Run browser in background" to see what's happening
    - Enable debug mode for detailed logs
    - PropStream website might have changed - check if you can login manually
    
    **❌ "Login failed":**
    - Verify the credentials in the code are correct
    - Check if PropStream requires 2FA
    - Try logging in manually first
    
    **❌ "No data extracted":**
    - Start with just 1-2 properties to test
    - Make sure addresses are properly formatted
    - Check if PropStream is accessible
    
    **❌ "Search input not found":**
    - Enable debug mode to see which selectors are being tried
    - The page might still be loading - increase timeout
    - PropStream may have updated their interface
    
    **❌ Browser issues:**
    - Uncheck "Run browser in background" to see browser actions
    - Close other browser instances that might conflict
    - Make sure you have enough system memory
    
    **⚡ Performance tips:**
    - Start with max 5 properties for testing
    - Close other applications to free up memory
    - Use headless mode for faster processing
    
    **🆕 New in this version:**
    - Dynamically waits for search input instead of fixed 20-second delay
    - Automatically handles "Proceed" button if it appears
    - Extracts additional financial data: Open Mortgages, Estimated Balance, Involuntary Liens, Involuntary Amount
    - **NEW: Detailed mortgage extraction** - Clicks "Mortgage & Transaction History" tab and extracts individual lender names and rates
    - **NEW: Multiple lender support** - Each lender gets separate columns (lender_1_name, lender_1_rate, etc.)
    - More robust error handling and input detection
    - Better debug information when enabled
    
    **💡 Mortgage Data Notes:**
    - The scraper will find up to 3 lenders per property (can be extended if needed)
    - Each lender gets separate columns for name and interest rate
    - If a property has fewer lenders, remaining columns will show 'N/A'
    """)