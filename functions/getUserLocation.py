import requests

def get_location_from_ip(client_ip: str) -> str:
    if client_ip.lower() in ["unknown", "127.0.0.1", "::1"]:
        return "Localhost / Unknown IP"
    
    try:
        response = requests.get(f"https://ipinfo.io/{client_ip}/json")
        if response.status_code == 200:
            data = response.json()
            city = data.get("city", "")
            region = data.get("region", "")
            country = data.get("country", "")
            location_parts = [part for part in [city, region, country] if part]
            return ", ".join(location_parts) if location_parts else "Location not found"
        else:
            return "Unable to fetch location"
    except Exception as e:
        return f"Location detection failed: {str(e)}"