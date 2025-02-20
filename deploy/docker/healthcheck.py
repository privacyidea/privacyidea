#!/privacyidea/venv/bin/python
import requests
import os
import sys
import time

# Set default values if the environment variables are not available
HOST = os.getenv('PI_HOST', 'localhost')  # Alternative to HOSTNAME, if set manually
PORT = os.getenv('PI_PORT', '8080')       # Default port as fallback
RETRY_COUNT = 3                            # Number of repetitions
TIMEOUT = 5                                # Seconds per request

BASE_URL = f"http://{HOST}:{PORT}"

def health_check():
    for attempt in range(RETRY_COUNT):
        try:
            response = requests.get(BASE_URL, timeout=TIMEOUT)
            if response.status_code == 200:
                print(f"[OK] Healthcheck successful - status: {response.status_code}")
                return 0  # Success
            else:
                print(f"[WARN] Unexpected statuscode: {response.status_code}, attempt {attempt+1}/{RETRY_COUNT}")
        except requests.ConnectionError:
            print(f"[ERROR] No connections to {BASE_URL}, attempt {attempt+1}/{RETRY_COUNT}")
        except requests.Timeout:
            print(f"[ERROR] Timeout after {TIMEOUT} seconds at {BASE_URL}, attempt {attempt+1}/{RETRY_COUNT}")
        except Exception as e:
            print(f"[ERROR] Unexpected failure: {str(e)}, attempt {attempt+1}/{RETRY_COUNT}")

        time.sleep(2) # Wait briefly before the next attempt is made 

    print(f"[CRITICAL] Healthcheck failed after {RETRY_COUNT} attempts.")
    sys.exit(1)  # Faulty container status

if __name__ == "__main__":
    sys.exit(health_check())

