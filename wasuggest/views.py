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

	result = common.wa_simple_lookup(arg_search_term)

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
