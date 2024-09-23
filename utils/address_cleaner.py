# utils/address_cleaner.py

import requests
from difflib import get_close_matches
import pycountry

GEONAMES_USERNAME = 'hvrshchaudhary'  # Replace with your GeoNames username

def get_country_code(country_name):
    """
    Convert country name to its two-letter ISO country code and standardized country name using pycountry.
    
    Args:
        country_name (str): The name of the country entered by the user.
        
    Returns:
        tuple: (country_code (str), standardized_country_name (str)) if found; otherwise, (None, None).
    """
    try:
        country = pycountry.countries.lookup(country_name)
        print(f"Exact match found for country '{country_name}': '{country.name}' with code '{country.alpha_2}'")
        return country.alpha_2, country.name
    except LookupError:
        print(f"Warning: Could not find ISO code for country '{country_name}'. Attempting fuzzy matching...")
        # Get list of all country names
        country_names = [country.name for country in pycountry.countries]
        # Find close matches
        matches = get_close_matches(country_name, country_names, n=1, cutoff=0.8)
        if matches:
            matched_country_name = matches[0]
            try:
                country = pycountry.countries.lookup(matched_country_name)
                print(f"Fuzzy matched country '{country_name}' to '{country.name}' with code '{country.alpha_2}'")
                return country.alpha_2, country.name
            except LookupError:
                print(f"Error: Fuzzy matched country name '{matched_country_name}' not found in pycountry.")
                return None, None
        else:
            print(f"No fuzzy matches found for country '{country_name}'.")
            return None, None

def validate_city(city, country_code, admin_code=None):
    """
    Validate the city using GeoNames API and implement fuzzy matching.
    
    Args:
        city (str): The city name entered by the user.
        country_code (str): The two-letter ISO country code.
        admin_code (str, optional): The administrative code of the state. Defaults to None.
        
    Returns:
        tuple: (corrected_city_name (str), is_valid (bool))
    """
    # Construct the GeoNames API URL with optional adminCode1
    if admin_code:
        url = f"http://api.geonames.org/searchJSON?q={city}&maxRows=10&country={country_code}&adminCode1={admin_code}&username={GEONAMES_USERNAME}"
    else:
        url = f"http://api.geonames.org/searchJSON?q={city}&maxRows=10&country={country_code}&username={GEONAMES_USERNAME}"
    
    response = requests.get(url)
    print(f"GeoNames API Response for City: {response}")
    
    if response.status_code == 200:
        results = response.json().get('geonames', [])
        city_names = [result['name'] for result in results]
        print(f"Fetched City Names: {city_names}")
        
        # If no exact match is found, use fuzzy matching
        if not city_names:
            print("No exact city match found. Applying fuzzy matching...")
            return apply_fuzzy_matching(city, country_code, admin_code)
        
        # If the city exists (case-insensitive), return it
        if city.lower() in (name.lower() for name in city_names):
            # Return the correctly cased city name from the API
            corrected_city = next(name for name in city_names if name.lower() == city.lower())
            print(f"Exact city match found: {corrected_city}")
            return corrected_city, True
        
        # Suggest closest match if the city is misspelled
        closest_matches = get_close_matches(city, city_names, n=1, cutoff=0.7)
        if closest_matches:
            print(f"Suggested City Match: {closest_matches[0]}")
            return closest_matches[0], False
        
    else:
        print(f"Error: GeoNames API request failed with status code {response.status_code}")
    
    return city, False

def apply_fuzzy_matching(city, country_code, admin_code=None):
    """
    Apply fuzzy matching to find the best matching city within a state.
    
    Args:
        city (str): The misspelled city name entered by the user.
        country_code (str): The two-letter ISO country code.
        admin_code (str, optional): The administrative code of the state. Defaults to None.
        
    Returns:
        tuple: (best_matching_city (str), is_valid (bool))
    """
    # Fetch a larger set of potential matches starting with the first 3 letters
    if admin_code:
        url = f"http://api.geonames.org/searchJSON?name_startsWith={city[:3]}&maxRows=200&country={country_code}&adminCode1={admin_code}&username={GEONAMES_USERNAME}"
    else:
        url = f"http://api.geonames.org/searchJSON?name_startsWith={city[:3]}&maxRows=200&country={country_code}&username={GEONAMES_USERNAME}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        results = response.json().get('geonames', [])
        city_names = [result['name'] for result in results]
        print(f"Fetched City Names for Fuzzy Matching: {city_names}")
        
        # Use difflib's get_close_matches to find similar city names
        closest_matches = get_close_matches(city, city_names, n=1, cutoff=0.7)
        if closest_matches:
            print(f"Fuzzy Matched City: {closest_matches[0]}")
            return closest_matches[0], False
    
    print("Fuzzy matching did not find a suitable city.")
    return city, False

def validate_state(state, country_code):
    """
    Validate the state using GeoNames API (with fuzzy matching for misspellings).
    
    Args:
        state (str): The state name entered by the user.
        country_code (str): The two-letter ISO country code.
        
    Returns:
        tuple: (corrected_state_name (str), is_valid (bool), admin_code (str or None))
    """
    # Construct the GeoNames API URL to search for administrative regions
    url = f"http://api.geonames.org/searchJSON?q={state}&maxRows=10&country={country_code}&featureClass=A&username={GEONAMES_USERNAME}"
    response = requests.get(url)
    
    if response.status_code == 200:
        results = response.json().get('geonames', [])
        # Extract state names and their admin codes
        state_info = [(result['adminName1'], result.get('adminCode1')) for result in results if 'adminName1' in result]
        state_names = [info[0] for info in state_info]
        print(f"Fetched State Names: {state_names}")
        
        # If no exact match is found, use fuzzy matching
        if not state_names:
            print("No exact state match found. Applying fuzzy matching...")
            return apply_fuzzy_matching_state(state, country_code)
        
        # If the state exists (case-insensitive), return it along with its admin code
        for name, admin_code in state_info:
            if state.lower() == name.lower():
                print(f"Exact state match found: {name} with adminCode1: {admin_code}")
                return name, True, admin_code
        
        # Suggest closest match if the state is misspelled
        closest_matches = get_close_matches(state, state_names, n=1, cutoff=0.7)
        if closest_matches:
            # Retrieve the admin code for the suggested state
            for name, admin_code in state_info:
                if name == closest_matches[0]:
                    print(f"Suggested State Match: {name} with adminCode1: {admin_code}")
                    return name, False, admin_code
        
    else:
        print(f"Error: GeoNames API request failed with status code {response.status_code}")
    
    return state, False, None

def apply_fuzzy_matching_state(state, country_code):
    """
    Apply fuzzy matching to find the best matching state within a country.
    
    Args:
        state (str): The misspelled state name entered by the user.
        country_code (str): The two-letter ISO country code.
        
    Returns:
        tuple: (best_matching_state (str), is_valid (bool), admin_code (str or None))
    """
    # Fetch a larger set of potential state matches starting with the first 3 letters
    url = f"http://api.geonames.org/searchJSON?name_startsWith={state[:3]}&maxRows=100&country={country_code}&featureClass=A&username={GEONAMES_USERNAME}"
    response = requests.get(url)
    
    if response.status_code == 200:
        results = response.json().get('geonames', [])
        state_info = [(result['adminName1'], result.get('adminCode1')) for result in results if 'adminName1' in result]
        state_names = [info[0] for info in state_info]
        print(f"Fetched State Names for Fuzzy Matching: {state_names}")
        
        # Use difflib's get_close_matches to find similar state names
        closest_matches = get_close_matches(state, state_names, n=1, cutoff=0.7)
        if closest_matches:
            # Retrieve the admin code for the suggested state
            for name, admin_code in state_info:
                if name == closest_matches[0]:
                    print(f"Fuzzy Matched State: {name} with adminCode1: {admin_code}")
                    return name, False, admin_code
        
    print("Fuzzy matching did not find a suitable state.")
    return state, False, None

def clean_address_fields(city, state, country):
    """
    Validate and correct the address fields.
    
    Args:
        city (str): City name.
        state (str): State name.
        country (str): Country name.
        
    Returns:
        dict: Corrected address fields.
    """
    # Convert country name to ISO code and get standardized country name
    country_code, standardized_country = get_country_code(country)
    
    if not country_code:
        print(f"Proceeding without country code for '{country}'.")
    
    # Validate and correct the state
    corrected_state, state_valid, admin_code = validate_state(state.title(), country_code) if country_code else (state.title(), False, None)
    
    # Validate and correct the city, passing admin_code to limit the search within the state
    corrected_city, city_valid = validate_city(city.title(), country_code, admin_code) if country_code else (city.title(), False)
    
    # Use the standardized country name if available; else, capitalize original input
    cleaned_country = standardized_country if standardized_country else country.title()
    
    return {
        'corrected_city': corrected_city,
        'corrected_state': corrected_state,
        'corrected_country': cleaned_country,
        'country_code': country_code if country_code else 'N/A'
    }
