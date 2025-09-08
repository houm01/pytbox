#!/usr/bin/env python3

from pytbox.base import ali_mail    

# r = ali_mail.get_mail_folders()
# print(r)

# r = ali_mail.get_mail_list()
# for i in r:
#     print(i)
#     s

r = ali_mail.move(uid="DzzzzzzMXHX", destination_folder="lulu_forward")
print(r)