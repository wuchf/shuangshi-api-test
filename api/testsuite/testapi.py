# coding=utf-8
import unittest
import requests


class TestAPI(unittest.TestCase):
    def testlogin(self):
        url = 'http://rti.speiyou.com/rti-rest/login/v1/login'
        data = {'username': '大衣',
                'password': '123456a',
                'tchType': '1',
                'areaCode': '020',
                'areaName': '广州',
                'client': '40'}
        r = requests.post(url=url, data=data)
        text = r.content.decode()
        assert (text.find('result') != -1)
