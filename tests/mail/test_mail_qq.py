#!/usr/bin/env python3


from pytbox.base import mail_qq




# for i in r:
#     print(i)
#    1382972721

# mail_163.mark_as_read(uid="1382972720")
# mail_163.move(uid='1382972722', destination_folder='bill')
# r = mail_163.send_mail(receiver=['houmingming@tyun.cn'], subject='test', contents='test')
# print(r)

# def test_get_mail_list():
#     r = mail_qq.get_mail_list()
#     for i in r:
#         print(i.uid)
#         assert isinstance(i.subject, str)

# def test_move_mail():
#     r = mail_qq.move(uid="9224", destination_folder="mlmw")
#     print(r)


# r = mail_qq.get_folder_list()
# print(r)

r = mail_qq.get_mail_list()
for i in r:
    print(i.uid)
    assert isinstance(i.subject, str)

r = mail_qq.move(uid="9225", destination_folder="其他文件夹/xx")
print(r)