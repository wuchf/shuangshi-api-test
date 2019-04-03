# coding=utf-8
import re
import socket
from tal import logconfig

logger = logconfig.Log('api')


# 判断是否为字典形式
def isdict(s):
    if s == '':
        return True
    try:
        s = s.replace('\n', '')
        s = s.replace(' ', '')
        if isinstance(eval(s), dict):
            return True
        else:
            return False
    except:
        return False


# 参数化替换
def replace(s, d):
    '''
    参数化替换
    :param s: 需要替换的字符串
    :param d: 字典类型，被替换的信息
    :return:替换后的新串
    '''
    names = re.findall(re.compile(r'{{.*?}}'), str(s))
    for n in names:
        # 通过替换变量后面指定序号来替换对应的值,可以为负数
        num = re.findall(r'-?[0-9]+$', n[2:-2])
        num = ''.join(num)
        alph = re.findall(r'^[a-zA-Z]+', n[2:-2])
        alph = ''.join(alph)
        try:
            if num:
                # 当在用例中输入的num大于列表长度，返回第一个元素
                s = s.replace(n, d[alph][0]) if abs(int(num)) > len(d[alph]) - 1 else s.replace(n, d[alph][int(num)])
            else:
                # 当替换的信息为列表，使用第一个元素替换
                s = s.replace(n, d[n[2:-2]][0]) if isinstance(d[n[2:-2]], list) else s.replace(n, d[n[2:-2]])
        except Exception as e:
            pass
    return s


def check(type, value, tmp=None):
    if type == 'text':
        if len(value) == 0:
            return '接口名称不能为空'
    if type == 'url':
        if len(value) == 0:
            return '接口url不能为空'
        if not value.startswith(('http://', 'https://', 'ws://')):
            return '接口url输入错误'
    if type == 'type':
        if value.lower() == 'ws':
            if tmp[0:2] != 'ws':
                return '接口url或接口类型错误'
        else:
            if tmp[0:4] != 'http':
                return '接口url或接口类型错误'
    if type == 'header':
        if len(value) != 0:
            try:
                if not isinstance(eval(value), dict):
                    return '接口头必须为字典类型'
            except:
                return '接口头必须为字典类型'


def getip():
    myname = socket.getfqdn(socket.gethostname())
    myaddr = socket.gethostbyname_ex(myname)[2]
    for i in myaddr:
        if i.startswith('10.'):
            return i
    return myaddr[0]


def reversdic(dic):
    from collections import defaultdict
    d = defaultdict(list)
    for k, v in dic.items():
        d[v].append(k)
    return d

def viewlog(filename,t_begin,t_end):
    with open(filename ,'r') as f:
        for line in f:
            pass
