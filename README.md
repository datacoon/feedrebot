# feedrebot
FeedRetranslatorBot translates your RSS feed or news on webpage to the telegram channel/channels

Warning: all messages inside bot are in Russian (cyrillic), it's not translated to any other language.

Installation:
1. Get bot key via Telegram BotFather https://t.me/BotFather
2. Write key into .key_newsbot file at the same directory as news2rsscmd.py file
3. Run cmd 'python3 news2rsscmd.py init <username>' where username is your public useid in telegram (starts with @ sign but without it). Example: python3 news2rsscmd.py init ibegtin 
4. Run your bot as 'python3 news2rssbot.py'
5. Connect your bot via telegram and use it's commands to add channels and feeds. Use '/help' command to start

Requirements:
 - MongoDB
 - mongoengine
 - newsworker (https://github.com/ivbeg/newsworker)
 - click
 - python-telegram-bot
