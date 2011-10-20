USER_STATUS = [u'Available', u'Chatty', u'Away', u'Busy']
SUCCESS = 0
AUTH_FAIL = -1
TIMEOUT = 1
ERROR = SERVER_FAULT = 2
NOT_FOUND = 3

from datetime import datetime
from pytz import utc
NULL_DATE = datetime.min.replace(tzinfo=utc).isoformat()

import re
# 2011-09-30T15:49:35.417693+00:00
VALID_DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d{6})?[+-]\d{2}:\d{2}$')
