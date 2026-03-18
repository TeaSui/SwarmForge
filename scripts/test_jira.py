import requests
from config import settings

def test_jira_connection():
    print(f"Testing Jira Connection to: {settings.JIRA_BASE_URL}")
    url = f"{settings.JIRA_BASE_URL}/rest/api/3/myself"
    auth = (settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)
    
    try:
        response = requests.get(url, auth=auth)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ SUCCESS: Connected as {user_data.get('displayName')} ({user_data.get('emailAddress')})")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    if "your-domain" in settings.JIRA_BASE_URL or "your-email" in settings.JIRA_EMAIL:
        print("⚠️ Please update your .env with real Jira credentials first!")
    else:
        test_jira_connection()
