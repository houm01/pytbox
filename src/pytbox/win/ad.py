#!/usr/bin/env python3


from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_REPLACE, SUBTREE, MODIFY_ADD, MODIFY_DELETE


class ADClient:
    '''
    _summary_
    '''
    def __init__(self, server, base_dn, username, password):
        self.server = Server(server, get_info=ALL)
        self.conn = Connection(self.server, user=username, password=password, auto_bind=True)
        self.base_dn = base_dn

    def list_user(self):
        '''
        查询所有用户

        Yields:
            dict: 返回的是生成器, 字典类型
        '''
        # 搜索过滤条件
        secarch_filter = '(objectCategory=person)'  # 过滤所有用户
        # SEARCH_ATTRIBUTES = ['cn', 'sAMAccountName', 'mail', 'userPrincipalName']  # 需要的用户属性
        search_attributes = ["*"]  # 需要的用户属性
        # 搜索用户
        if self.conn.search(search_base=self.base_dn, search_filter=secarch_filter, search_scope=SUBTREE, attributes=search_attributes):
            for entry in self.conn.entries:
                yield {k: v[0] if isinstance(v, list) else v for k, v in entry.entry_attributes_as_dict.items()}