import time
import datetime
import json
import random
import operator
from slackclient import SlackClient

sc = None
sentLunchReminder = 0

def Initialize():
	with open('LunchbotSettings.json') as json_data:
		settings = json.load(json_data)
		token = settings['token']
		
		global sc
		sc = SlackClient(token)
		return True
	return False

def GetChannel():
	with open('LunchbotSettings.json') as json_data:
		settings = json.load(json_data)
		return settings['lunchChannel'] 
	
def SendMessage(message):
	possibleIcons = [':pizza:', ':bread:', ':fried_shrimp:', ':poultry_leg:', ':meat_on_bone:', ':hamburger:', ':taco:', ':spaghetti:', ':burrito:', ':ramen:', ':stew:', ':bento:', ':curry:', ':oden:']
	icon = random.choice(possibleIcons)
	print sc.api_call('chat.postMessage', channel=GetChannel(), text=message, username='LunchtimeBot', icon_emoji=icon)
	
def GetSubOfTheDay():
	message = ' ($6 sub of the day: '
	weekday = datetime.datetime.today().weekday()
	if weekday == 0:
		return message + 'sweet onion chicken teriyaki)'
	elif weekday == 1:
		return message + 'oven roasted chicken)'
	elif weekday == 2:
		return message + 'turkey breast)'
	elif weekday == 3:
		return message + 'italian B.M.T.)'
	elif weekday == 4:
		return message + 'tuna)'
	
def GetUserInfo(lunchbotUser):
	userInfo = sc.api_call('users.info', user=lunchbotUser)
	
	if userInfo is None or userInfo['ok'] == False:
		return ''
	else:
		return userInfo['user']['name']
		
def GetLunchLocationName(data, search):
	for location in data['locations']:
		if search == str(location['key']):
			return location['name']	
	return ''
	
def GetTodaysFrontrunner(data):
	today = datetime.datetime.today().strftime("%m/%d/%Y")
	
	popularChoices = {}
	
	for user in data['users']:
		#find today's choice for this user
		for choice in user['lunchChoices']:
			if choice['date'] == today:
				choiceToday = choice['choice']
				
				if choiceToday in popularChoices:
					print 'incrementing choice ' + str(choiceToday)
					popularChoices[choiceToday] += 1
				else:
					print 'first time seeing choice ' + str(choiceToday)
					popularChoices[choiceToday] = 1
					
	mostPopularChoiceText = ''
	mostPopularNumVotes = 0
	
	if len(popularChoices) > 0:
		#get the most popular choice and how many votes it got
		mostPopularNumVotes = str(max(popularChoices.values()))
		print 'mostPopularNumVotes: ' + str(mostPopularNumVotes)
		
		mostPopularChoice = max(popularChoices,key=popularChoices.get)  
		print 'mostPopularChoice: ' + str(mostPopularChoice)
		
		for location in data['locations']:
			if str(location['key']) == str(mostPopularChoice):
				print 'found'
				mostPopularChoiceText = location['name']
		
	return mostPopularChoiceText, mostPopularNumVotes
	
def GetAllUsers(data):
	users = ''
	for user in data['users']:
		if user['active'] == '1':
			users += '<@' + user['slackId']  + '|' + user['name'] + '>, '
	return users
	
def SendLunchReminder(data):
	mostPopularChoiceText, mostPopularNumVotes = GetTodaysFrontrunner(data)
	
	if int(mostPopularNumVotes) == 0:
		SendMessage('This is a reminder to choose a lunch option.')
	elif int(mostPopularNumVotes) == 1:
		SendMessage('This is a reminder to choose a lunch option. The current frontrunner is:')
		time.sleep(2)
		SendMessage(mostPopularChoiceText + ' with ' + mostPopularNumVotes + ' vote(s)')
	else:
		SendMessage('Hop on the ' + mostPopularChoiceText + ' train. ' + mostPopularNumVotes + ' votes so far')
	
def SendGoToLunchMessage(data):	
	mostPopularChoiceText, mostPopularNumVotes = GetTodaysFrontrunner(data)
	
	if mostPopularNumVotes == 0:
		SendMessage('No one picked where to go to lunch :frowning:')
	else:
		SendMessage('The polls have closed! The winner is:')
		time.sleep(3)
		SendMessage(mostPopularChoiceText + ' with ' + mostPopularNumVotes + ' vote(s)')
		time.sleep(1)
		SendMessage('Please head downstairs and enjoy lunch')
		
def SendLunchInvitation():
	with open('LunchbotData.json') as json_data, open('LunchbotSettings.json') as json_settings:
		data = json.load(json_data)
		settings = json.load(json_settings)

		#don't send a lunch invitation on weekends
		weekday = datetime.datetime.today().weekday()
		if weekday == 5 or weekday == 6:
			return
		
		lunchtimeHour = int(settings['lunchtimeHour'])
		lunchtimeMinute = int(settings['lunchtimeMinute'])
		lunchtimeReminder = int(settings['reminder'])
		lunchtime = datetime.timedelta(hours=lunchtimeHour, minutes=lunchtimeMinute)
		
		reminderTime = lunchtime - datetime.timedelta(minutes=lunchtimeReminder)
		currentTime = datetime.datetime.now()

		global sentLunchReminder
		
		if currentTime.hour == (reminderTime.seconds / 3600) and currentTime.minute == ((reminderTime.seconds / 60)%60):
			if sentLunchReminder == 0:
				users = GetAllUsers(data)
				SendMessage('Lunch time soon! ' + users + 'interested?')
				
				#show lunch options from json
				options = 'Here are the options:\n'
				for location in data['locations']:
					if location['active'] == '1':
						lunchDestination = location['key'] + ' - ' + location['name']
					
						#add the sub of the day for subway
						if location['name'].lower() == 'subway':
							lunchDestination += GetSubOfTheDay()
					
						options += lunchDestination + '\n'
				
				time.sleep(1)
				SendMessage(options)
				
				#increment the counter so the bot will look for incoming votes
				sentLunchReminder = 1
				
		if sentLunchReminder > 0:
			#increment the count every second once it starts
			sentLunchReminder += 1

			#send a reminder after 5 minutes and 10 minutes
			if sentLunchReminder == 300 or sentLunchReminder == 600:
				SendLunchReminder(data)
			elif sentLunchReminder == 900:
				#send final tally and stop everything after 15 minutes
				sentLunchReminder = 0
				SendGoToLunchMessage(data)
				
def ProcessLunchVote(choiceMessage, user):
	data = ''
	success = 0
	
	username = ''
	chosenLocation = ''
	existingChoice = 0
	existingUser = 0

	#get the first number in the message
	firstNumber  = [int(s) for s in choiceMessage.split() if s.isdigit()]
	
	if len(firstNumber) > 0:
		choice = firstNumber[0]
		print 'choice:' + str(choice)
		
		with open('LunchbotData.json', 'r') as json_data:
			data = json.load(json_data)
			
			today = datetime.datetime.today().strftime("%m/%d/%Y")
			
			locations = data['locations']
			
			for location in locations:
				if str(choice) == location['key']: 
					username = GetUserInfo(user)
					chosenLocation = location['name']
					
					users = data['users'] 
						
					for user in users:
						if user['name'] == username:
						
							#don't let inactive users vote
							if user['active'] == '0':
								SendMessage('Refused to process ' + username + '\'s vote. Zombies may not vote.')
								return
						
							existingUser = 1
							print 'found ' + username
							#found this user
							lunchChoices = user['lunchChoices']
							
							for lunchChoice in lunchChoices:
								if lunchChoice['date'] == today:
									#changing today's choice
									existingChoice = 1
									lunchChoice['choice'] = choice
									
							if existingChoice == 0:
								print 'no existing choice'
								#no choice for today yet so add one
								newChoice = {}
								newChoice['date'] = today
								newChoice['choice'] = choice

								user['lunchChoices'].append(newChoice)
					
					if existingUser == 0:
						#user not found, make a new one with today's choice
						newUser = {}
						newUser['name'] = username
						newUser['slackId'] = user
						
						newChoice = {}
						newChoice['date'] = today
						newChoice['choice'] = choice
						newUser['lunchChoices'] = {}
						newUser['lunchChoices'] = [newChoice]
						
						#now add the new user to the list of users
						users.append(newUser)
						
					success = 1

	#only update if the parsing was successful		
	if success == 1:
		if existingChoice == 1:
			SendMessage(username + ' has changed their decision. They would now like to go to "' + chosenLocation + '"')
		else:
			SendMessage(username + ' has chosen "' + chosenLocation + '"')
			
		#override the file with the new choice
		with open('LunchbotData.json', 'w') as json_data:
			json.dump(data, json_data, sort_keys=True, indent=2)
		
def GetStatistics(message):
	#message should look like "lunchbot stats:<user or location>"
	messageParts = message.split(':')
	desiredStat = messageParts[1].strip()
	
	with open('LunchbotData.json') as json_data:
		data = json.load(json_data)
		
		#look to see if a username matches the input
		users = data['users'] 
		for user in users:
			if user['name'] == desiredStat:
				GetUserStatistics(desiredStat)
				return
		
		#if we didn't find any user name matches then see if a location matches the input
		locations = data['locations'] 
		for location in locations:
			if location['name'] == desiredStat:
				GetLocationStatistics(desiredStat)
				return
		
		#did not find any matching information to look up statistics on
		SendMessage('Could not find any statistics for \'' + desiredStat + '\'')
	
#TO-DO: location stats
#num days a location has gotten at least one vote
#num days location has won
#total votes overall for location		
def GetLocationStatistics(location):
	SendMessage('Summary for: ' + location + ':')

#TO-DO: just pass in the user object instead of finding by the name again
def GetUserStatistics(username):	
	numVotes = 0;
	favoriteLunchLocations = {}
	
	with open('LunchbotData.json') as json_data:
		data = json.load(json_data)
		
		users = data['users'] 
		for user in users:
			if user['name'] == username:
				lunchChoices = user['lunchChoices']
				numVotes = len(lunchChoices)

				for choice in user['lunchChoices']:
					location = choice['choice']
				
					if location in favoriteLunchLocations:
						favoriteLunchLocations[location] += 1
					else:
						favoriteLunchLocations[location] = 1
						
		summary = username + ' has voted ' + str(numVotes) + ' time(s)'

		if len(favoriteLunchLocations) > 0:
			#sort the list by the number of votes
			sortedVotes = sorted(favoriteLunchLocations.items(), key=operator.itemgetter(1), reverse=True)
			favoriteLocation = GetLunchLocationName(data, str(sortedVotes[0][0]))
			summary += '\n' + username + '\'s favorite location is: ' + favoriteLocation + ' with ' + str(sortedVotes[0][1]) + ' votes'
			
		SendMessage(summary)

def SetLunchTime(message):
	#message should look like "luncbot set time:<time>"
	messageParts = message.split(':')
	if len(messageParts) == 3:
		desiredHour = messageParts[1].strip()
		desiredMinute = messageParts[2].strip()
		
		#default to the time being in PM
		isPM = True
		if desiredMinute.lower().endswith('am'):
			isPM = False
		
		#strip the am/pm so converting to an int works
		desiredMinute=''.join(i for i in desiredMinute if i.isdigit())
		
		if isPM and int(desiredHour) < 12:
			desiredHour = str(int(desiredHour) + 12)

		settings = ''
		with open('LunchbotSettings.json', 'r') as json_settings:
			settings = json.load(json_settings)	
			settings["lunchtimeHour"] = int(desiredHour)
			settings["lunchtimeMinute"] = int(desiredMinute)
			
		#override the file with the new choice
		with open('LunchbotSettings.json', 'w') as json_data:
			json.dump(settings, json_data, sort_keys=True, indent=2)
			
		message = 'Lunchtime has been moved to ' + desiredHour + ':' + desiredMinute
		SendMessage(message)
		
		#if voting is currently happening postpone it
		global sentLunchReminder
		if sentLunchReminder > 0:
			sentLunchReminder = 0
			SendMessage('Voting has been postponed')
	
def AddLunchLocation(message):
	#message should look like "lunchbot add location:<location>"
	messageParts = message.split(':')
	newLocationName = messageParts[1].strip()
	data = ''
	
	with open('LunchbotData.json') as json_data:
		data = json.load(json_data)
		
		#check if the location already exists
		for location in data['locations']:
			if location['name'].lower() == newLocationName.lower():
				SendMessage(newLocationName + ' already exists')
				return
				
		#location doesn't exist, so add it 	
		newLocation = {}
		newLocation['name'] = newLocationName
		newLocation['active'] = "1"
		currentMaxKey = max(data['locations'], key= lambda x: int(x['key']))
		newKey = int(currentMaxKey['key']) + 1
		newLocation['key'] = str(newKey)
		data['locations'].append(newLocation)
		
	with open('LunchbotData.json', 'w') as json_data:
		json.dump(data, json_data, sort_keys=True, indent=2)	
		SendMessage('Added ' + newLocationName)

def RetireUser(message):
	#message should look like "lunchbot retire:<username>"
	messageParts = message.split(':')
	desiredUser = messageParts[1].strip()
	data = ''
	foundUserToDelete = 0
	
	with open('LunchbotData.json') as json_data:
		data = json.load(json_data)
		
		users = data['users'] 
		for user in users:
			if user['name'] == desiredUser:
				foundUserToDelete = 1
				user['active'] = '0'
				
	if foundUserToDelete == 1:
		#override the file
		with open('LunchbotData.json', 'w') as json_data:
			json.dump(data, json_data, sort_keys=True, indent=2)
			
		SendMessage(desiredUser + ' has been retired. May he rest in peace.')
	else:
		SendMessage('Could not find: ' + desiredUser)	

if Initialize():			
	if sc.rtm_connect():
		while True:
			SendLunchInvitation()
			new_evts = sc.rtm_read()
			for evt in new_evts:
				print(evt)
				print
				if "type" in evt:
					if evt["type"] == "message" and "text" in evt:
						channel=evt["channel"]			
						message=evt["text"].lower()
						if message.startswith('lunchbot stats:') or message.startswith('lunch statistics:'):
							GetStatistics(message)
						elif message.startswith('lunchbot set time:'):
							SetLunchTime(message)
						elif message.startswith('lunchbot retire:'):
							RetireUser(message)
						elif message.startswith('lunchbot add location:'):
							AddLunchLocation(message)							
							
						#if sentLunchReminder > 0 we're in lunch voting mode
						if sentLunchReminder > 0:
							if 'user' in evt:
								user=evt['user']	
								ProcessLunchVote(message, user)
						message = ""
			new_evts = ""				
		
			time.sleep(1)
	else:
		print "Connection Failed, try checking the token"
else:
	print "Initialize failed, try checking LunchbotSettings"
