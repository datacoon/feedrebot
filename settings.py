# -*- coding: utf-8 -*-
import logging
import logging.handlers
#logging.basicConfig(
#        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#        level=logging.DEBUG)

#logger = logging.getLogger(__name__)


LOG_FILENAME = 'feedrebot.log'

# Set up a specific logger with our desired output level
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

## Check if log exists and should therefore be rolled
#needRoll = os.path.isfile(LOG_FILENAME)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, backupCount=50, maxBytes=10000000)

logger.addHandler(handler)


BOT_KEY = '/.key_newsbot'

# Number of entries in one digest
DIGEST_LIMIT = 10


# Enable/disable debugging
BOT_DEBUG = True
BOT_EXC_TIMEOUT = 20
BOT_TIMEOUT = 2

PYTHON_EXEC = 'python3'

# Database
MONGO_HOST = 'localhost'
MONGO_PORT = 27017

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0'