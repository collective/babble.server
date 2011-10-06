USER_STATUS = [u'Available', u'Chatty', u'Away', u'Busy']
SUCCESS = 0
AUTH_FAIL = -1
TIMEOUT = 1
SERVER_FAULT = 2

from datetime import datetime
NULL_DATE = datetime.min.isoformat()

import re
VALID_DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d{6}[+-]\d{2}:\d{2})?$')
