"""Get ISP and network location information"""
import requests


def get_isp_info(client_ip=None):
    """
    Fetch ISP info for a specific IP address.
    
    If client_ip is provided, get info for that IP.
    Otherwise, ipinfo.io will auto-detect the requesting IP.
    """
    
    url = "https://ipinfo.io/json"
    
    # If client IP provided, query that specific IP
    if client_ip:
        url = f"https://ipinfo.io/{client_ip}/json"
        print(f"[ISP] Fetching info for client IP: {client_ip}")
    else:
        print(f"[ISP] Auto-detecting IP from request")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"[ISP] Got IP: {data.get('ip', 'unknown')}")
        print(f"[ISP] ISP: {data.get('org', 'unknown')}")
        print(f"[ISP] Location: {data.get('city', 'unknown')}, {data.get('country', 'unknown')}")
        
        isp_data = {
            "ip": data.get("ip", "N/A"),
            "isp": data.get("org", "N/A"),
            "city": data.get("city", "N/A"),
            "region": data.get("region", "N/A"),
            "country": data.get("country", "N/A"),
            "timezone": data.get("timezone", "N/A"),
            "hostname": data.get("hostname", "N/A"),
        }
        
        return {"success": True, "data": isp_data}
    
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch ISP info: {str(e)}"
        }