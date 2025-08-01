import requests
import logging
import time

logger = logging.getLogger(__name__)

class DigiKeyComponentRecommender:
    """
    Dynamic electronic component recommendation using Digi-Key API.
    """

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://api.digikey.com/v1/oauth2/token"
        self.search_url = "https://api.digikey.com/services/partsearch/v2/parts"
        self.access_token = None
        self.token_expiry = 0

    def authenticate(self):
        """
        Authenticate with Digi-Key API to get access token.
        """
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
            self.token_expiry = time.time() + expires_in - 60  # Refresh 1 min before expiry
            logger.info("Authenticated with Digi-Key API successfully.")
        except Exception as e:
            logger.error(f"Failed to authenticate with Digi-Key API: {e}")
            self.access_token = None

    def get_access_token(self):
        """
        Get valid access token, refresh if expired or not present.
        """
        if not self.access_token or time.time() >= self.token_expiry:
            self.authenticate()
        return self.access_token

    def search_component(self, part_number):
        """
        Search for component details by part number using Digi-Key API.
        """
        token = self.get_access_token()
        if not token:
            logger.error("No access token available for Digi-Key API.")
            return None

        headers = {
            "X-DIGIKEY-Client-Id": self.client_id,
            "Authorization": f"Bearer {token}",
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
                return data["Parts"][0]
            else:
                logger.warning(f"No results found for part number: {part_number}")
                return None
        except Exception as e:
            logger.error(f"Error searching component {part_number}: {e}")
            return None

    def get_alternatives(self, part_number):
        """
        Digi-Key API does not provide direct alternatives endpoint.
        This method performs a broader search to find similar parts.
        """
        token = self.get_access_token()
        if not token:
            logger.error("No access token available for Digi-Key API.")
            return []

        headers = {
            "X-DIGIKEY-Client-Id": self.client_id,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        params = {
            "keywords": part_number,
            "recordCount": 10,
            "startingRecord": 0,
            "searchOptions": "FuzzyMatch"
        }
        try:
            response = requests.get(self.search_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            alternatives = data.get("Parts", [])
            # Filter out the original part if present
            alternatives = [alt for alt in alternatives if alt.get("PartNumber") != part_number]
            # Limit to 3 modern alternatives with core specs
            modern_alternatives = []
            for alt in alternatives:
                if len(modern_alternatives) >= 3:
                    break
                modern_alternatives.append({
                    "part_number": alt.get("PartNumber"),
                    "manufacturer": alt.get("Manufacturer", {}).get("Name"),
                    "description": alt.get("Description"),
                    "datasheet_url": alt.get("Datasheets", [{}])[0].get("Url"),
                    "features": alt.get("Attributes", {})
                })
            return modern_alternatives
        except Exception as e:
            logger.error(f"Error fetching alternatives for {part_number}: {e}")
            return []

    def format_features(self, features):
        """
        Format features dictionary into a readable string.
        """
        if not features:
            return "No key features available."
        feature_lines = []
        for key, value in features.items():
            feature_lines.append(f"- {key}: {value}")
        return "\n".join(feature_lines)

    def recommend(self, part_number):
        """
        Recommend alternatives with detailed info and EoL status.
        """
        component = self.search_component(part_number)
        if not component:
            return {"error": "Component not found"}

        # Extract EoL status if available in attributes or description
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

        # Compose response with friendly, casual, and technically accurate tone
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
            "next_step_prompt": "What is your intended application (e.g., ADC, USB, timers) to narrow down the suggestions?",
            "project_proposal": f"Consider a basic electronics project using the {part_number} microcontroller for sensor interfacing and data acquisition."
        }
        return response

# Example usage:
# client_id = "ZT9LNhAQzYvQ9x06NlqtYGZoeRDdTsYEgK0JJDh0QlUs8Re4"
# client_secret = "hQrLAiEuT73MvLmSjReuIGLvNdygRwb8E91P7UXYdK5CaUeyzYrFcKf6Gvvrjs25"
# recommender = DigiKeyComponentRecommender(client_id, client_secret)
# result = recommender.recommend("C8051F120")
# print(result)
