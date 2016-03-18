from scrapy import Spider, Request

import SlippyFuncs as sf
import json
import re
import os
import warnings
import sys

# =====================================================================
# Globals
seasons = range(2015, 2016)
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
		fname = 'Conferences.json'
		sf.dump_json(data['Conferences'], fname, fdir=fdir, indent=4)

		# Save Team data
		teamkeys = [key for key in data['Teams'].keys()]
		for key in teamkeys:
			fdir = 'data/' + str(data['Season']) + '/teams/'
			fname = str(data['Teams'][key]['School']) + '.json'
			sf.dump_json(data['Teams'][key], fname, fdir=fdir, indent=4)

		# Save weeks data
		fdir = 'data/' + str(data['Season']) + '/'
		fname = 'Weeks.json'
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
	for season in seasons:
		try:
			# load season data
			weeks = sf.weeks_in_season(season)
			# regular season
			for week in weeks:
				start_urls.append(base_url + str(season) + '&seasonType=1&week=' + str(week))
			# bowls
			start_urls.append(base_url + str(season) + '&seasonType=2')
		except IOError:
			warnings.warn("Season info ("+ str(season) +") not collected. Run \"scrapy crawl seasoninfo\" then try again.", UserWarning)

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
			fname = 'gameinfo_' + str(game['Id']) + '.json'
			sf.dump_json(game, fname, fdir=fdir, indent=4)


class TeamStatsSpider(Spider):
	"""
	Scrapes the boxscores for each game. Uses links
	collected by GameInfoSpider and must be run after
	game info has been collected.

	NOTE: This spider grabs the boxscore stats from the
	"Team Stats page and creates the boxscore JSON file.
	BoxscoreSpider gets the rest of the boxscore stats to
	complete the file.
	"""
	name = 'teamstats'
	allowed_domains = ['http://www.foxsports.com']

	#Build URLs
	base_url = 'http://www.foxsports.com'
	start_urls = []
	for season in seasons:
		try:
			# load season data
			weeks = sf.weeks_in_season(season)
			# grab links from game info files
			for root, dirs, files in os.walk(os.path.join('data', str(season), 'gameinfo')):
				for f in files:
					if re.match(r'gameinfo_\d+\.json', f):
						game = sf.load_json(f, fdir=root)
						start_urls.append(base_url + game['Links']['boxscore'] + '&type=3')
		except IOError:
			warnings.warn("Game info ("+ str(season) +") not collected. Run \"scrapy crawl gameinfo\" then try again.", UserWarning)

	def parse(self, response):

		# Find folder location and set up data struct
		folder, gameid = sf.find_game_folder(response)

		try:
			teamstats = {}
			teamstats['awayTeam'] = {}
			teamstats['homeTeam'] = {}
			stats_area = response.xpath('//div[contains(@class,"wisfb_bsTeamStats")]')

			# Get team names
			tm_divs = stats_area.xpath('.//div[contains(@class,"wisfb_bstsTeamDisplay")]')
			teamstats['awayTeam']['nameFull'] = tm_divs[0].xpath('.//span[contains(@class,"wisfb_bsFull")]/text()').extract()[0]
			teamstats['awayTeam']['nameShort'] = tm_divs[0].xpath('.//span[contains(@class,"wisfb_bsShort")]/text()').extract()[0]
			teamstats['homeTeam']['nameFull'] = tm_divs[1].xpath('.//span[contains(@class,"wisfb_bsFull")]/text()').extract()[0]
			teamstats['homeTeam']['nameShort'] = tm_divs[1].xpath('.//span[contains(@class,"wisfb_bsShort")]/text()').extract()[0]

			# Get boxscore stats
			boxtable = stats_area.xpath('.//tbody')
			stat_data = boxtable.xpath('.//td[contains(@class,"wisfb_bstsStat")]/text()').extract()
			stat_type = boxtable.xpath('.//td[contains(@class,"wisfb_bstsTitle")]/text()').extract()
			# away stats
			for sdata, stype in zip(stat_data[::2], stat_type[::2]):
				sf.add_boxscore_data(sdata, stype, teamstats['awayTeam'])
			# home stats
			for sdata, stype in zip(stat_data[1::2], stat_type[1::2]):
				sf.add_boxscore_data(sdata, stype, teamstats['homeTeam'])

			sf.dump_json(teamstats, 'boxscore.json', fdir=folder, indent=4)

		# Log where problem occurred to debug scraper later
		except Exception,error:
			with open(os.path.join(folder, 'bad_boxscore.json'), 'w') as f:
				f.write("ERROR: " + str(error) + "\n" + 
						" LINE: " + str(sys.exc_info()[-1].tb_lineno) + "\n" + 
						" GAME: " + str(gameid) + "\n" + 
						"  URL: " + response.url)


class PlayerStatsSpider(Spider):
	"""
	Scrapes the boxscores for each game. Uses links
	collected by GameInfoSpider and must be run after
	game info has been collected.
	"""
	name = 'playerstats'
	allowed_domains = ['http://www.foxsports.com']

	#Build URLs
	base_url = 'http://www.foxsports.com'
	start_urls = []
	for season in seasons:
		try:
			# load season data
			weeks = sf.weeks_in_season(season)
			# grab links from game info files
			for root, dirs, files in os.walk(os.path.join('data', str(season), 'gameinfo')):
				for f in files:
					if re.match(r'gameinfo_\d+\.json', f):
						game = sf.load_json(f, fdir=root)
						start_urls.append(base_url + game['Links']['boxscore'])
		except IOError:
			warnings.warn("Game info ("+ str(season) +") not collected. Run \"scrapy crawl gameinfo\" then try again.", UserWarning)

	
	def parse(self, response):

		# Find folder location and set up data struct
		folder, gameid = sf.find_game_folder(response)

		try:
			# Assume away team is in first column
			main_content = response.xpath('//div['+ sf.contains_str('wisfb_bsMainContent') +']')
			box_areas = main_content.xpath('.//div['+ sf.contains_str('wisfb_bsArea') +']')
			playerstats = {}
			playerstats['awayTeam'] = {}
			playerstats['homeTeam'] = {}
			teams = ['awayTeam', 'homeTeam']
			# Find all stat types
			for area in box_areas:
				# Go to stat table per team
				team_tables = area.xpath('.//div['+ sf.contains_str('wisfb_bsTable') +']')
				for i, table in enumerate(team_tables):
					column = table.xpath('.//table['+ sf.contains_str('wisfb_bsStandard') +']')
					header = column.xpath('.//thead/tr/th/text()').extract()
					player_cols = column.xpath('.//tbody/tr')
					playerstats[teams[i]][header[0]] = {}
					# Find all players with stat
					for player in player_cols:
						try:
							name = player.xpath('.//td['+ sf.contains_str('wisfb_bsNameCell') +']/a/text()').extract()[0]
						except IndexError:
							name = player.xpath('.//td['+ sf.contains_str('wisfb_bsNameCell') +']/span/text()').extract()[0]
						stats = player.xpath('.//td[contains(@class,"wisfb_priority")]/text()').extract()
						playerstats[teams[i]][header[0]][name] = {}
						for j, stat in enumerate(stats):
							try:
								stat = float(stat)
							except ValueError:
								# Won't work when stat is null ("-")
								pass
							playerstats[teams[i]][header[0]][name][header[j+1]] = stat
			# Put players stats totals into boxscore file as well
			try:
				teamstats = sf.load_json('boxscore.json', fdir=folder)
			except IOError:
				teamstats = {}
			for team, stats in playerstats.iteritems():
				for statType, players in stats.iteritems():
					try:
						for stat, data in players['Total'].iteritems():
							teamstats[team][statType +' '+ stat] = data
					except KeyError:
						pass

			sf.dump_json(teamstats, 'boxscore.json', fdir=folder, indent=4)
			sf.dump_json(playerstats, 'playerstats.json', fdir=folder, indent=4)

		# Log where problem occurred to debug scraper later
		except Exception,error:
			with open(os.path.join(folder, 'bad_playerstats.json'), 'w') as f:
				f.write("ERROR: " + str(error) + "\n" + 
						" LINE: " + str(sys.exc_info()[-1].tb_lineno) + "\n" + 
						" GAME: " + str(gameid) + "\n" + 
						"  URL: " + response.url)

