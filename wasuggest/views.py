from flask import Flask, render_template, jsonify, request, make_response, url_for, send_from_directory, redirect

from . import app, cache
from . import db
from . import common

import datetime, time
import re
import os
import pandas as pd
import logging
import random
import urllib.parse
#import dataclass
from typing import List

logger = app.logger #logging.getLogger(__name__)

site_config = db.config['site']

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

	url = f'https://api.wolframalpha.com/v1/result?appid={api_key}&i={urllib.parse.quote_plus(search_term)}&timeout={db.config["wolframalpha"]["timeout_sec"]}'
	logger.info(f"Making request to: {url}")

	try:
		return common.call_url_max5sec(url, timeout_sec=db.config["wolframalpha"]["timeout_sec"]+1.0).text
	except Exception as e:
		logger.info(f"Error calling WolframAlpha API: {e}")
		return '???'

logger.info(f"Doing test WA API call to init session. 'random int' -> '{wa_simple_lookup('random int')}'.")

@app.template_filter('pluralize')
def pluralize(number, singular = '', plural = 's'):
	if number == 1:
		return singular
	else:
		return plural


@app.context_processor
def inject_global_vars():
	""" These variables will be available in all templates. """
	return {
		'now': datetime.datetime.utcnow(), # access with {{ now.year }}
		
		'site_config': site_config,
	}

@app.route('/')
@cache.cached(timeout=3600*24)
def index():
	return render_template("index.jinja2")


@app.route('/search', methods=['GET']) # args: q=search_term
@cache.cached(timeout=600, query_string=True)
def search():
	
	arg_search_term_orig = request.args.get('q', '') # required for 'sanity check' by browser in suggestion mode
	arg_search_term = arg_search_term_orig.strip() # clean

	# remove garbage/result
	if ' => ' in arg_search_term:
		arg_search_term = arg_search_term.split(' => ')[0].strip()

	# redirect
	return redirect('https://www.wolframalpha.com/input/?i=' + urllib.parse.quote_plus(arg_search_term), 302)



@app.route('/suggest', methods=['GET']) # args: q=search_term
@cache.cached(timeout=1, query_string=True)
def suggest():
	"""
	Provide JSON search suggestions.

	Resources on Spec:
	- http://wiki.mozilla.org/Search_Service/Suggestions
	- Descriptor: https://github.com/dewitt/opensearch/blob/master/opensearch-1-1-draft-6.md#opensearch-11-parameters
	- https://developer.mozilla.org/en-US/docs/Web/OpenSearch
	"""
	
	arg_search_term_orig = request.args.get('q', '') # required for 'sanity check' by browser in suggestion mode
	arg_search_term = arg_search_term_orig.strip() # clean

	# remove garbage/result
	if ' => ' in arg_search_term:
		arg_search_term = arg_search_term.split(' => ')[0].strip()

	result = wa_simple_lookup(arg_search_term)

	suggest_results = [
		f"{arg_search_term} => {result}",
		f"{result}",
	]

	out = [
		arg_search_term_orig,
		suggest_results,
	]

	resp = make_response(jsonify(out))
	resp.headers['Content-Type'] = 'application/x-suggestions+json'
	return resp

@app.route('/contact')
@cache.cached(timeout=3600*24)
def contact():
	return render_template("contact.jinja2")


@app.route('/guide/firefox')
@cache.cached(timeout=3600*24)
def guide_firefox():
	return render_template("guide_firefox.jinja2")

@app.route('/guide/vivaldi')
@cache.cached(timeout=3600*24)
def guide_vivaldi():
	return render_template("guide_vivaldi.jinja2")


@app.route('/favicon.ico')
#@cache.cached(timeout=3600*24)
def favicon():
	return send_from_directory(os.path.join(app.root_path, 'static', 'img'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/robots.txt')
#@cache.cached(timeout=3600*24)
def robots_txt():
	return send_from_directory(os.path.join(app.root_path, 'static', 'other'), 'robots.txt', mimetype='text/plain')

@app.route('/privacy')
@app.route('/privacypolicy')
@app.route('/privacy-policy')
@cache.cached(timeout=3600*24)
def privacypolicy():
	return render_template("privacypolicy.jinja2")
