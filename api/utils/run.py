# coding=utf-8
import re
import requests
from requests.adapters import HTTPAdapter
import websocket
import queue
import threading
import time
from urllib import parse
from collections import defaultdict
import json

from . import common
from .. import models
from tal import logconfig
logger=logconfig.Log('api')
import urllib3

#在requests的时候设置参数verify为false，不校验证书，这里将警告信息不显示
urllib3.disable_warnings()

HTTP_RETRY_TIME=5
WS_TIME_OUT=3
WS_RECV_TIME=50
requests.adapters.DEFAULT_RETRIES = HTTP_RETRY_TIME
rr = requests.Session()

class RUN:
    def __init__(self, id, rtype=None, seqid=0,**kwargs):
        self.seqid = seqid
        self.id = id
        self.rtype = rtype
        self.q = queue.Queue()
        self.common=kwargs['common']  if 'common' in kwargs.keys()else None
        self.procomm = kwargs['procomm'] if 'procomm' in kwargs.keys()else None
    def runtest(self, relist):
        if self.rtype == 'case':
            result = self._param(isall=True)
            return self._case(result, relist)
        elif self.rtype == 'param':
            result = self._param()
            if not isinstance(result, dict):
                return result
            for k, v in result.items():
                if k=='errormsg':
                    relist.append({'name':v, 'result': result['res_info']})
                    # relist.append({k:v,'res_info':result['res_info']})
                elif isinstance(v,websocket._core.WebSocket):
                    pass
                else:
                    if k!='res_info':
                        relist.append({'name': k, 'result': v})
        elif self.rtype=='postcon':
            result = self._param(isall=True)
            reslist=self._postcon(result)
            for i in reslist:
                relist.append(i)
        else:
            result = self._param(isall=True)
            logger.info('参数化获取的参数值为:%s'%result)
            self._case(result, relist, isall=True)
            self._postcon(result,isall=True)

    def _case(self, result, relist, isall=False):
        case_api = models.ApiList.objects.get(id=self.id)
        if not isall:
            cases = models.ApiCase.objects.filter(cname=self.id, seqid=self.seqid)
        else:
            cases = models.ApiCase.objects.filter(cname=self.id)
        if len(cases)==0:
            return
        for case in cases:
            #添加用例名，用例序号，预期结果
            redict = {'name': case_api.name, 'seqid': case.seqid,'expect':case.response,'response':'','pname':"","re":""}
            curl=common.replace(case_api.url,result)
            header = common.replace(case_api.header, result)
            params = common.replace(case.params, result)
            logger.debug('用例【%s】替换完参数之后的params值为：%s' % (case_api.name,params))
            data = case.body.replace('\n', '')
            data = data.replace(' ', '')
            data = common.replace(data, result)
            logger.debug('用例【%s】替换完参数之后的data值为：%s' % (case_api.name, data))
            try:
                #如果参数是dict类型并且有sleep字段，则进行睡眠指定的时间
                p=eval(params)
                if isinstance(p, dict) and 'sleep' in p.keys():
                    time.sleep(p['sleep'])
                    logger.debug('sleep%s秒钟'%p['sleep'])
            except:
                if case_api.type=='WS':
                    tmp=re.search("client=(.*?)&|client=(.*?)$",params)
                    if tmp:
                        client=tmp.group(1)
                        logger.info('用例获取到的client为：%s'%client)
                    else:
                        #ws没有参数，获取不到client。默认为0
                        client='0'
                    #client字段已经在result中，直接使用，没有，进行连接
                    if (client in result.keys()):
                        ws = result[client]
                    else:
                        ws= self._ws_connect(client,url=curl,params=params)
                        if ws:
                            result[client] = ws
                    #直接发送ws信令
                    self._ws_send(ws, client, data)
                    #验证类型为content，对response信息进行验证
                    if case.restype == 'content':
                        logger.info("进行内容校验")
                        _result=[]
                        response = case.response.split('\n')
                        logger.info('验证信息为：%s'%response)
                        for i in response:
                            #对于ws连接，如果response中没有指定验证具体哪一个端返回的信息，默认验证当前连接的信息
                            if "|" not in i:
                                client_name = client
                                client_res = i
                            else:
                                client_con = i.split('|')
                                client_name = client_con[0]
                                client_res = client_con[1]
                            if client_name in result.keys():
                                t2 = threading.Thread(target=self._ws_recv,
                                                      args=(result[client_name],client_name,client_res))
                                t2.start()
                                t2.join()
                                while not self.q.empty():
                                    _result.append(self.q.get())
                            else:
                                _result.append('fail;客户端%s还没有连接'%client_name)
                        logger.info ("recv接收结果为："%_result)
                        redict['result']='fail' if 'fail' in [i.split(';')[0] for i in _result] else 'pass'
                        redict['response'] = [x.split(';')[1] for x in _result]
                    else:
                        # 验证类型为status，ws没有返回的状态，验证类型为None不验证直接通过
                        self._ws_recv(ws, client)
                        logger.info ('不进行校验直接通过')
                        redict['result'] = 'pass'
                    relist.append(redict)
                else:
                    res=self._http_request(curl,case_api.type,header,params,data)
                    if not isinstance(res, requests.models.Response):
                        redict['errormsg']='%s'%res
                        redict['result'] = 'fail'
                        redict['response'] = '%s' % res
                    if case.restype == 'content':
                        logger.info("通过内容进行校验")
                        logger.info(res.text)
                        _result = []
                        #对于content类型的验证，判断是否有多个结果需要验证
                        response = case.response.split('\n')
                        logger.info('验证信息为：%s' % response)
                        for i in response:
                            #如果“|”在验证信息中不存在，验证http响应
                            if '|'not in i:
                                if re.search(i, res.content.decode()):
                                    _result.append('pass;%s'%res.content.decode())
                                else:
                                    _result.append('fail;%s' % res.content.decode())
                            else:
                                #30|CLIENT_ANSWER
                                client_con = i.split('|')
                                client_name = client_con[0]
                                client_res = client_con[1]
                                if client_name in result.keys():
                                    self._ws_recv(result[client_name], client_name, client_res)
                                    if not self.q.empty():
                                        _tmp=self.q.get()
                                        logger.info("ws验证获取到的结果为：%s"%_tmp)
                                        if _tmp.split(';')[0]=='pass':
                                            #todo 对于ws的获取，先进行验证，验证通过，相同client，相同command的指令获取信息
                                            pass
                                        _result.append(_tmp)
                                else:
                                    _result.append('fail;客户端%s还没有连接' % client_name)
                        logger.debug('content验证结果%s'%_result)
                        redict['result'] = 'fail' if 'fail' in [i.split(';')[0] for i in _result] else 'pass'
                        redict['response'] = [x.split(';')[1] for x in _result]
                    elif case.restype == 'status':
                        if res.status_code == int(case.response):
                            redict['result'] = 'pass'
                        else:
                            redict['result'] = 'fail'
                            redict['response'] = res.text
                    else:
                        # 无需验证，直接pass
                        redict['result'] = 'pass'
                    #用例执行完，验证完之后进行参数获取
                    if case.re !="":
                        com = case.re.split('\n')
                        names = case.name.split(';')
                        # 获取参数信息
                        self.getparam(res.text,com,names,result)
                        d = defaultdict(list)
                        pname=""
                        pre=""
                        for i in names:
                            pname=pname+i+"<hr/>"
                            if isinstance(result.get(i),list):
                                str=" ".join(result.get(i))
                            else:
                                str=result.get(i)
                            pre = pre + str + "<hr/>"
                            # d['pname'].append(i)
                            # d['re'].append(result.get(i))
                        # redict['pname']=d.get('pname')
                        # redict['re'] = d.get('re')
                        redict['pname']=pname
                        redict['re'] = pre
                    relist.append(redict)
                #一条用例运行完之后需要运行tm为n的后置条件
                self._postcon(result, isall=True,tm='n')
    #预置条件处理
    def _param(self, isall=False):
        result = {}
        if not isall:
            param = models.ApiParam.objects.filter(cname=self.id,seqid__lte=self.seqid)
        else:
            param = models.ApiParam.objects.filter(cname=self.id)
        for p in param:
            #对参数化中需要替换的参数进行替换
            purl = common.replace(p.url,result)
            pheader = common.replace(p.header, result)
            pparams = common.replace(p.params, result)
            pbody = common.replace(p.body,result)
            logger.debug ('参数化中替换完参数之后的请求params:%s'%pparams)
            logger.debug('参数化中替换完参数之后的请求body:%s' % pbody)
            try:
                #主要处理每一次交易的冷冻时间
                #如果参数是dict类型并且有sleep字段，则进行睡眠指定的时间
                p=eval(pparams)
                if isinstance(p, dict) and 'sleep' in p.keys():
                    time.sleep(p['sleep'])
                    logger.info('sleep%s秒钟'%p['sleep'])
            except:
                if p.type == 'WS':
                    try:
                        com = p.re.split('\n')
                        names = p.name.split(';')
                    except Exception as e:
                        result['errormsg'] =e
                        logger.error(e)
                        continue
                    tmp=re.search("client=(.*?)&|client=(.*?)$", pparams)
                    if tmp:
                        client=tmp.group(1)
                    else:
                        client = 0
                        #如果参数中没有client，但是参数名称中指定了client名称，即参数名称比获取参数值多1，指定第一个names为client名称
                        #排除com 会出现[""]空的列表，他的长度也是1
                        if com[0]=="":
                            if names[0]!="":
                                client = names[0]
                        else:
                            if len(com) == len(names)-1:
                                client=names[0]
                    logger.info('client值为：%s' % client)
                    #查看client是否已连接
                    if (client in result.keys()):
                        ws = result[client]
                    else:
                        ws = self._ws_connect(client, url=purl, params=pparams)
                        if ws:
                            result[client] = ws
                        else:
                            result[client]='客户端%s连接ws的失败'%client
                            continue
                    if pbody!="":
                        self._ws_send(ws,client,pbody)
                        if len(com[0])>0:
                            if len(com) == len(names)-1:
                                client = names[0]
                                names = names[1:]
                            elif len(com) != len(names):
                                result['errormsg']='参数个数与获取正则个数不匹配，请修改！'
                                logger.error('参数个数与获取正则个数不匹配，请修改！')
                                #结束本次循环，执行下一次
                                continue
                            #获取ws的信令返回后获取指定的参数信息
                            self.getwsparam(com,names,client,result)
                else:
                    r=self._http_request(purl,p.type,pheader,pparams,pbody)
                    if not isinstance(r,requests.models.Response):
                        result['errormsg']=r
                        continue
                    logger.debug("参数化返回结果为%s"%r.text)
                    if p.re is not None:
                        com = p.re.split('\n')
                        names = p.name.split(';')
                        #获取参数信息
                        self.getparam(r.text,com,names,result)
                    else:
                        result[purl]=r.text
        return result
    def _postcon(self,result,isall=False,tm='1'):
        reslist=[]
        if not isall:
            postcons = models.ApiPostcon.objects.filter(cname=self.id, seqid=self.seqid)
        else:
            postcons = models.ApiPostcon.objects.filter(cname=self.id,time=tm)
        for p in postcons:
            res = {}
            pcurl=common.replace(p.url,result)
            header = common.replace(p.header, result)
            param = common.replace(p.params, result)
            body = common.replace(p.body, result)
            try:
                #主要处理每一次交易的冷冻时间
                #如果参数是dict类型并且有sleep字段，则进行睡眠指定的时间
                p=eval(param)
                if isinstance(p, dict) and 'sleep' in p.keys():
                    time.sleep(p['sleep'])
                    logger.info('sleep%s秒钟'%p['sleep'])
            except:
                if p.type=='WS':
                    client=0
                    tmp = re.search("client=(.*?)&|client=(.*?)$", param)
                    if tmp:
                        client=tmp.group(1)
                    logger.info('后置条件获取到的client为：%s' % client)
                    if body == "":
                        # 当body都为空，并且type为ws，默认为关闭ws请求
                        if (client in result.keys()):
                            ws = result[client]
                            try:
                                ws.close()
                                res['res'] = '端%s ws连接已关闭' % client
                            except Exception as e:
                                logger.error('端%s ws连接关闭失败，失败原因为：%s'%(client,e))
                                res['res'] = '端%s ws连接关闭失败，失败原因为：%s'%(client,e)
                        else:
                            logger.info('端%s ws还没有连接' % client)
                            res['res'] = '端%s ws连没有连接' % client
                    else:
                        if (client in result.keys()):
                            ws = result[client]
                        else:
                            ws = self._ws_connect(client, url=pcurl, params=param)
                            result[client] = ws
                        ws.send(payload=body)
                        try:
                            r = ws.recv()
                            res['res'] = r
                            logger.info('后置条件ws接受信息为： %s' % r)
                        except Exception as e:
                            logger.error(e)
                            res['res'] = str(e)
                else:
                    r=self._http_request(pcurl,p.type,header,param,body)
                    if not isinstance(r, requests.models.Response):
                        res['errormsg']=r
                    else:
                        res['res'] = r.text
            reslist.append(res)
        logger.debug ('后置条件运行结果为:%s'%reslist)
        return reslist
    def _ws_connect(self,client,timeout=WS_TIME_OUT,**kwargs):
        '''
        ws连接
        '''
        # logger.info('connect ws')
        logger.info('客户端%s连接ws' % (client))
        if 'params' in kwargs.keys():
            url = kwargs['url'] + "?" + kwargs['params']
        else:
            url=kwargs['url']
        if self.procomm is not None:
            url = common.replace(url, self.procomm)
        if self.common is not None:
            url = common.replace(url, self.common)
        try:
            logger.info('客户端%s连接ws的url为%s' % (client, url))
            ws = websocket.create_connection(url.replace(' ',''),timeout)
            logger.info('客户端%s连接ws的结果为%s' % ( client,ws))
            return ws
        except Exception as e:
            logger.error('客户端%s连接ws的错误信息为%s'%(client,e))
            return None


    def _ws_send(self,ws, client,payload):
        '''
        发送ws请求
        :param ws: 已连接的ws对象
        :param payload: 发送的信息
        :return:
        '''
        if self.procomm is not None:
            payload = common.replace(payload, self.procomm)
        if self.common is not None:
            payload = common.replace(payload, self.common)
        logger.info('客户端%s ws发送的信息为:%s'%(client,payload))
        try:
            ws.send(payload=payload)
        except Exception as e:
            logger.error(e)

    def _ws_recv(self,ws, client, response=None):
        '''
        接受服务器返回的信息
        :param ws: ws连接对象
        :param client: 客户端类型
        :param response: 返回结果校验信息
        '''
        try:
            flag=True
            tm=WS_RECV_TIME
            while flag:
                res=ws.recv()
                logger.info('客户端%s 接收到的信息为:%s' % (client, res))
                if response  is not None:
                    if re.search(response, res):
                        self.q.put( 'pass;%s'%res)
                        flag= False
                    #限制获取次数
                    else:
                        flag=True
                        if tm <=0:
                            flag=False
                            self.q.put( 'fail;%s'%res)
                    tm-=1
                else:
                    self.q.put('pass;%s' % res)
        except Exception as e:
            logger.error(e)
            self.q.put( 'fail;%s'%str(e))
            return False

    def _http_request(self,url,type,header,param,body):
        #requests.adapters.DEFAULT_RETRIES = HTTP_RETRY_TIME
        #rr = requests.Session()
        rr.keep_alive = False
        if self.procomm is not None:
            url = common.replace(url, self.procomm)
            header = common.replace(header, self.procomm)
            param = common.replace(param, self.procomm)
            body = common.replace(body, self.procomm)
        if self.common is not None:
            url = common.replace(url, self.common)
            header = common.replace(header, self.common)
            param = common.replace(param, self.common)
            body = common.replace(body, self.common)
        headers={}
        if header:
            logger.debug('指定的header为%s'%header)
            headers=eval(header)
        #如果没有指定Content-type，根据body来添加
        if 'content-type' not in [h.lower() for h in headers.keys()]:
            try:
                if isinstance(eval(body), dict):
                    headers['Content-type'] = 'application/json'
            except:
                headers ['Content-type']= 'application/x-www-form-urlencoded'
        logger.info('http请求的url为：%s' % url.replace(' ',''))
        logger.info('http请求的type为：%s' % type)
        logger.info('http请求的header为：%s' % headers)
        logger.info('http请求的header为：%s' % parse.quote(param.replace(' ',''),':/+.&=?%",{}[]@-_'))
        logger.info('http请求的header为：%s' % parse.quote(body.replace(' ',''),':/+.&=?%",{}[]@()%;-_'))
        r=""
        try:
            #parse.quote用进行转码处理，其中:/+.&=?%",{}[]@这些字符不进行转码保留
            #verify  对于https请求，需要校验证书的设置不校验，解决报错信息(Caused by SSLError(SSLError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:777)'),))
            if type == 'GET':
                r = rr.get(url=url.replace(' ',''), headers=headers, params=parse.quote(param.replace(' ',''),':/+.&=?%",{}[]@-_'),verify=False)
            if type == 'POST':
                r = rr.post(url=url.replace(' ',''), headers=headers, params=parse.quote(param.replace(' ',''),':/+.&=?%",{}[]@-_'), data=parse.quote(body.replace(' ',''),':/+.&=?%",{}[]@()%;-_'),verify=False)
            logger.info('http请求返回结果为%s'%r.content)
        except Exception as e:
            logger.error(e)
            return e
        return r

    #获取http返回参数
    def getparam(self,r,com,names,result):
        if len(com[0]) != 0:
            if len(com) != len(names):
                result['errormsg'] = '参数个数与获取正则个数不匹配，请修改！'
                result['res_info'] = r
                logger.error('参数个数与获取正则个数不匹配，请修改！')
                return
            for i in range(0, len(names)):
                # 对中括号进行转义
                com[i] = com[i].replace('[', '\[').replace(']', '\]')
                reg = re.compile(com[i])
                tmp = reg.findall(r)
                logger.info('查找%s信息为:%s' % (com[i], tmp))
                if tmp:
                    if len(tmp) == 1:
                        result[names[i]] = tmp[0]
                    else:
                        result[names[i]] = tmp
                else:
                    result['res_info'] = r
                    result['errormsg'] = '%s未找到对应参数值' % com[i]
                    logger.error('%s未找到对应参数值' % com[i])

    #获取ws的参数
    def getwsparam(self,com,names,client,result):
        _ws = {}
        _com = {}
        _reg = {}
        for i in range(len(com)):
            # 格式为10;REQUEST_NAVIGATION_DATA|"cwid":"(.*?)"
            # 指定收取的端，收取的指令command，获取的信息正则
            try:
                if "|" not in com[i]:
                    result['res_info'] = "未指定具体的command"
                    logger.error('获取websocket返回的信令，请指定信令的command')
                    result['errormsg'] = '获取websocket返回的信令，请指定信令的command'
                    break
                else:
                    #没准会有多个分隔符，直接使用re的split进行分割
                    tmp=re.split("[;|]",com[i])
                    if len(tmp)==3:
                        _ws[i]=tmp[0]
                        _com[i]=tmp[1]
                        _reg[i]=tmp[2]
                    else:
                        _ws[i] = client
                        _com[i] = tmp[0]
                        _reg[i] = tmp[1]
            except Exception as e:
                logger.error("出现错误了，错误信息为：%s"%e)
                result['res_info'] = "分割获取参数出错"
                result['errormsg'] = "出现错误了，错误信息为：%s"%e
        wss = common.reversdic(_ws)
        command = common.reversdic(_com)
        # 通过指定的不同端来获取信息
        #这里的k就是client值，v值编号已list显示，如30端下面获取两个参数，会出现列表
        for k, v in wss.items():
            if k in result.keys():
                # 通过command来确定收取几次信息
                for cc, item in command.items():
                    self._ws_recv(result[k], k, cc)
                    if not self.q.empty():
                        r = self.q.get()
                        if r.split(';')[0] == 'fail':
                            result['res_info'] = "ws信令获取失败"
                            result['errormsg'] = r.split(';')[1]
                        else:
                            # 查找的同一client下面的相同command的数据，&即获取集合的交集
                            for n in set(item) & set(v):
                                logger.info("查找的信息为：%s", _reg[n])
                                reg = re.compile(_reg[n])
                                tmp=reg.findall(r.split(';')[1])
                                logger.info('查找%s信息为:%s' % (_reg[n], tmp))
                                # tmp = re.search(_reg[n], r.split(';')[1])
                                if tmp:
                                    try:
                                        if len(tmp) == 1:
                                            result[names[n]] = tmp[0]
                                        else:
                                            result[names[n]] = tmp
                                        # result[names[n]] = tmp.group(1)
                                    except Exception as e:
                                        logger.error("失败原因：%s" % (e))
                                else:
                                    result['res_info'] = r.split(';')[1]
                                    result['errormsg'] = '%s未找到对应参数值' % _reg[n]
                                    logger.error('%s未找到对应参数值' % _reg[n])
                                    break
            else:
                result['res_info'] = '客户端%s还没有连接' % k
                result['errormsg'] = '客户端%s还没有连接' % k
                logger.error('客户端%s还没有连接' % k)