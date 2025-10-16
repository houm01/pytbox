#!/usr/bin/env python3

import sys
import os
sys.path.append('/workspaces/pytbox/src')

from pytbox.base import pyjira

def test_jira_connection():
    """测试 JIRA 连接和权限"""
    print("=== JIRA 连接测试 ===")
    
    # 测试 1: 获取项目信息
    print("\n1. 测试获取项目信息...")
    try:
        project_result = pyjira.get_project('CNDS')
        print(f"项目信息获取结果: {project_result.code}")
        print(f"消息: {project_result.msg}")
        if project_result.data:
            print(f"项目名称: {project_result.data.get('name', 'N/A')}")
            print(f"项目键: {project_result.data.get('key', 'N/A')}")
    except Exception as e:
        print(f"获取项目信息失败: {e}")
    
    # 测试 2: 搜索问题
    print("\n2. 测试搜索问题...")
    try:
        search_result = pyjira.issue_search('project = CNDS', max_results=5)
        print(f"搜索结果: {search_result.code}")
        print(f"消息: {search_result.msg}")
        if search_result.data and 'issues' in search_result.data:
            print(f"找到 {len(search_result.data['issues'])} 个问题")
            for issue in search_result.data['issues'][:3]:  # 只显示前3个
                print(f"  - {issue['key']}: {issue['fields']['summary']}")
    except Exception as e:
        print(f"搜索问题失败: {e}")
    
    # 测试 3: 获取特定问题
    print("\n3. 测试获取特定问题...")
    test_issues = ['CNDS-267', 'CNDS-1', 'CNDS-2']  # 测试几个可能的问题
    
    for issue_key in test_issues:
        print(f"\n尝试获取问题: {issue_key}")
        try:
            issue_result = pyjira.issue_get(issue_key)
            print(f"获取结果: {issue_result.code}")
            print(f"消息: {issue_result.msg}")
            if issue_result.data:
                print(f"问题摘要: {issue_result.data.get('summary', 'N/A')}")
                print(f"问题状态: {issue_result.data.get('status', {}).get('name', 'N/A')}")
        except Exception as e:
            print(f"获取问题 {issue_key} 失败: {e}")

if __name__ == "__main__":
    test_jira_connection()
