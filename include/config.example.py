SQLITE_DB_FILE_PATH = 'my_app.db'

LOGIN_API = 'https://app.bupt.edu.cn/uc/wap/login/check'
REPORT_PAGE = 'https://app.bupt.edu.cn/ncov/wap/default/index'
REPORT_API = 'https://app.bupt.edu.cn/ncov/wap/default/save'
API_TIMEOUT = 20 # in seconds

XISU_REPORT_PAGE = 'https://app.bupt.edu.cn/site/ncov/xisudailyup'
XISU_HISTORY_DATA = 'https://app.bupt.edu.cn/xisuncov/wap/open-report/index'
XISU_REPORT_API = 'https://app.bupt.edu.cn/xisuncov/wap/open-report/save'

OUT_SCH_LOGIN = 'https://auth.bupt.edu.cn/authserver/login'
OUT_SCH_PAGE = 'https://service.bupt.edu.cn/v2/matter/start?id=578'
OUT_SCH_API = 'https://service.bupt.edu.cn/site/apps/launch'
OUT_SCH_IS_LOGIN = 'https://service.bupt.edu.cn/site/user/get-name'

CRON_TIMEZONE = 'Asia/Shanghai'
CHECKIN_ALL_CRON_HOUR = 8
CHECKIN_ALL_CRON_MINUTE = 0
CHECKIN_ALL_CRON_RETRY_HOUR   = 0
CHECKIN_ALL_CRON_RETRY_MINUTE = 25

CHECKIN_OUTSCH_ALL_CRON_HOUR = 6
CHECKIN_OUTSCH_ALL_CRON_MINUTE = 0
CHECKIN_OUTSCH_ALL_CRON_RETRY_HOUR   = 0
CHECKIN_OUTSCH_ALL_CRON_RETRY_MINUTE = 25

XISU_CHECKIN_ALL_CRON_NOON_HOUR = 12
XISU_CHECKIN_ALL_CRON_NOON_MINUTE = 10
XISU_CHECKIN_ALL_CRON_NOON_RETRY_HOUR = 12
XISU_CHECKIN_ALL_CRON_NOON_RETRY_MINUTE = 25

XISU_CHECKIN_ALL_CRON_NIGHT_HOUR = 18
XISU_CHECKIN_ALL_CRON_NIGHT_MINUTE = 10
XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_HOUR = 18
XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_MINUTE = 25

REASONABLE_LENGTH = 24

TG_BOT_PROXY = None # {'proxy_url': 'socks5h://127.0.0.1:7891/'}
TG_BOT_TOKEN = ""   # Bot Token
TG_BOT_MASTER = 100000   # Master Telegram User ID

CHECKIN_PROXY = {} # example: {'http': 'socks5://user:pass@host:port', 'https': 'socks5://user:pass@host:port'}

BOT_DEBUG = False

HELP_MARKDOWN=f'''
自动签到时间：每日8点0分
自动晨午晚检时间：每日12点10分、18点10分
自动报备出校时间：每日6点0分
请在使用本 bot 前，确保已经正确提交过一次上报。
本 bot 的目标签到系统为：{REPORT_PAGE}
本 bot 的目标晨午晚检系统为：{XISU_REPORT_PAGE}
本 bot 的目标上报系统为: {OUT_SCH_PAGE}

/list
  列出所有签到用户

/checkin
  立即执行签到

/remove [学号, ...]
  移除用户

/add `学号` `密码` `手机号(Optional)`
  用户信息为统一身份认证 UIS 系统
  通过用户名与密码添加签到用户
  例：/add `2010211000 password123` `13011000011`
  NOTE: **没有手机号将无法进行自动报备出校**

工作原理与位置变更须知：
从网页上获取上一次成功签到的数据，处理后再次提交。
晨午晚检地理位置信息采取与原签到功能相同的数据。
因此，如果您改变了城市（如返回北京），请先使用 /pause 暂停自动签到，并 **【连续两天】** 手动签到成功后，再使用 /resume 恢复自动签到。
'''
