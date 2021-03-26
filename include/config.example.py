SQLITE_DB_FILE_PATH = 'my_app.db'

LOGIN_API = 'https://app.bupt.edu.cn/uc/wap/login/check'
REPORT_PAGE = 'https://app.bupt.edu.cn/ncov/wap/default/index'
REPORT_API = 'https://app.bupt.edu.cn/ncov/wap/default/save'
API_TIMEOUT = 20 # in seconds

OUT_SCH_LOGIN = 'https://auth.bupt.edu.cn/authserver/login'
OUT_SCH_PAGE = 'https://service.bupt.edu.cn/v2/matter/start?id=578'
OUT_SCH_API = 'https://service.bupt.edu.cn/site/apps/launch'
OUT_SCH_IS_LOGIN = 'https://service.bupt.edu.cn/site/user/get-name'

CRON_TIMEZONE = 'Asia/Shanghai'
CHECKIN_ALL_CRON_HOUR = 8
CHECKIN_ALL_CRON_MINUTE = 0
CHECKIN_ALL_CRON_RETRY_HOUR   = 0
CHECKIN_ALL_CRON_RETRY_MINUTE = 25

CHECKIN_OUT_ALL_CRON_HOUR = 6
CHECKIN_OUT_ALL_CRON_MINUTE = 0
CHECKIN_OUT_ALL_CRON_RETRY_HOUR   = 0
CHECKIN_OUT_ALL_CRON_RETRY_MINUTE = 25

REASONABLE_LENGTH = 24

TG_BOT_PROXY = None # {'proxy_url': 'socks5h://127.0.0.1:7891/'}
TG_BOT_TOKEN = ""   # Bot Token
TG_BOT_MASTER = 100000   # Master Telegram User ID

CHECKIN_PROXY = {} # example: {'http': 'socks5://user:pass@host:port', 'https': 'socks5://user:pass@host:port'}

BOT_DEBUG = False
