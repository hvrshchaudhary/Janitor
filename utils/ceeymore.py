# utils/ceeymore.py

import os
import json
import re
from openai import OpenAI
from neo4j import GraphDatabase
import tempfile

# Initialize the OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

class CeeyMore:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_user = os.getenv("NEO4J_USER")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))

    def handle_anomaly(self, anomaly_data):
        # Step 1: Use LLM to analyze the data and determine how to clean it
        cleaned_data = self.analyze_and_clean_data(anomaly_data)
        if not cleaned_data:
            print("LLM could not clean the data")
            return None

        # Step 2: Generate code updates and knowledge graph updates
        self.generate_updates(anomaly_data, cleaned_data)

        return cleaned_data

    def analyze_and_clean_data(self, anomaly_data):
        # Use LLM to figure out what the user intended
        prompt = f"""
                        You are an AI assistant helping to clean address data.

                        The user provided the following inputs:
                        - City: '{anomaly_data['city_input']}'
                        - State: '{anomaly_data['state_input']}'
                        - Country: '{anomaly_data['country_input']}'

                        The system couldn't process this data. Analyze the inputs and determine what the user might have meant.
                        For context, this data provided to you is address data with fields city, state, country. The user may enter some relevant data in the provided fields that may or may not
                        be sufficient to infer the actual data. Your task is to guess what data the user may be trying to point to based on the data that the user has provided. If there
                        are few valid fields, try inferring the invalid field based on the valid ones as they are all related. You may also be given some relevant information in the invalid field
                        that may help you infer the data.

                        Provide only the cleaned data in JSON format with the fields:
                        {{
                            "city": "cleaned city name",
                            "state": "cleaned state name",
                            "country": "cleaned country name"
                        }}

                        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                stop=None  # Ensure full response is captured
            )

            # Get the response content
            raw_content = response.choices[0].message.content.strip()
            print(f"Raw response from OpenAI:\n{raw_content}\n")

            # Try to extract JSON from the response
            json_data = self.extract_json(raw_content)

            if json_data:
                try:
                    cleaned_data = json.loads(json_data)
                    return cleaned_data
                except json.JSONDecodeError as jde:
                    print(f"JSON Decode Error in analyze_and_clean_data: {jde}")
                    print(f"Extracted JSON: {json_data}")
                    return None
            else:
                print("Could not extract JSON from the response.")
                return None

        except Exception as e:
            print(f"Error in analyze_and_clean_data: {e}")
            return None

    def extract_json(self, text):
        """
        Extracts JSON object from a string.
        """
        try:
            # Locate the first '{' and the last '}' to extract the JSON substring
            start = text.index('{')
            end = text.rindex('}') + 1
            json_str = text[start:end]
            return json_str
        except ValueError as ve:
            print(f"Error extracting JSON: {ve}")
            return None

    def generate_updates(self, anomaly_data, cleaned_data):
        # Generate knowledge graph updates as Python code
        kg_code = self.generate_kg_updates(anomaly_data, cleaned_data)
        
         # Generate code updates
        code_changes = self.generate_code_updates(anomaly_data, cleaned_data, kg_code)

        # Write code changes to a temporary file
        self.write_temp_file('code_update.py', code_changes)

        # Write knowledge graph update code to a temporary file
        self.write_temp_file('kg_update.py', kg_code)
        

    def generate_code_updates(self, anomaly_data, cleaned_data, kg_code):
        
        # Read the current address_cleaner.py code
        address_cleaner_path = os.path.join(os.path.dirname(__file__), 'address_cleaner.py')
        try:
            with open(address_cleaner_path, 'r', encoding='utf-8') as f:
                address_cleaner_code = f.read()
        except Exception as e:
            print(f"Error reading address_cleaner.py: {e}")
            address_cleaner_code = ""
            
        system_prompt = (
            "You are an AI assistant specialized in enhancing a data cleaner's script called 'address_cleaner.py' a.k.a Janitor's python code that uses a neo4j graph for reference to help it clean data"
            "When the janitor encounters a data anomaly that it cannot handle, it asks another agent to upgrade it's knowledge graph and to make it famaliar with that anomaly and then It asks you to update it's code to leverage the changes made freshly in the knowledge graph to handdle similar anomalies in the future."
            "You will be given the anomalous instance of data, the corrected instance of data along with the code that updated the knowledge graph and the code of the janitor. Your task is to update the janitor's code in a way that it can handle similar types of anomalies (not just that specific instance) in the future."
            "Example: Let's say that the user enter the coordinates of the city in the city field, the graph updater would add coordinates of all cities and send that code to you. You will then create a new method and update the logic of the janitor such that it is able to leverage the freshly updated data to infer other city names if coordinates are provided without relying on the generative logic."
        )
            
        # Use LLM to suggest code changes
        prompt = f"""
                    The following address data caused an anomaly in the system:
                    - City: '{anomaly_data['city_input']}'
                    - State: '{anomaly_data['state_input']}'
                    - Country: '{anomaly_data['country_input']}'

                    The cleaned data is:
                    - City: '{cleaned_data['city']}'
                    - State: '{cleaned_data['state']}'
                    - Country: '{cleaned_data['country']}'

                    Here is the current code for address_cleaner.py:

                    ```python
                    {address_cleaner_code}
                    ```
                    
                    Additionally, the knowledge graph was updated with the following code:
                    ```python
                    {kg_code}
                    ```
                    
                    Provide the entire updated 'address_cleaner.py' file, make required changes to the existing methods and add new methods if necessary but output the entire ready to use file.
                    """

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                stop=None  # Ensure full response is captured
            )

            raw_content = response.choices[0].message.content.strip()
            print(f"Raw code_changes response from OpenAI:\n{raw_content}\n")

            # Attempt to extract code block if present
            code_changes = self.extract_code(raw_content)

            return code_changes

        except Exception as e:
            print(f"Error in generate_code_updates: {e}")
            return ""

    def extract_code(self, text):
        """
        Extracts Python code from a string, removing markdown syntax if present.
        """
        # Check if the response contains a code block
        code_block_pattern = re.compile(r'```python\s*(.*?)\s*```', re.DOTALL)
        match = code_block_pattern.search(text)
        if match:
            return match.group(1).strip()
        else:
            # If no code block, assume the entire text is code
            return text.strip()

    def generate_kg_updates(self, anomaly_data, cleaned_data):
        """
        Generates Python code to fetch new required data and add it to the Neo4j knowledge graph.

        Args:
            anomaly_data (dict): The original anomalous address data.
            cleaned_data (dict): The cleaned address data inferred by the AI.

        Returns:
            str: The Python code that fetches new data and updates the knowledge graph.
        """
        # Define the system prompt
        system_prompt = (
            "You are an AI assistant specialized in enhancing a Neo4j knowledge graph to improve data validation and anomaly resolution."
            "The graph that you enhance is used by our address cleaning system called janitor which uses the graph to handle anomalous data entered by user"
            "When the janitor cannot handle an anomaly, it asks you to update it's graph and gives you any relevant information"
            "Your goal is to help the Janitor system resolve address anomalies by ensuring the knowledge graph contains all necessary data and relationships to deal with similar anomaly in the future. "
            "Add the data and relationships in the knowledge graph such that similar category of anomalous data can be cleaned just using the knowledge graph without relying on you."
        )

        # Construct the user prompt with enhanced context
        user_prompt = f"""
        The Janitor system has detected an address anomaly. Below is the anomalous data provided by the user and the cleaned data inferred by the system:
        - City: '{anomaly_data['city_input']}'
        - State: '{anomaly_data['state_input']}'
        - Country: '{anomaly_data['country_input']}'

        The cleaned data inferred is:
        - City: '{cleaned_data['city']}'
        - State: '{cleaned_data['state']}'
        - Country: '{cleaned_data['country']}'

        Task:
        1. Analyze the differences between the anomalous data and the cleaned data.
        2. Determine what additional data or relationships should be added to the knowledge graph to map the anomalous input to the correct data.
        3. Generate Python code that:
        - Fetches the necessary data for that anomaly category (that helps deal with similar anomalies in the future) from a real external source (e.g., APIs, dont use placeholders for APIs, you have to decide which API to use) to add to the knowledge graph.
        - Updates the knowledge graph by adding nodes and relationships that enable mapping from anomalous data to the correct data.
        - Ensures that the knowledge graph can be queried using different instances of similar type of anomalous data to retrieve the corrected fields.
        4. Generalize the solution to handle various types of anomalies from the received anomaly class, not just this specific case. For example, if the user enters coordinates of a city in place of city
           then fetch the coordinates of all cities and add them to the graph with a 'belongs to' relationship with their corresponding cities so that the janitor can 
           use the graph to resolve similar anomalies with various different coordinates in future and not just the coordinate received in the 
           current anomaly. You task would be in this case to add data for all the coordinates and not just the given coordinate (but remember this just an example).

        Important Notes:
        - The knowledge graph uses nodes like `City`, `State`, `Country`, etc., and relationships such as `IN_STATE`, `IN_COUNTRY`.
        - The code should add enough data and relationships to the graph to handle similar anomalies in future.
        - Think step by step.
        - Use the following connection details to interact with the Neo4j database:

         Neo4j Connection Details:
        ```python
        import os
        from neo4j import GraphDatabase

        NEO4J_URI = os.getenv("NEO4J_URI")
        NEO4J_USER = os.getenv("NEO4J_USER")
        NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        ```
        
        Use the above connection details to interact with the Neo4j database.
        """

        try:
            # Call the OpenAI API with the system prompt
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
            )

            # Extract and log the raw response from OpenAI for debugging
            raw_content = response.choices[0].message.content.strip()
            print(f"Raw kg_updates code from OpenAI:\n{raw_content}\n")

            # Extract the Python code from the response
            kg_code = self.extract_code(raw_content)

            return kg_code

        except Exception as e:
            print(f"Error in generate_kg_updates: {e}")
            return ""

    

    def write_temp_file(self, filename, content):
        if not content:
            print(f"No content to write for {filename}.")
            return

        temp_dir = os.path.join(os.getcwd(), 'temp_updates')
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Generated {filename} and saved to {file_path}")

    def close(self):
        self.driver.close()
