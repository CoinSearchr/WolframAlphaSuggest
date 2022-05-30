import re
import requests
import random

from ratelimit import limits, RateLimitException
from backoff import on_exception, expo


def extract_re(regex, txt, group_number):
	s = re.search(regex, txt)
	try:
		return s.group(group_number)
	except:
		return None
	
@on_exception(expo, (RateLimitException, Exception), max_time=5, max_tries=10)
def call_url_max5sec(url: str) -> requests.Response:
	response = requests.get(url)
	if response.status_code not in [200, 501]: # 501 is a "Not Implemented" code
		raise Exception(f'API response ({response.status_code}) to {url}: {response.text}')
	return response

