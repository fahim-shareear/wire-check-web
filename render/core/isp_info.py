import requests
from render.core.helpers import get_timestamp


def fetch_from_ipinfo(ip=None):
    """Primary source: ipinfo.io"""
    url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json(), url


def fetch_from_ipapi(ip=None):
    """Backup source: ipapi.co"""
    url = f"https://ipapi.co/{ip}/json/" if ip else "https://ipapi.co/json/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json(), url


def get_isp_info(client_ip=None):
    """
    Fetch ISP + IP + location info.
    If client_ip is provided, looks up that IP instead of server's own IP.
    """
    sources = [
        lambda: fetch_from_ipinfo(client_ip),
        lambda: fetch_from_ipapi(client_ip),
    ]

    for source in sources:
        try:
            data, url_used = source()

            isp_data = {
                "ip":        data.get("ip", client_ip or "N/A"),
                "isp":       data.get("org") or data.get("isp", "N/A"),
                "city":      data.get("city", "N/A"),
                "region":    data.get("region", "N/A"),
                "country":   data.get("country", "N/A"),
                "timezone":  data.get("timezone", "N/A"),
                "hostname":  data.get("hostname", "N/A"),
                "asn":       data.get("asn", "N/A"),
                "source":    url_used,
                "timestamp": get_timestamp(),
                "note":      f"Looked up client IP: {client_ip}" if client_ip else "Used server IP",
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
        "error":   "Failed to fetch ISP info from all available services."
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