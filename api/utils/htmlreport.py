import sys
HTML_TMP='''
    <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link href="../../static/css/bootstrap.min.css" rel="stylesheet">
    <script src="../../static/js/jquery-3.2.1.min.js"></script>
    <script src="../../static/js/bootstrap.min.js"></script>
    <script src="http://cdn.hcharts.cn/highcharts/highcharts.js"></script>
    <style type="text/css">
        #chart{
            width: 550px;
            height: 500px;
            margin: 0;
        }
        .fail{
            color: red;
            font-weight:bold

            }
        td{
            {#max-width: 80px;#}
            word-wrap: break-word;
            table-layout:fixed;
            word-break:break-all;
        }
    </style>
    <title>%(title)s</title>
</head>
<body>
%(script)s
%(body)s

</body>
'''
HTML_SCRIPT='''
<script language="JavaScript">
    $(document).ready(function() {  
   var chart = {
       plotBackgroundColor: null,
       plotBorderWidth: null,
       plotShadow: false
   };
   var title = {
      text: '测试结果比例'   
   };      
   var tooltip = {
      pointFormat: '{series.name}：{point.percentage:.2f}%%'
   };
   var plotOptions = {
      pie: {
         allowPointSelect: true,
         cursor: 'pointer',
         dataLabels: {
            enabled: true,
            format: '<b>{point.name}</b>: {point.percentage:.2f}%%',
            style: {
               color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
            }
         }
      }
   };
   var series= [{
      type: 'pie',
      name: '比例',
      data: [
       ['error',    %(fail)d],
         {
            name: 'pass',
            y: %(success)d,
            sliced: true,
            selected: true
         },
      ]
   }];     
      
   var json = {};   
   json.chart = chart; 
   json.title = title;     
   json.tooltip = tooltip;  
   json.series = series;
   json.plotOptions = plotOptions;
   $('#chart').highcharts(json);  
});
function clickall() {
        $("#all").toggle();
        $("#fail").hide();
    }
function clickfail() {
        $("#fail").toggle();
        $("#all").hide();
    }
</script>

'''
HTML_BODY='''
<div class="container" >
<h2>%(title)s</h2>
    <div class="col-md-12">
        <div class="col-md-3">
            <h3>测试概要信息</h3>
            <p> 总计运行时间：%(time)s</p>
            <p> 运行用例总数：<a href='javascript:clickall()'>%(total)s</a>,
            <p> 执行成功用例数：%(success)s</p>
            <p> 执行失败用例数：%(fail)s</p>
            <p><a href="#" onclick="clickall();return false;">查看结果详情</a></p>
            <p><a href="#" onclick="clickfail();return false;">查看失败信息</a></p>
        </div>
        <div class="col-md-9">
            <div id="chart" style="width: 650px; height: 350px; margin: 0 auto"></div>
        </div>
    </div>
    <div id='all' style="display: none">
    <h3>全部详细信息</h3>
        <table class="table table-striped table-bordered table-hover" width="100">
            <caption>详细结果</caption>
                <th >用例名</th>
                <th >用例序号</th>
                <th >pass/fail</th>
                <th >预期结果</th>
                <th >实际结果</th>
                %(tr)s
        </table>
    </div>
    <div id='fail' style="display: none">
    <h3>失败详细信息</h3>
        <table class="table table-striped table-bordered table-hover" width="100">
            <caption>详细结果</caption>
                <th >用例名</th>
                <th >用例序号</th>
                <th >fail</th>
                <th >预期结果</th>
                <th >实际结果</th>
                %(err)s
        </table>
    </div>
    </div>
'''
TABLE_INFO='''
    <tr>
        <td width="15%%" rowspan="%(n)s">%(name)s</td>
        <td width="7%%" rowspan="%(n)s">%(seqid)s</td>
        <td width="8%%"class="%(result)s" rowspan="%(n)s">%(result)s</td>
    </tr>
    %(res)s
'''
TR = '''
    <tr><td width="35%%">%s</td><td width="35%%">%s</td></tr>
    '''



class result():
    DEFAULT_TITLE = '测试报告'
    def __init__(self,results,t_begin,t_end,stream=sys.stdout,title=None):
        self.stream=stream
        if title:
            self.title=title
        else:
            self.title=self.DEFAULT_TITLE
        self.results=results
        self.fail=[x for x in self.results if x['result'] == 'fail']
        self.success=[x for x in self.results if x['result'] == 'pass']
        self.time=t_end-t_begin

    def _generate_data(self):
        #所有信息
        rows=[]
        for info in self.results:
            exp = info.get('expect').split('\n')
            n = len(exp)
            info['n'] = n + 1
            tr = ''
            if n > 1:
                for i in range(len(exp)):
                    if isinstance(info.get('response'),list):
                        tr += TR % (exp[i], info.get('response')[i])
                    else:
                        tr += TR % (exp[i], info.get('response'))
            else:
                tr+=TR%(info.get('expect'),info.get('response'))
            info['res'] = tr
            row=TABLE_INFO % info
            rows.append(row)
        #失败信息显示
        fails_li = []
        if len(self.fail)>0:
            for err in self.fail:
                exp = err.get('expect').split('\n')
                n = len(exp)
                err['n'] = n + 1
                tr = ''
                if n > 1:
                    for i in range(len(exp)):
                        if isinstance(info.get('response'), list):
                            tr += TR % (exp[i], err.get('response')[i])
                        else:
                            tr += TR % (exp[i], err.get('response'))
                else:
                    tr += TR % (err.get('expect'), err.get('response'))
                err['res'] = tr
                fail = TABLE_INFO % err
                fails_li.append(fail)
        else:
            pass
            # fail = '''<tr>无错误信息</tr>'''

        body = HTML_BODY % dict(
            err=''.join(fails_li),
            tr=''.join(rows),
            title=self.title,
            time=self.time,
            total=len(self.results),
            success=len(self.success),
            fail=len(self.fail),
        )
        return body
    def chart(self):
        if len(self.results)==0:
            chart = HTML_SCRIPT % dict(
                fail=0,
                success=0,
            )
        else:
            chart=HTML_SCRIPT % dict(
                fail=len(self.fail)/len(self.results)*100,
                success = len(self.success) / len(self.results) * 100,
            )
        return chart

    def generatereport(self):
        output=HTML_TMP %dict(
            title=self.title,
            body=self._generate_data(),
            script=self.chart()
        )
        self.stream.write(output.encode('utf-8'))

if __name__ == '__main__':
    fp=open("result.html",'wb')
    time='0.12'
    #results=[{'name': 'login', 'seqid': 1, 'expect': "'status','200'", 'result': 'fail', 'response': '{"avatar":null,"businessId":"40288b155f4d4c0c015f4d9a2eef00d1","userType":"2","loginName":"xiangjiaopi","token":"fab340e5229f4dc48e95ea583abd18cd","point":0,"areaCode":"020","areaName":"广州","liveNum":null,"classId":null,"classNum":null,"yunXinId":"40288b155f4d4c0c015f4d9a2eef00d1","yunXinToken":"9c0d6e6ec1ba4921a9677813000e7e03","stuNum":0}'}, {'name': 'login', 'seqid': 2, 'expect': '1000', 'result': 'pass', 'response': '{"message":"用户名或密码错误","status":"error"}'}]
    results=[{'name': 'ws通信', 'seqid': 1, 'expect': 'reply.*?"code":0.*?"msg":"ok"', 'response': ['{"type":"reply","cmd":"join","code":0,"msg":"ok","reqid":123}'], 'result': 'pass'}, {'name': 'ws通信', 'seqid': 2, 'expect': 'reply.*?"code":0.*?"msg":"ok"', 'response': ['{"type":"reply","cmd":"heart","code":0,"msg":"ok","reqid":123}'], 'result': 'pass'}, {'name': 'ws通信', 'seqid': 3, 'expect': 'reply.*?"code":0.*?"msg":"ok"', 'response': ['{"type":"reply","cmd":"get_room_users","code":0,"msg":"ok","reqid":123,"data":[{"room_id":"r_65","user_id":"t_91","role":"t","guid":"6c983908fb4635f6777457d9647d5604","user_info":{"audio_status":0,"stream_id":"peiyou-o2o_beijing2_beijingerxiao2&__03"},"login_time":1539155211}]}'], 'result': 'pass'}, {'name': 'ws通信', 'seqid': 4, 'expect': 'reply.*?"code":-15', 'response': ['{"type":"reply","cmd":"send","code":-15,"msg":"all user_id does not exist","reqid":123}'], 'result': 'pass'}, {'name': 'ws通信', 'seqid': 5, 'expect': 'reply.*?"code":0.*?"msg":"ok"', 'response': ['{"type":"reply","cmd":"update_user_info","code":0,"msg":"ok","reqid":null}'], 'result': 'pass'}, {'name': 'ws通信', 'seqid': 6, 'expect': 'reply.*?"code":0.*?"msg":"ok"', 'response': ['{"type":"reply","cmd":"quit","code":0,"msg":"ok","reqid":123}'], 'result': 'pass'}]
    res=result(results,time,fp)
    res.generatereport()
    #print (res.chart())

