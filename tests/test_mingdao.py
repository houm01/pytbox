#!/usr/bin/env python3

from pytbox.base import mingdao


def test_get_app_info():
    r = mingdao.get_app_info()
    print(r)

def test_get_work_sheet_info():
    r = mingdao.get_work_sheet_info(table_name="首页", worksheet_name="工单中心")
    print(r)

def test_get_project_info():
    r = mingdao.get_project_info(keywords="")
    print(r)

def test_get_work_sheet_id_by_name():
    r = mingdao.get_work_sheet_id_by_name(table_name="首页", worksheet_name="项目信息")
    print(r)

def test_get_control_id():
    r = mingdao.get_control_id(table_name="首页", worksheet_name="工单中心", control_name="完成日期")
    print(r)

def test_get_work_record():
    r = mingdao.get_work_record(
        worksheet_id="64a77d4277649ebe61a9cb45",
        project_control_id="64a822be5760cf37a93d07ff",
        project_value="4b97c271-4997-4230-90be-28d5285f609b",
        complete_date_control_id="64a7e18c77649ebe61aad968",
        complete_date="上个月"
    )
    print(r)
    
if __name__ == '__main__':
    test_get_work_record()
