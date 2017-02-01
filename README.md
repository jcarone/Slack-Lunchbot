Tired of arguing with and rounding up your favorite coworkers from different departments when deciding what do to for lunch? Let slack lunchbot organize lunch for you!

Requirements
1.	Python
2.	Slack (duh)

Deployment
1.	Update the “token” in LunchbotSettings.json to your slack API token. Optionally change the lunchChannel, lunchtimeHour, lunchtimeMinute, and reminder to better suit your schedule
2.	Run lunchbot.py from the command line

Normal Usage
While running the bot will start a lunch vote in the specified lunch channel once per weekday, just before lunchtime (default start time is 11:45 PM with a 15 minute window for voting before lunch starts). Each slack user gets to cast 1 vote on where to go to lunch each day by sending a message in the lunch channel with the number that corresponds to a lunch option. After 15 minutes the votes will be tallied and a winner will be chosen

Additional Slack Commands
	Type any of the following commands as a message in slack to interact with lunchbot:
lunchbot add location:Panera		Adds Panera to the list of lunch choices
lunch statistics:jcarone			Get statistics on how jcarone has voted over time
lunchbot set time:1:00PM		Change lunchtime to 1 (13:00 also works)
lunchbot retire:jcarone			Stop including jcarone in the lunch vote process


License
This project is licensed under the MIT License - see the LICENSE.md file for details