import os
import requests
from neo4j import GraphDatabase

# Neo4j connection details
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Function to fetch city coordinates from GeoNames API
def fetch_city_coordinates():
    # GeoNames API endpoint
    url = "http://api.geonames.org/citiesJSON"
    params = {
        'north': 90,
        'south': -90,
        'east': 180,
        'west': -180,
        'lang': 'en',
        'username': 'your_geonames_username',  # Replace with your GeoNames username
        'maxRows': 1000
    }
    response = requests.get(url, params=params)
    return response.json().get('geonames', [])

# Function to update the Neo4j knowledge graph
def update_knowledge_graph(cities):
    with driver.session() as session:
        for city in cities:
            city_name = city.get('name')
            latitude = city.get('lat')
            longitude = city.get('lng')
            country_name = city.get('countryName')

            # Create or update city and coordinate nodes and relationships
            session.run("""
                MERGE (c:City {name: $city_name})
                MERGE (co:Coordinates {latitude: $latitude, longitude: $longitude})
                MERGE (c)-[:HAS_COORDINATES]->(co)
                MERGE (country:Country {name: $country_name})
                MERGE (c)-[:IN_COUNTRY]->(country)
            """, city_name=city_name, latitude=latitude, longitude=longitude, country_name=country_name)

# Main function to execute the process
def main():
    cities = fetch_city_coordinates()
    update_knowledge_graph(cities)

if __name__ == "__main__":
    main()