import requests

from render.core.helpers import get_timestamp


def get_isp_info():
    """Fetching public IP, ISP, location info from ipinfo.io
       Returning a directory with all network identity info
    """

    url = "https://ipinfo.io/json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        isp_data = {
            "ip": data.get("ip", "N/A"),
            "isp": data.get("org", "N/A"),
            "city": data.get("city", "N/A"),
            "region": data.get("region", "N/A"),
            "country": data.get("country", "N/A"),
            "timezone": data.get("timezone", "N/A"),
            "hostname": data.get("hostname", "N/A"),
            "timestamp": get_timestamp(),
        }

        return {"success": True, "data": isp_data}

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "No internet connection. Please check your network and try again."
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Requests timed out while fetching ISP info."
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch ISP info: {str(e)}"
        }

def display_isp_info(isp_result):
    """"Simple print display for quick testing"""
    if isp_result["success"]:
        data = isp_result["data"]
        print("\n--- ISP Information ---")
        print(f"IP Address: {data['ip']}")
        print(f"ISP / Org : {data['isp']}")
        print(f"City      : {data['city']}")
        print(f"Region    : {data['region']}")
        print(f"Timezone  : {data['timezone']}")
        print(f"Hostname  : {data['hostname']}")
        print(f"Timestamp : {data['timestamp']}")
    else:
        print(f"\n[Error] {isp_result["error"]}")


if __name__ == "__main__":
    result = get_isp_info()
    display_isp_info(result)