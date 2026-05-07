import requests
from render.core.helpers import get_timestamp


def fetch_from_ipinfo():
    """Primary source: ipinfo.io"""
    url = "https://ipinfo.io/json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json(), url


def fetch_from_ipapi():
    """Backup source: ipapi.co"""
    url = "https://ipapi.co/json/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json(), url


def get_isp_info():
    """
    Fetch ISP + IP + location info using multiple APIs for better accuracy
    """

    sources = [fetch_from_ipinfo, fetch_from_ipapi]

    for source in sources:
        try:
            data, url_used = source()

            isp_data = {
                "ip": data.get("ip", "N/A"),
                "isp": data.get("org") or data.get("isp", "N/A"),
                "city": data.get("city", "N/A"),
                "region": data.get("region", "N/A"),
                "country": data.get("country", "N/A"),
                "timezone": data.get("timezone", "N/A"),
                "hostname": data.get("hostname", "N/A"),
                "asn": data.get("asn", "N/A"),
                "source": url_used,
                "timestamp": get_timestamp(),
            }

            return {"success": True, "data": isp_data}

        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            continue
        except requests.exceptions.RequestException:
            continue

    return {
        "success": False,
        "error": "Failed to fetch ISP info from all available services."
    }


def display_isp_info(isp_result):
    """Simple console output"""

    if isp_result["success"]:
        data = isp_result["data"]

        print("\n--- ISP / Network Information ---")
        print(f"IP Address : {data['ip']}")
        print(f"ISP / Org  : {data['isp']}")
        print(f"ASN        : {data['asn']}")
        print(f"City       : {data['city']}")
        print(f"Region     : {data['region']}")
        print(f"Country    : {data['country']}")
        print(f"Timezone   : {data['timezone']}")
        print(f"Hostname   : {data['hostname']}")
        print(f"Source     : {data['source']}")
        print(f"Timestamp  : {data['timestamp']}")

    else:
        print(f"\n[Error] {isp_result['error']}")


if __name__ == "__main__":
    result = get_isp_info()
    display_isp_info(result)