#!/usr/bin/env python3

import os
from pytbox.database.mongo import Mongo
from pytbox.utils.load_config import load_config_by_file
from pytbox.database.victoriametrics import VictoriaMetrics
from pytbox.feishu.client import Client as FeishuClient
from pytbox.dida365 import Dida365
from pytbox.alert.alert_handler import AlertHandler
from pytbox.log.logger import AppLogger
from pytbox.network.meraki import Meraki
from pytbox.utils.env import get_env_by_os_environment
from pytbox.vmware import VMwareClient
from pytbox.pyjira import PyJira
from pytbox.mail.client import MailClient
from pytbox.mail.alimail import AliMail
from pytbox.alicloud.sls import AliCloudSls
from pytbox.utils.cronjob import cronjob_counter
from pytbox.notion import Notion
from pytbox.mingdao import Mingdao


config = load_config_by_file(path='/workspaces/pytbox/tests/alert/config_dev.toml', oc_vault_id=os.environ.get('oc_vault_id'))


def get_mongo(collection):
    return Mongo(
        host=config['mongo']['host'],
        port=config['mongo']['port'],
        username=config['mongo']['username'],
        password=config['mongo']['password'],
        auto_source=config['mongo']['auto_source'],
        db_name=config['mongo']['db_name'],
        collection=collection
    )

vm = VictoriaMetrics(url=config['victoriametrics']['url'])

feishu = FeishuClient(
    app_id=config['feishu']['app_id'],
    app_secret=config['feishu']['app_secret']
)
dida = Dida365(
    cookie=config['dida']['cookie'],
    access_token=config['dida']['access_token']
)


alert_handler = AlertHandler(config=config, mongo_client=get_mongo('alert_test'), feishu_client=feishu, dida_client=dida)

def get_logger(app):
    return AppLogger(
        app_name=app, 
        enable_victorialog=True, 
        victorialog_url=config['victorialog']['url'],
        feishu=feishu,
        dida=dida,
        mongo=get_mongo('alert_program')
    )

def get_logger_sls(app):
    return AppLogger(
        app_name=app, 
        enable_sls=True,
        feishu=feishu,
        dida=dida,
        mongo=get_mongo('alert_program'),
        sls_access_key_id=config['alicloud']['account1']['access_key_id'],
        sls_access_key_secret=config['alicloud']['account1']['access_key_secret'],
        sls_project=config['alicloud']['account1']['project'],
        sls_logstore=config['alicloud']['account1']['logstore']
    )

# ad_dev = ADClient(
#     server=config['ad']['dev']['AD_SERVER'],
#     base_dn=config['ad']['dev']['BASE_DN'],
#     username=config['ad']['dev']['AD_USERNAME'],
#     password=config['ad']['dev']['AD_PASSWORD']
# )

# ad_prod = ADClient(
#     server=config['ad']['prod']['AD_SERVER'],
#     base_dn=config['ad']['prod']['BASE_DN'],
#     username=config['ad']['prod']['AD_USERNAME'],
#     password=config['ad']['prod']['AD_PASSWORD']
# )

env = get_env_by_os_environment(check_key='ENV')
meraki = Meraki(api_key=config['meraki']['api_key'], organization_id=config['meraki']['organization_id'])

# vmware_test = VMwareClient(
#     host=config['vmware']['test']['host'],
#     username=config['vmware']['test']['username'],
#     password=config['vmware']['test']['password'],
#     version=config['vmware']['test']['version'],
#     proxies=config['vmware']['test']['proxies']
# )

pyjira = PyJira(
    base_url=config['jira']['base_url'],
    username=config['jira']['username'],
    token=config['jira']['token']
)

# mail_163 = MailClient(mail_address=config['mail']['163']['mail_address'], password=config['mail']['163']['password'])
# mail_qq = MailClient(mail_address=config['mail']['qq']['mail_address'], password=config['mail']['qq']['password'])
# ali_mail = AliMail(mail_address=config['mail']['aliyun']['mail_address'], client_id=config['mail']['aliyun']['client_id'], client_secret=config['mail']['aliyun']['client_secret'])

sls = AliCloudSls(
    access_key_id=config['alicloud']['account1']['access_key_id'],
    access_key_secret=config['alicloud']['account1']['access_key_secret'],
    project=config['alicloud']['account1']['project'],
    logstore=config['alicloud']['account1']['logstore']
)

def get_cronjob_counter(app_type='', app='', comment=None, schedule_interval=None, schedule_cron=None):
    return cronjob_counter(vm=vm, log=get_logger('cronjob_counter'), app_type=app_type, app=app, comment=comment, schedule_interval=schedule_interval, schedule_cron=schedule_cron)


notion = Notion(token=config['notion']['api_secrets'], proxy=config['notion']['proxy'])
mingdao = Mingdao(app_key=config['mingdao']['app_key'], sign=config['mingdao']['sign'])