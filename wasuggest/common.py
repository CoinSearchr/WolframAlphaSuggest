import re
import requests
import random
import urllib.parse
import time

from ratelimit import limits, RateLimitException
from backoff import on_exception, expo

from . import app, cache
from . import db
logger = app.logger

req_session = requests.Session()

def extract_re(regex, txt, group_number):
	s = re.search(regex, txt)
	try:
		return s.group(group_number)
	except:
		return None
	
@on_exception(expo, (RateLimitException, Exception), max_time=5, max_tries=10)
def call_url_max5sec(url: str, timeout_sec: float) -> requests.Response:
	response = req_session.get(url, timeout=timeout_sec)
	if response.status_code not in [200, 501]: # 501 is a "Not Implemented" code
		raise Exception(f'API response ({response.status_code}) to {url}: {response.text}')
	return response


class cache_obj:
	def __init__(self, first_result: str):
		self.results_history: List[str] = [first_result]
		self.last_new_result_time: float = time.time()
		self.ever_had_varying_results: bool = False

	def add_result(self, result: str):
		""" Add a result, ensuring that the list doesn't get too long. """
		
		if result not in self.results_history:
			self.ever_had_varying_results = True

		self.results_history.append(result)
		if len(self.results_history) > 20:
			self.results_history.pop()

		self.last_new_result_time = time.time()

class MyMemoize:
	"""
	An advanced function memoization tool to cache API calls to WA to limit API call usage and increase speed.
	Designed to play nice with random number generation requests, "what time is it", etc.from WolframAlpha.
	"""
	
	def __init__(self, f):
		self.f = f
		self.memo = {}

	def __call__(self, search_term):
		if not search_term in self.memo:
			# never been called before, not in cache
			result = self.f(search_term)
			self.memo[search_term] = cache_obj(result)
			logger.info(f"New cache for search_term '{search_term}'.")
			return result

		elif len(self.memo[search_term].results_history) <= 2:
			# not enough calls yet
			result = self.f(search_term)
			self.memo[search_term].add_result(result)
			logger.info(f"Not enough calls for '{search_term}' to trust cache.")
			return result

		elif self.memo[search_term].ever_had_varying_results:
			# had enough calls, but the results differ, and we know they differ
			logger.info(f"Calls for search_term '{search_term}' have differed, so doing new call.")
			return self.f(search_term)

		elif (time.time() - self.memo[search_term].last_new_result_time) > (2 ** len(self.memo[search_term].results_history)):
			# it's been a long time since we checked for a new result; check for a result to ensure it hasn't changed
			logger.info(f"It's been a while for search_term '{search_term}' so checking there's no new result.")
			result = self.f(search_term)
			self.memo[search_term].add_result(result)
			return result

		logger.info(f"Using cached result for '{search_term}'.")
		return self.memo[search_term].results_history[-1]

@MyMemoize
def wa_simple_lookup(search_term: str) -> str:
	""" Perform WA API request on non-escaped string `search_term`, and return a non-escaped result. Use caching if appropriate. """
	api_key = random.choice(db.config['wolframalpha']['api_keys_list'])

	url = f'https://api.wolframalpha.com/v1/result?appid={api_key}&i={urllib.parse.quote_plus(search_term)}&timeout={db.config["wolframalpha"]["timeout_sec"]}&units=metric'
	logger.info(f"Making request to: {url}")

	try:
		return call_url_max5sec(url, timeout_sec=db.config["wolframalpha"]["timeout_sec"]+1.0).text
	except Exception as e:
		logger.info(f"Error calling WolframAlpha API: {e}")
		return '???'

logger.info(f"Doing test WA API call to init session. 'random int' -> '{wa_simple_lookup('random int')}'.")

