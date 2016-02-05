from scrapy import Spider, Request

import SlippyFuncs as sf
import json
import re
import os
import warnings

# =====================================================================
# Globals
seasons = range(2000, 2016)
# ---------------------------------------------------------------------


class SeasonInfoSpider(Spider):
	"""
	Scrapes team data, conference data, and the number of 
	weeks in each season.
	"""
	name = 'seasoninfo'
	allowed_domains = ['http://www.foxsports.com']
	base_url = 'http://www.foxsports.com/foxbox/CFB/API/League/League?season='
	start_urls = [base_url + str(season) for season in seasons]

	def parse(self, response):
		# Make sure URL is good
		if response.body == '[]':
			return
		# Save json data	
		data = json.loads(response.body)

		# Save Conference data
		fdir = 'data/' + str(data['Season']) + '/'
		fname = 'Conferences.txt'
		sf.dump_json(data['Conferences'], fname, fdir=fdir, indent=4)

		# Save Team data
		teamkeys = [key for key in data['Teams'].keys()]
		for key in teamkeys:
			fdir = 'data/' + str(data['Season']) + '/teams/'
			fname = str(data['Teams'][key]['School']) + '.txt'
			sf.dump_json(data['Teams'][key], fname, fdir=fdir, indent=4)

		# Save weeks data
		fdir = 'data/' + str(data['Season']) + '/'
		fname = 'Weeks.txt'
		sf.dump_json(data['Weeks'], fname, fdir=fdir, indent=4)


class GameInfoSpider(Spider):
	"""
	Scrapes the top-level information for each game in
	the season. GameInfoSpider uses the week data scraped
	by SeasonInfoSpider and must be run after the season 
	info has been collected.
	"""
	name = 'gameinfo'
	allowed_domains = ['http://www.foxsports.com']

	# Build URLs
	base_url = 'http://www.foxsports.com/foxbox/CFB/API/League/Schedule?groupId=2&season='
	start_urls = []
	try:
		for season in seasons:
			# load season data
			weeks = sf.weeks_in_season(season)
			# regular season
			for week in weeks:
				start_urls.append(base_url + str(season) + '&seasonType=1&week=' + str(week))
			# bowls
			start_urls.append(base_url + str(season) + '&seasonType=2')
	except IOError:
		warnings.warn("Season info not collected. Run \"scrapy crawl seasoninfo\" then try again.", UserWarning)

	def parse(self, response):
		# Make sure URL is good
		if response.body == '[]':
			return
		# Save json data	
		games = json.loads(response.body)
		for game in games:
			if game['SeasonType'] == 1:
				fdir = 'data/' + str(game['Season']) + '/gameinfo/week_' + str(game['Week']) + '/game_' + str(game['Id'])
			else:
				fdir = 'data/' + str(game['Season']) + '/gameinfo/bowls/game_' + str(game['Id'])
			fname = 'gameinfo_' + str(game['Id']) + '.txt'
			sf.dump_json(game, fname, fdir=fdir, indent=4)


class BoxscoreSpider(Spider):
	"""
	Scrapes the boxscores for each game. Uses links
	collected by GameInfoSpider and must be run after
	game info has been collected.
	"""
	name = 'boxscore'
	allowed_domains = ['http://www.foxsports.com']

	#Build URLs
	base_url = 'http://www.foxsports.com'
	start_urls = []
	try:
		for season in seasons:
			# load season data
			weeks = sf.weeks_in_season(season)
			# grab links from game info files
			for root, dirs, files in os.walk(os.path.join('data', str(season), 'gameinfo')):
				for f in files:
					if re.match(r'gameinfo_\d+\.txt', f):
						game = sf.load_json(f, fdir=root)
						start_urls.append(base_url + game['Links']['boxscore'] + '&type=3')
	except IOError:
		warnings.warn("Game info not collected. Run \"scrapy crawl gameinfo\" then try again.", UserWarning)

	def parse(self, response):
		# Find folder location
		gameid = re.search(r'\?id=(?P<id>\d+)', response.url).group('id')
		folder = sf.find_game_folder(gameid)
		sf.dump_json(box, 'boxscore.txt', fdir=folder)