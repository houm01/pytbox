#!/usr/bin/env python3


from pytbox.base import mail_163


r = mail_163.get_mail_list()

# for i in r:
#     print(i)
#    1382972721

# mail_163.mark_as_read(uid="1382972720")
# mail_163.move(uid='1382972722', destination_folder='bill')
# r = mail_163.send_mail(receiver=['houmingming@tyun.cn'], subject='test', contents='test')
# print(r)


r = mail_163.get_folder_list()
print(r)