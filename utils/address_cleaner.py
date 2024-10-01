# utils/address_cleaner.py

import os
import requests
import difflib 
import pycountry
from neo4j import GraphDatabase

GEONAMES_USERNAME = 'hvrshchaudhary'  # Replace with your GeoNames username

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def get_country_code(country_name):
    """
    Convert country name to its ISO code and standardized name using Neo4j.
    """
    with driver.session() as session:
        # Try exact match
        result = session.run("""
            MATCH (c:Country)
            WHERE toLower(c.country_name) = toLower($country_name)
            RETURN c.country_name AS country_name, c.iso_code AS iso_code
            LIMIT 1
        """, country_name=country_name)
        record = result.single()
        if record:
            return record['iso_code'], record['country_name']

        # Fuzzy match using full-text search
        result = session.run("""
            CALL db.index.fulltext.queryNodes('countryNameIndex', $country_name + '~')
            YIELD node, score
            RETURN node.country_name AS country_name, node.iso_code AS iso_code
            ORDER BY score DESC
            LIMIT 1
        """, country_name=country_name)
        record = result.single()
        if record:
            return record['iso_code'], record['country_name']

        return None, None

###########################################################################################################################

def validate_city(city_name, country_code, admin_code=None):
    """
    Validate the city using Neo4j with fuzzy matching.
    """
    with driver.session() as session:
        # Try exact match
        if admin_code:
            result = session.run("""
                MATCH (city:City)-[:IN_STATE]->(state:State { admin1_code: $admin_code })
                WHERE toLower(city.city_name) = toLower($city_name)
                RETURN city.city_name AS city_name
                LIMIT 1
            """, city_name=city_name, admin_code=admin_code)
        else:
            result = session.run("""
                MATCH (city:City)-[:IN_STATE]->(state:State)-[:IN_COUNTRY]->(c:Country { iso_code: $country_code })
                WHERE toLower(city.city_name) = toLower($city_name)
                RETURN city.city_name AS city_name
                LIMIT 1
            """, city_name=city_name, country_code=country_code)
        record = result.single()
        if record:
            return record['city_name'], True

        # Fuzzy match using full-text search
        if admin_code:
            result = session.run("""
                CALL db.index.fulltext.queryNodes('cityNameIndex', $city_name + '~')
                YIELD node, score
                MATCH (node)-[:IN_STATE]->(state:State { admin1_code: $admin_code })
                RETURN node.city_name AS city_name, score
                ORDER BY score DESC
                LIMIT 1
            """, city_name=city_name, admin_code=admin_code)
        else:
            result = session.run("""
                CALL db.index.fulltext.queryNodes('cityNameIndex', $city_name + '~')
                YIELD node, score
                MATCH (node)-[:IN_STATE]->(state:State)-[:IN_COUNTRY]->(c:Country { iso_code: $country_code })
                RETURN node.city_name AS city_name, score
                ORDER BY score DESC
                LIMIT 1
            """, city_name=city_name, country_code=country_code)
        record = result.single()
        if record:
            return record['city_name'], False

        return city_name, False
    
#######################################################################################################################################
    
def validate_state(state_name, country_code):
    """
    Validate the state using Neo4j with fuzzy matching.
    """
    with driver.session() as session:
        # Try exact match
        result = session.run("""
            MATCH (s:State)-[:IN_COUNTRY]->(c:Country { iso_code: $country_code })
            WHERE toLower(s.admin1_name) = toLower($state_name)
            RETURN s.admin1_name AS state_name, s.admin1_code AS admin_code
            LIMIT 1
        """, country_code=country_code, state_name=state_name)
        record = result.single()
        if record:
            return record['state_name'], True, record['admin_code']

        # Fuzzy match using full-text search
        result = session.run("""
            CALL db.index.fulltext.queryNodes('stateNameIndex', $state_name + '~')
            YIELD node, score
            MATCH (node)-[:IN_COUNTRY]->(c:Country { iso_code: $country_code })
            RETURN node.admin1_name AS state_name, node.admin1_code AS admin_code, score
            ORDER BY score DESC
            LIMIT 1
        """, state_name=state_name, country_code=country_code)
        record = result.single()
        if record:
            return record['state_name'], False, record['admin_code']

        return state_name, False, None

###########################################################################################################################

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
    
    driver.close()
    return {
        'corrected_city': corrected_city,
        'corrected_state': corrected_state,
        'corrected_country': cleaned_country,
        'country_code': country_code if country_code else 'N/A'
    }
