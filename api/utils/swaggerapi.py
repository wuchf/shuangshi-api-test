## coding=gbk

from selenium import webdriver
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
from tal import logconfig
logger=logconfig.Log('api')

class swaggerapi():
    def __init__(self,content,active):
        self.content=content
        #用来确定激活的active，如果不指定active，会有很多信息，没办法找出脏数据
        if active is not None:
            if "-" in active:
                self.active = "45".join(active.split("-"))
            else:
                self.active=active
        else:
            if "#" in self.content:
                con=self.content.split("#")[-1]
                if len(con)>1:
                    self.active=self.content.split("#")[-1].lstrip("/")
                else:
                    self.active=None
            else:
                self.active=None
        logger.info (self.active)
        try:
            self.dr=webdriver.Firefox()
            # self.dr = webdriver.Remote("http://localhost:4444/wd/hub", desired_capabilities=DesiredCapabilities.HTMLUNIT)
            self.dr.get(self.content)
        except Exception as e:
            logger.error(e)

    def gethtml(self):
        html=''
        try:
            body=self.dr.find_element_by_tag_name('body')
            time.sleep(10)
            # print(body.get_attribute('innerHTML'))
            if self.active is not None:
                logger.info ("resource_" + self.active)
                content = body.find_element_by_id("resource_" + self.active)
                html = content.get_attribute('innerHTML')
            else:
                logger.error("没有指定需要查到的定位信息，请输入路径信息")
        except Exception as e:
            logger.error(e)
        finally:
            self.dr.close()
            # self.p.terminate()
        return html

    def getinfo_bs(self,html_):
        res = {}
        if html_=="":
            res['error'] = '未搜索到相关信息，请查看日志'
            return res
        soup = bs(html_, "html.parser")
        # 标题
        title = soup.find_all("ul", class_="options")
        _title = [x.get_text().strip('\n') for x in title]
        res['title'] = '\n'.join([x for x in _title if "Operations" not in x])
        method = soup.find_all("span", class_="http_method")
        _method = [x.get_text().strip('\n') for x in method]
        res['method'] = '\n'.join(_method)
        urls = soup.find_all("span", class_="path")
        _url = [x.get_text().strip('\n') for x in urls]
        res['url'] = '\n'.join(_url)

        table = soup.find_all("table", class_="parameters")
        param = []
        body = []
        for tb in table:
            td = tb.find_all("td")
            pam = [x.get_text() for x in td]
            # Enum不知道是什么，在参数的时候直接取消
            _pam = [x.strip('\n') for x in pam if x != 'Enum:']
            _p = _pam[0::5]  # 保存参数
            _v = _pam[3::5]  # 保存类型
            _b = _pam[4::5]  # 保存body字段
            par = []
            bo = []
            for i in range(len(_v)):
                if _v[i].lower() == 'body':
                    if "{" in _b[i]:
                        # bo.append('{'+_b[i].split('{')[-1].strip('\n'))
                        bo.append(''.join(_b[i].split('\n\n\n\n')[-1].split('\n')))
                elif _v[i].lower() == 'path':
                    # 字段在路径中出现，所以在参数字段中不存在
                    pass
                else:
                    par.append(_p[i].strip('$') + "=")
            body.append(bo)
            param.append('&'.join(par))
        res['param'] = '\n'.join(param)
        # res['body'] = '\n'.join(["".join(x[0].split()) for x in body])
        bb = []
        for b in body:
            if b:
                bb.append("".join(b[0].split()))
            else:
                bb.append("")
        res['body'] = '\n'.join(bb)
        logger.info(res)
        return res

if __name__ == '__main__':
    ss=swaggerapi("http://192.168.10.101:8030/swagger-ui.html#/activity45life45controller",None)
    html=ss.gethtml()
    print(html)
    res=ss.getinfo_bs(html)
    print (res)






