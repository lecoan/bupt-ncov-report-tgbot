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
    removed = 2

class TGUser(BaseModel):
    id = AutoField()
    userid = IntegerField(unique=True)
    username = CharField(null=True, index=True)
    create_time = DateTimeField(default=datetime.datetime.now, index=True)

    def get_buptusers_by_seqids(self, seqids: [int]):
        available_targets = self.get_buptusers()
        assert max(seqids) <= len(available_targets), "Seqid out of range."

        return [available_targets[i-1] for i in seqids]

    def get_buptusers(self, include_all=False):
        if include_all:
            return self.buptusers
        else:
            return self.buptusers.where(BUPTUser.status != BUPTUserStatus.removed)

class BUPTUser(BaseModel):
    id = AutoField()
    owner = ForeignKeyField(model=TGUser, backref='buptusers', lazy_load=False, index=True, on_delete="CASCADE", on_update="CASCADE")
    username = CharField(null=True)
    password = CharField(null=True)
    cookie_eaisess = CharField(null=True)
    cookie_uukey = CharField(null=True)
    latest_data = TextField(null=True)
    latest_response_data = TextField(null=True)
    latest_response_time = DateTimeField(null=True, index=True)

    status = IntegerField(index=True, default=BUPTUserStatus.normal)
    create_time = DateTimeField(default=datetime.datetime.now, index=True)
    update_time = DateTimeField(default=datetime.datetime.now, index=True)

    latest_xisu_checkin_data = TextField(null=True)
    latest_xisu_checkin_response_data = TextField(null=True)
    latest_xisu_checkin_response_time = DateTimeField(null=True, index=True)
    xisu_checkin_status = IntegerField(index=True, default=BUPTUserStatus.normal)

    # TODO 似乎有的并不需要
    cookie_vjuid = CharField(null=True)
    cookie_vjvd = CharField(null=True)
    cookie_vt = CharField(null=True)
    cookie_castgc = CharField(null=True)
    phone = CharField(null=True)

    def save(self, *args, **kwargs):
        self.update_time = datetime.datetime.now()
        return super(BUPTUser, self).save(*args, **kwargs)

    def check_xisu_checkin_status(self):
        assert self.xisu_checkin_status != BUPTUserStatus.stopped
        assert self.status != BUPTUserStatus.removed

    def check_status(self):
        assert self.status != BUPTUserStatus.stopped
        assert self.status != BUPTUserStatus.removed

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
        assert self.phone != None
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
        
        payload = build_out_sch_post_data(self, '南门', '吃饭')
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

    # name adapted from api /xisuncov/wap/open-report/index
    def xisu_ncov_checkin(self, force=False):
        if not force:
            self.check_xisu_checkin_status()
        session = requests.Session()
        session.proxies.update(CHECKIN_PROXY)
        if self.cookie_eaisess != None:
            cookies={
                'eai-sess': self.cookie_eaisess,
                'UUKey': self.cookie_uukey
            }
            requests.utils.add_dict_to_cookiejar(session.cookies, cookies)

        history_data = session.get(XISU_HISTORY_DATA, allow_redirects=False, timeout=API_TIMEOUT)
        _logger.debug(f'[xisu report page] status: {history_data.status_code}')
        if history_data.status_code == 302:
            session = self.login()
            history_data = session.get(XISU_HISTORY_DATA, allow_redirects=False, timeout=API_TIMEOUT)
        if history_data.status_code != 200:
            RuntimeError(f'Xisu Report Page returned {history_data.status_code}.')

        xisu_nconv_checkin_pending_form = history_data.json()

        report_page_resp = session.get(REPORT_PAGE, allow_redirects=False, timeout=API_TIMEOUT)
        ncov_report_page_html = report_page_resp.text
        assert 'realname' in ncov_report_page_html, f"Xisu Report 中的报告页面 {REPORT_PAGE} 返回信息不正确"

        post_data = build_xisu_ncov_checkin_post_data(ncov_report_page_html=ncov_report_page_html, xisu_nconv_checkin_pending_form=xisu_nconv_checkin_pending_form)

        self.latest_xisu_checkin_data = json.dumps(post_data)
        self.save()

        _logger.debug(f'[xisu report api] Final data: {json.dumps(post_data)}')

        xisu_report_api_resp = session.post(XISU_REPORT_API, post_data,
                                       headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
                                       timeout=API_TIMEOUT
                                       )
        assert xisu_report_api_resp.status_code == 200, "Xisu 提交 API 状态异常"
        self.latest_xisu_checkin_response_data = xisu_report_api_resp.text.strip()
        self.latest_xisu_checkin_response_time = datetime.datetime.now()
        self.save()

        if xisu_report_api_resp.json()['e'] == 0:
            return xisu_report_api_resp.text.strip()
        else:
            raise Exception(xisu_report_api_resp.text.strip())

def db_init():
    database_proxy.connect()
    database_proxy.create_tables([TGUser,BUPTUser])

