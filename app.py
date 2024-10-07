# app.py

from flask import Flask, render_template, request
from utils.address_cleaner import clean_address_fields
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    cleaned_data = None
    if request.method == 'POST':
        # Get the address fields entered by the user
        city = request.form.get('city')
        state = request.form.get('state')
        country = request.form.get('country')
        
        # Clean the address fields using the address_cleaner logic
        cleaned_address = clean_address_fields(city, state, country)
        
        # Prepare the cleaned data for display
        cleaned_data = {
            'original_city': city,
            'corrected_city': cleaned_address['corrected_city'],
            'original_state': state,
            'corrected_state': cleaned_address['corrected_state'],
            'original_country': country,
            'corrected_country': cleaned_address['corrected_country'],
            'country_code': cleaned_address['country_code'],
        }
    
    return render_template('index.html', cleaned_data=cleaned_data)

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
