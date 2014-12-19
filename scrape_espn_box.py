# ESPN CFB Box Score Scraping
import pandas as pd
import numpy as np
import requests
import re
from bs4 import BeautifulSoup as bsoup

# Initiate empty DFs
df_games = pd.DataFrame()
df_drives = pd.DataFrame()
df_plays = pd.DataFrame()

url_pattern = 'http://scores.espn.go.com/ncf/scoreboard?confId=80&seasonYear=%s&seasonType=2&weekNumber=%d' # (year, wk)

errfile = 'cfb_espn_err'
f = open(errfile, 'w')
f.close()

def log_err(file, vals):
	f = open(errfile, 'a')
	errmsg = '%s\n' % vals
	f.write(errmsg)
	f.close()
	pass



years = range(2005,2015)
# weeks = range(1,12)
max_wk = {
	2005: 16,
	2006: 17,
	2007: 17,
	2008: 17,
	2009: 16,
	2010: 16,
	2011: 16,
	2012: 16,
	2013: 17,
	2014: 10
}

# year=2013
# wk = 17


for year in years:
	print year
	for wk in range(1,max_wk[year]+1):
		print wk
		url = url_pattern % (year, wk)
		html = requests.get(url)
		soup = bsoup(html.text, 'html.parser')

		score_map = ['Q1', 'Q2', 'Q3', 'Q4', 'OT', 'FIN']

		games = []
		game_divs = soup.findAll('div', {'class': 'mod-content'})
		for g in game_divs:	# check if visitor element exists
			game_periods = ['Q1', 'Q2', 'Q3', 'Q4', 'OT', 'Final']
			game_dict = {}
			game_id = g.span.text if g.span else None
			# If this is a game record
			if game_id:
				# ot = 'OT' in game_status.p.text
				game_dict['game_id'] = game_id
				# teams
				vis = g.find('div', {'class' : 'team visitor'})
				home = g.find('div', {'class' : 'home'})
				game_dict['visitor'] = vis.a.text
				game_dict['home'] = home.a.text
				game_dict['year'] = year
				game_dict['week'] = wk
				
				# scores
				vscores = vis.find('ul', {'class': 'score'})
				hscores = home.find('ul', {'class': 'score'})
				# game_dict['visitor_scores'] = [s.text for s in vscores.findAll('li')]
				for i,m in enumerate(score_map):
					game_dict['visitor_%s' % m] = vscores.findAll('li')[i].text
				# game_dict['home_scores'] = [s.text for s in hscores.findAll('li')]
				for i,m in enumerate(score_map):
					game_dict['home_%s' % m] = hscores.findAll('li')[i].text
			
				games.append(game_dict)

		df_games_tmp = pd.DataFrame(games)
		df_games_tmp.set_index('game_id', inplace=True)

		df_games = pd.concat([df_games, df_games_tmp])


# df_games.index.map(get_pbp)
# df_drives.to_csv('drives.csv', index=True, header=True)
# df_plays.to_csv('plays.csv', index=True, header=True, encoding='utf-8')

def get_pbp(game_id):
	# game_id = 400548021
	global df_drives
	global df_plays
	global errfile
	pbp_url = 'http://espn.go.com/ncf/playbyplay?gameId=%s&period=0' % game_id
	print pbp_url
	try:
		html_game = requests.get(pbp_url)
		pbp_soup = bsoup(html_game.text, 'html.parser')

		tbl = pbp_soup.find('table', {'class': 'mod-pbp'})	# table.mod-pbp == Play By Play table

		drives = []
		plays = []
		game_vars = {'ball': None, 'period': None, 'time': None, 'v_pts': 0, 'h_pts': 0}
		drive_id = 0 	 # Initiate first drive_id as 0
		play_id = 0 	 # Initiate first drive_id as 0
		for child in tbl.children:
			if child.name == 'thead':
				qtr = child.find('div', {'class': 'mod-header'})
				drive_start = child.find('tr', {'class': 'team-color-strip'})
				drive_summ = child.find('tr', {'class': 'colhead'})
				if qtr:
					game_vars['period'] = qtr.h4.text[0]
					# print 'Period: ', game_vars['period']
					
				elif drive_start:
					play_id = 0 	 # Initiate first play_id as 0
					game_vars['ball'] = drive_start.th.text.split(' at ')[0].strip()
					game_vars['time'] = drive_start.th.text.split(' at ')[1].strip()
					# print game_vars['ball'],' ball at clock:',game_vars['time']
					drive = {
						'game_id' : game_id,
						'drive_id' : drive_id,
						'ball': game_vars['ball'],
						'period' : game_vars['period'],
						'start': game_vars['time'],
						'end' : None,
						'start_v_pts' : game_vars['v_pts'],
						'start_h_pts' : game_vars['h_pts'],
						'description': None
					}
					drives.append(drive)
					drive_id += 1
					# drive_id = len(drives)-1
					
				elif drive_summ:
					drives[drive_id-1]['description'] = drive_summ.text.strip()
					# Update Drive End Time ? 
			
			if child.name == 'tr':
				cells = child.findAll('td')
				if cells[2].text.strip():
					game_vars['v_pts'], game_vars['h_pts'] = cells[2].text, cells[3].text
				play = {
					'game_id' : game_id,
					'drive_id': drive_id,
					'play_id' : play_id,
					'situation': cells[0].text.strip(),
					'action': cells[1].text.strip()
				}
				play_id += 1
				plays.append(play)

		global df_drives
		df_drives_tmp = pd.DataFrame(drives)
		df_drives_tmp.set_index(['game_id', 'drive_id'], inplace=True)
		df_drives = pd.concat([df_drives, df_drives_tmp])

		global df_plays
		df_plays_tmp = pd.DataFrame(plays)
		df_plays_tmp.set_index(['game_id', 'drive_id', 'play_id'], inplace=True)
		df_plays = pd.concat([df_plays, df_plays_tmp])
	except:
		log_err(errfile, pbp_url)


# table.mod-pbp == Play By Play table
# thead div.mod-header ==  Quarter Start
# thead tr.team-color-strip == Drive Team/Start Time
# thead tr.colhead ==  Drive Summary Line
