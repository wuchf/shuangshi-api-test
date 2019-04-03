import requests


class Robot:
    def __init__(self):
        # self.url = 'https://oapi.dingtalk.com/robot/send?access_token=02631e40d5e3fc810a6c431f1bdefc1c412100bafcf34268f6a9e3a7054bf296'
        self.url = 'https://oapi.dingtalk.com/robot/send?access_token=63fb97b47fb5fdfbbe3a5551c4072745dfe509613c0d7906f3dd15066914f2f7'

    def sendlink(self, title, text, messageUrl):
        json = {
            "msgtype": "link",
            "link": {
                "text": text,
                "title": title,
                "picUrl": "",
                "messageUrl": messageUrl
            }
        }
        requests.post(url=self.url, json=json)

    def sendtext(self, text, isAtAll=False):
        json = {
            "msgtype": "text",
            "text": {
                "content": text
            },
            "at": {
                "isAtAll": isAtAll
            }
        }
        requests.post(url=self.url, json=json)
