import httpx, os
from dotenv import load_dotenv
load_dotenv('.env.local')
token = os.environ['RUNNER_TOKEN']
url = os.environ['PLATFORM_URL']
resp = httpx.get(f'{url}/api/v1/ui-automation/runner/next-job', params={'runner_token': token})
print(resp.status_code, resp.json())
