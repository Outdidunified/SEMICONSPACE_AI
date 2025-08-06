import requests
import logging
import time

logger = logging.getLogger(__name__)

class DigiKeyComponentRecommender:
    """
    Dynamic electronic component recommendation using Digi-Key API.
    """
    CACHE_TTL = 3600

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://api.digikey.com/v1/oauth2/token"
        self.search_url = "https://api.digikey.com/services/partsearch/v2/parts"
        self.access_token = None
        self.token_expiry = 0
        self.component_cache = {}
        self.alternatives_cache = {}

    def authenticate(self):
        """Authenticate with Digi-Key API to get access token."""
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://api.digikey.com/.default"
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            response = requests.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = time.time() + expires_in - 60
            logger.info("Authenticated with Digi-Key API successfully.")
        except Exception as e:
            logger.error(f"Failed to authenticate with Digi-Key API: {e}")
            self.access_token = None

    def get_access_token(self):
        """Get valid access token, refresh if expired or not present."""
        if not self.access_token or time.time() >= self.token_expiry:
            self.authenticate()
        return self.access_token

    def is_cache_valid(self, cache_entry):
        """Check if cache entry is still valid based on TTL."""
        if not cache_entry:
            return False
        timestamp, _ = cache_entry
        return (time.time() - timestamp) < self.CACHE_TTL

    def search_component(self, part_number):
        """Search for component details by part number using Digi-Key API with caching."""
        cache_entry = self.component_cache.get(part_number)
        if self.is_cache_valid(cache_entry):
            return cache_entry[1]

        token = self.get_access_token()
        if not token:
            logger.error("No access token available for Digi-Key API.")
            return None

        headers = {
            "X-DIGIKEY-Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        params = {
            "keywords": part_number,
            "recordCount": 1,
            "startingRecord": 0,
            "searchOptions": "ExactMatch"
        }
        try:
            response = requests.get(self.search_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("Parts") and len(data["Parts"]) > 0:
                component = data["Parts"][0]
                self.component_cache[part_number] = (time.time(), component)
                return component
            else:
                logger.warning(f"No results found for part number: {part_number}")
                return None
        except Exception as e:
            logger.error(f"Error searching component {part_number}: {e}")
            return None

    def get_alternatives(self, part_number):
        """Get alternative components with caching."""
        cache_entry = self.alternatives_cache.get(part_number)
        if self.is_cache_valid(cache_entry):
            return cache_entry[1]

        token = self.get_access_token()
        if not token:
            logger.error("No access token available for Digi-Key API.")
            return []

        headers = {
            "X-DIGIKEY-Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        params = {
            "keywords": part_number,
            "recordCount": 5,
            "startingRecord": 0,
            "searchOptions": "Similar"
        }
        try:
            response = requests.get(self.search_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            alternatives = data.get("Parts", [])
            modern_alternatives = [
                {
                    "part_number": alt.get("PartNumber"),
                    "manufacturer": alt.get("Manufacturer", {}).get("Name"),
                    "description": alt.get("Description"),
                    "datasheet_url": alt.get("Datasheets", [{}])[0].get("Url"),
                    "features": alt.get("Attributes", {})
                }
                for alt in alternatives
            ]
            self.alternatives_cache[part_number] = (time.time(), modern_alternatives)
            return modern_alternatives
        except Exception as e:
            logger.error(f"Error fetching alternatives for {part_number}: {e}")
            return []

    def format_features(self, features):
        """Format features dictionary into a readable string."""
        if not features:
            return "No key features available."
        feature_lines = []
        for key, value in features.items():
            feature_lines.append(f"- {key}: {value}")
        return "\n".join(feature_lines)

    def generate_human_like_response(self, part_number, component, eol_status, recommendations):
        """Generate a friendly, casual, and human-like response string."""
        response_lines = []
        response_lines.append(f"Hey! Here's what I found about the component '{part_number}':\n")
        response_lines.append(f"Manufacturer: {component.get('Manufacturer', {}).get('Name', 'Unknown')}")
        response_lines.append(f"Description: {component.get('Description', 'No description available.')}")
        response_lines.append(f"EoL Status: {eol_status}")
        response_lines.append("Key Features:")
        response_lines.append(self.format_features(component.get('Attributes', {})))
        response_lines.append("\nHere are some modern alternatives you might consider:\n")

        for alt in recommendations:
            response_lines.append(f"- {alt.get('part_number')} by {alt.get('manufacturer')}")
            response_lines.append(f"  Description: {alt.get('description')}")
            response_lines.append(f"  Datasheet: {alt.get('datasheet_url')}")
            response_lines.append("  Features:")
            response_lines.append(self.format_features(alt.get('features')))
            response_lines.append("")

        response_lines.append("What is your intended application (e.g., ADC, USB, timers) to help me narrow down the suggestions?")
        response_lines.append(f"Also, you might want to try a basic electronics project using the {part_number} microcontroller for sensor interfacing and data acquisition. Let me know if you want details!")
        return "\n".join(response_lines)

    def recommend(self, part_number):
        """Recommend alternatives with detailed info and EoL status."""
        component = self.search_component(part_number)
        if not component:
            return {"error": "Component not found"}

        eol_status = "Unknown"
        attributes = component.get("Attributes", {})
        for attr_key, attr_value in attributes.items():
            if "EOL" in attr_key or "End of Life" in attr_key:
                eol_status = attr_value
                break

        alternatives = self.get_alternatives(part_number)
        recommendations = []
        for alt in alternatives:
            recommendations.append({
                "part_number": alt.get("part_number"),
                "manufacturer": alt.get("manufacturer"),
                "description": alt.get("description"),
                "datasheet_url": alt.get("datasheet_url"),
                "features": alt.get("features")
            })

        human_response = self.generate_human_like_response(part_number, component, eol_status, recommendations)
        response = {
            "original_component": {
                "part_number": part_number,
                "manufacturer": component.get("Manufacturer", {}).get("Name"),
                "description": component.get("Description"),
                "datasheet_url": component.get("Datasheets", [{}])[0].get("Url"),
                "key_features": self.format_features(attributes),
                "eol_status": eol_status
            },
            "modern_alternatives": recommendations,
            "human_like_response": human_response
        }
        return response