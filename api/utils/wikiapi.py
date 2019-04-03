#coding=utf-8
from selenium import webdriver
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import re
import time
import os
import subprocess
from tal import logconfig
from tal import settings
logger=logconfig.Log('api')


class getapi():
    def __init__(self,url,args):
        try:
            self.url=url
            self.args=args
            self.p=""
            self.dr=""
            # 使用htmlunit，必须启动webdriver server
            if "JAVA_HOME" in os.environ:
                logger.info("没有java环境，使用firefox driver")
                # raise Exception("没有安装java环境，请安装")
                server_jar=os.path.join(settings.STATICFILES_DIRS[0], 'jar','selenium-server-standalone-3.8.0.jar'),
                cmd='java -jar '+ server_jar[0]
                self.p=subprocess.Popen(cmd)
                self.dr = webdriver.Remote("http://localhost:4444/wd/hub", desired_capabilities=DesiredCapabilities.HTMLUNIT)
            else:
                self.dr = webdriver.Firefox()
            self.dr.get(self.url)
        except Exception as e:
            logger.error(e)

    def login(self):
        try:
            name=self.dr.find_element_by_id('os_username')
            name.send_keys('guoxinfa')
            password=self.dr.find_element_by_id('os_password')
            password.send_keys('123456')
            self.dr.find_element_by_id('loginButton').click()
        except Exception as e:
            logger.error(e)

    def gethtml(self):
        html=""
        try:
            if self.args is None:
                content = self.dr.find_element_by_id('main-content')
                html = content.get_attribute('innerHTML')
            else:
                link = self.dr.find_element_by_link_text(self.args)
                link.click()
                time.sleep(3)
                content = self.dr.find_element_by_id('main-content')
                html = content.get_attribute('innerHTML')
        except Exception as e:
            logger.error(e)
        finally:
            if self.p !="":
                self.p.terminate()
            else:
                self.dr.close()
        return html
    def getinfo_bs(self,html_):
        res = {}
        if html_=="":
            res['error'] = '未搜索到相关信息，请查看日志'
            return res
        soup = bs(html_, "html.parser")
        # 标题
        title = soup.find_all("h1")
        res["title"] = [x.string for x in title if x.string is not None]
        p = soup.find_all("p")
        url_tmp = [x.get_text() for x in p]
        print(url_tmp)
        url = ["".join(x.split()) for x in url_tmp if x.upper().startswith(('GET', 'POST'))]
        print(url)
        if url:
            try:
                method = [x.split(':')[0] for x in url]
                res['method'] = method
                urls = [''.join(y) for y in [x.split(':')[1:] for x in url]]
                res['url'] = urls
            except:
                a = soup.find_all("a")
                res['url'] = [y for y in [x.string for x in a] if y and y.lower().startswith(('http', 'https'))]
        else:
            pre = soup.find_all("pre")
            # _url = [x.get_text() for x in pre]
            _url = []
            for a in pre:
                _a = a.find("a")
                if _a:
                    _url.extend(_a)
            res['url'] = _url
        # 请求参数
        table = soup.find_all("table", class_="confluenceTable")
        param = []
        for tb in table:
            td = tb.find_all("td")
            pam = [x.get_text() for x in td]
            _p = pam[0::4]
            par = []
            for i in range(len(_p)):
                par.append(_p[i].strip('$') + "=")

            param.append('&'.join(par))
        res['param'] = param

        # 参数示范
        # code=soup.find_all("code",class_="java")
        # all=[x.get_text() for x in code]
        # print(all)
        # aa=[]
        # for i in [''.join(x.split())for x in all]:
        #     if i=="'{'":
        #         aa.append(i)
        #     elif i=="":
        #         pass
        #     elif i=="'}'":
        #         aa.append(i)
        #         break
        #     else:
        #         aa.append(i)
        # print (aa)
        logger.info (res)
        return res

    def getinfo_re(self,html):
        dr = re.compile(r'<[^>]+>', re.S)
        title_reg = re.compile('h1 .*?>(.*?)</h1>')
        p_reg = re.compile('<p>(.*?)</p>')
        # 参数实例
        table_reg = re.compile('<td class="code">(.*?)</td>')
        # 请求参数
        body_reg = re.compile(r'<tr><td.*?confluenceTd.*?>(.*?)</td>.*?</tr>')
        title_tmp = title_reg.findall(html)
        title = [dr.sub('', x) for x in title_tmp]
        p = p_reg.findall(html)
        print(p)
        info = [dr.sub('', x) for x in p]
        nbsp = re.compile(r'&nbsp;')
        all = [nbsp.sub('', x) for x in info if x != '&nbsp;']
        print(all)
        url_tmp = [x for x in all if x.startswith(('GET', 'POST','get','post'))]
        _body = body_reg.findall(html)
        body = [dr.sub('', x) for x in _body]
        # 请求参数第一列
        print(body)
        table_tmp = table_reg.findall(html)
        str_reg = re.compile(r'<code .*?java.*?>(.*?)</code>')
        str = str_reg.findall(table_tmp[0])
        # 实例参数
        print([nbsp.sub('', x) for x in str if x != '&nbsp;'])

        print(title)
        print(url_tmp)
        # if len(title)==len(url_tmp):
        temp = [x.split(':', maxsplit=1) for x in url_tmp]
        method = [x[0] for x in temp]
        temp1 = [x[1].split('?') for x in temp]
        url = [x[0] for x in temp1]
        param = [x[1] if len(x) > 1 else '' for x in temp1]
        print(method)
        print(url)
        print(param)

if __name__ == '__main__':
    # url='http://sswiki.speiyou.com/pages/viewpage.action?pageId=1248908'
    # api=getapi(url,'课中文档','0314版本文档','互动红包(0314完成)')
    # api.openbrows()
    # api.login()
    # html=api.gethtml()
    # print(html)
    pass






















