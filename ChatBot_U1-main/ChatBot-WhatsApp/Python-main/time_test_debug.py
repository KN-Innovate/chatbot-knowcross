import time
from datetime import datetime
import requests

# Fetch time from an NTP server
ntp_url = "http://worldtimeapi.org/api/timezone/Etc/UTC"
response = requests.get(ntp_url)
if response.status_code == 200:
    utc_time = response.json()["utc_datetime"]
    print(f"NTP Time: {utc_time}")
    print(f"Current Time (Local): {datetime.now()}")
    print(f"Current Timestamp: {int(time.time())}")
else:
    print("Failed to fetch NTP time")