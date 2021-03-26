import datetime
import logging
import requests
import json
from peewee import *
from playhouse.migrate import *
from .config import *
from .function import *


database_proxy = DatabaseProxy()
_logger = logging.getLogger(__name__)


class BaseModel(Model):
    class Meta:
        database = database_proxy


class BUPTUserStatus:
    normal  = 0
    stopped = 1


class BUPTUser(BaseModel):
    id = AutoField()
    username = CharField(unique=True, index=True)
    password = CharField(null=True)
    cookie_eaisess = CharField(null=True)
    cookie_uukey = CharField(null=True)
    latest_data = TextField(null=True)
    latest_response_data = TextField(null=True)
    latest_response_time = DateTimeField(null=True, index=True)

    status = IntegerField(index=True, default=BUPTUserStatus.normal)
    create_time = DateTimeField(default=datetime.datetime.now, index=True)
    update_time = DateTimeField(default=datetime.datetime.now, index=True)

    cookie_vjuid = CharField(null=True)
    cookie_vjvd = CharField(null=True)
    cookie_vt = CharField(null=True)
    cookie_castgc = CharField(null=True)
    out_json = CharField(null=True)

    def save(self, *args, **kwargs):
        self.update_time = datetime.datetime.now()
        return super(BUPTUser, self).save(*args, **kwargs)

    def check_status(self):
        assert self.status != BUPTUserStatus.stopped

    def login(self):
        self.check_status()
        assert self.username != None
        _logger.info(f"[login] Trying user: {self.username}")
        session = requests.Session()
        session.proxies.update(CHECKIN_PROXY)

        login_resp = session.post(LOGIN_API, data={
            'username': self.username,
            'password': self.password,
        }, timeout=API_TIMEOUT)
        _logger.debug(login_resp.text)
        if login_resp.status_code != 200:
            raise RuntimeError('Login Server ERROR!')

        ret_data = login_resp.json()
        if ret_data['e'] == 0:
            self.cookie_eaisess = login_resp.cookies['eai-sess']
            self.cookie_uukey = login_resp.cookies['UUkey']
            self.save()
            _logger.info(f'[login] Succeed! user: {self.username}.')
            return session
        else:
            _logger.warning(f'[login] Failed! user: {self.username}, ret: {ret_data}')
            raise RuntimeWarning(f'Login failed! Server return: `{ret_data}`')
    
    def out_sch_login(self):
        self.check_status()
        assert self.username != None
        _logger.info(f"[login] Trying user: {self.username}")
        session = requests.Session()
        session.proxies.update(CHECKIN_PROXY)

        login_page = session.get(OUT_SCH_LOGIN, allow_redirects=False, timeout=API_TIMEOUT)
        lt = match_re_group1('<input type="hidden" name="lt" value="(.*)" />', login_page.text)
        login_resp = session.post(OUT_SCH_LOGIN, data={
            'username': self.username,
            'password': self.password,
            'lt': lt,
            'execution': 'e1s1',
            '_eventId': 'submit',
            'rmShown': 1,

        }, timeout=API_TIMEOUT)
        _logger.debug(login_resp.text)
        is_login_resp = session.get(OUT_SCH_IS_LOGIN, timeout=API_TIMEOUT)
        try:
            is_login_resp_json = is_login_resp.json()
            self.cookie_castgc = session.cookies['CASTGC']
            self.cookie_vjuid = session.cookies['vjuid']
            self.cookie_vjvd = session.cookies['vjvd']
            self.cookie_vt = session.cookies['vt']
            self.save()
            return session
        except json.JSONDecodeError:
            raise RuntimeWarning(f'[login] Failed! user: {self.username}')

    def out_sch_checkin(self, force=False):
        if not force:
            self.check_status()
        session = requests.Session()
        session.proxies.update(CHECKIN_PROXY)
        if self.cookie_castgc != None:
            cookies={
                'CASTGC': self.cookie_castgc,
                'UUKey': self.cookie_uukey,
                'vjuid': self.cookie_vjuid,
                'vjvd': self.cookie_vjvd,
                'vt': self.cookie_vt
            }
            requests.utils.add_dict_to_cookiejar(session.cookies, cookies)
        
        is_login_resp = session.get(OUT_SCH_IS_LOGIN, timeout=API_TIMEOUT)
        try:
            is_login_resp.json()
        except json.JSONDecodeError:
            session = self.out_sch_login()
        
        payload = build_out_sch_post_data(self)
        upload_resp = session.post(OUT_SCH_API, data={'data': payload}, timeout=API_TIMEOUT)
        if upload_resp.json()['e'] == 0:
            return upload_resp.text.strip()
        else:
            raise Exception(upload_resp.text.strip())


    def ncov_checkin(self, force=False):
        if not force:
            self.check_status()
        session = requests.Session()
        session.proxies.update(CHECKIN_PROXY)
        if self.cookie_eaisess != None:
            cookies={
                'eai-sess': self.cookie_eaisess,
                'UUKey': self.cookie_uukey
            }
            requests.utils.add_dict_to_cookiejar(session.cookies, cookies)

        report_page_resp = session.get(REPORT_PAGE, allow_redirects=False, timeout=API_TIMEOUT)
        _logger.debug(f'[report page] status: {report_page_resp.status_code}')
        if report_page_resp.status_code == 302:
            session = self.login()
            report_page_resp = session.get(REPORT_PAGE, allow_redirects=False, timeout=API_TIMEOUT)
        if report_page_resp.status_code != 200:
            RuntimeError(f'Report Page returned {report_page_resp.status_code}.')

        page_html = report_page_resp.text
        assert 'realname' in page_html, "报告页面返回信息不正确"

        # 从上报页面中提取 POST 的参数
        post_data = extract_post_data(page_html)
        self.latest_data = json.dumps(post_data)
        self.save()
        _logger.debug(f'[report api] Final data: {json.dumps(post_data)}')

        # 最终 POST
        report_api_resp = session.post(REPORT_API, post_data,
            headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
            timeout=API_TIMEOUT
        )
        assert report_api_resp.status_code == 200, "提交 API 状态异常"
        self.latest_response_data = report_api_resp.text.strip()
        self.latest_response_time = datetime.datetime.now()
        self.save()

        if report_api_resp.json()['e'] == 0:
            return report_api_resp.text.strip()
        else:
            raise Exception(report_api_resp.text.strip())


def db_init():
    database_proxy.connect()
    database_proxy.create_tables([BUPTUser])

