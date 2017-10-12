# Simple python screen scraper for WMATA SmarTrip Card Usage History Data
# Scrapes data from WMATA's website and returns clean CVS file of SmarTrip Card Usage History.
# NOTES - ONLY THING NECESSARY IS TO ADD USER NAME AND PASSWORD IN CODE

# importing libs
import BeautifulSoup
import mechanize
import csv
import sys
import datetime
import re
import os
from dateutil.parser import parse

now = datetime.datetime.now()

br = mechanize.Browser()
br.open("https://smartrip.wmata.com/Account/AccountLogin.aspx") #login page

br.select_form(nr=0) #form name

br["ctl00$ctl00$MainContent$MainContent$txtUsername"] = os.environ['WMATA_SMARTRIP_USERNAME'] #<-- enter your username here
br["ctl00$ctl00$MainContent$MainContent$txtPassword"] = os.environ['WMATA_SMARTRIP_PASSWORD'] #<-- enter your password here

response1 = br.submit().read()

if len(sys.argv) == 1:
	# download the first card, but show all card names so the user can choose

	print "Available cards are..."
	for cards in re.findall(r"CardSummary.aspx\?card_id=(\d+)\">(.*?)<", response1):
		print cards[0], cards[1]
	print ""
	print "And you can specify a card number on the command line!"
	print

	matching_card = re.search(r"CardSummary.aspx\?card_id=(\d+)\">(.*?)<", response1)
	if not matching_card: raise Exception("card not found")
	card_id = matching_card.group(1)
	card_name = matching_card.group(2)

	print "Downloading data for...", card_id, card_name

else:
	# download just one card's data
	card_id = sys.argv[1]

#follows link to View Card Summary page	for a particular card
response1 = br.follow_link(url_regex=r"CardSummary.aspx\?card_id=" + card_id).read()

#follows link to View Usage History page for a particular card
response1 = br.follow_link(text_regex=r"Use History").read()

br.select_form(nr=0)

response1 = br.submit().read()

br.select_form(nr=0)

#transaction status either 'All' or 'Successful' or 'Failed Autoloads'; All includes every succesful transaction including failed (card didn't swipe or error)
br["ctl00$ctl00$MainContent$MainContent$ddlTransactionStatus"] = ["All"]

br.submit()

#write files
fieldnames = ['sequence', 'timestamp', 'description', 'operator', 'entry_location_or_bus_route', 'exit_location', 'product', 'change', 'balance']
g = csv.writer(open('wmata_log_' + card_id + '.csv', 'w'))

csvrows = []
#wmata only started posting data in 2010, pulls all available months
for year in xrange(2010, now.year+1):
	for month in xrange(1, 12+1):
		time_period = ("%d%02d" % (year, month))
		print "\t", time_period

		try:
			#opens link to 'print' version of usage page for easier extraction
			response1 = br.open("https://smartrip.wmata.com/Card/CardUsageHistoryPrint.aspx?card_id=" + card_id + "&period=M&month=" + time_period)
		except Exception as e:
			print e
			continue

		#extracts data from html table, writes to csv
		soup = BeautifulSoup.BeautifulSoup(response1.read())
		t = soup.findAll('table')[1:]

		for table in t:
			rows = table.findAll('tr')
			for tr in rows:

				cols = tr.findAll('td')
				column_vals = [str(td.find(text=True)) for td in cols]
				if len(column_vals) == 9:
					column_vals[1] = parse(column_vals[1])
					column_vals[7] = float(column_vals[7])
					column_vals[8] = float(column_vals[8])
					csvrows.append(column_vals)
				elif len(column_vals) == 3:

					last_row = csvrows.pop()
					last_row[6] = '{} + {}'.format(last_row[-3], column_vals[0])
					last_row[7] = last_row[7] + float(column_vals[1])
					last_row[8] = last_row[8] + float(column_vals[2])
					csvrows.append(last_row)
				else:
					#raise ValueError('Found unexpected number of columns ({})'.format(len(column_vals)))
g.writerow(fieldnames)
g.writerows(csvrows)
