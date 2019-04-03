# coding=utf-8
import shutil
from urllib import parse

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
import os
import json
import time
from . import models
from .utils.run import RUN
from .utils import common, htmlreport, robot,swaggerapi,wikiapi
from tal import logconfig

logger = logconfig.Log('api')

RESULT_PATH = os.path.join(settings.BASE_DIR, 'api', 'result')


# Create your views here.
def index(req):
    if req.method == 'GET':
        #直接返回到具体的项目中
        proname=req.GET.get("pro_name")
        pagenum=req.GET.get("page_num")
        if proname is None:
            proname=""
        if pagenum is None:
            pagenum=1
        logger.info("当前的项目为%s,当前的页数为%s"%(proname,pagenum))
        result = models.Apicommon.objects.filter(project=0)
        data_common=[]
        for i in result:
            data_common.append({'id':i.id,'key': i.key, 'value': i.value})
        logger.info("系统共有参数：%s"%data_common)
        return render(req, 'api/index.html',{'name':proname,'pageNum':pagenum,"data_common":data_common,"data_procomm":data_common})
    else:
        pass


# 获取接口下的用例
def caselist(req):
    if req.method == 'GET':
        cid = req.GET.get('id')
        result = models.ApiCase.objects.filter(cname=cid)
        data = []
        for i in result:
            data.append(
                {'seqid': i.seqid, 'params': i.params, 'restype': i.restype, 'response': i.response, 'body': i.body})
        return HttpResponse(json.dumps(data), content_type="application/json")
    else:
        cid = req.POST.get('id')
        pagenum=req.POST.get('pagenum')
        name=models.ApiList.objects.filter(id=cid).values('name')[0]
        pid=models.ApiList.objects.filter(id=cid).values('project_id')[0]
        pro_name=models.Apiproject.objects.filter(id=pid.get("project_id")).values("name")[0]
        result = models.ApiCase.objects.filter(cname=cid)
        result_param = models.ApiParam.objects.filter(cname=cid)
        result_postcon = models.ApiPostcon.objects.filter(cname=cid)
        data = []
        data_param = []
        data_postcon = []
        for i in result:
            if i.name is None:
                i.name=""
            if i.re is None:
                i.re=""
            data.append(
                {'seqid': i.seqid, 'params': i.params, 'restype': i.restype, 'response': i.response,
                 'body': i.body,'name':i.name,'re':i.re})
        for i in result_param:
            data_param.append(
                {'seqid': i.seqid, 'name': i.name, 'url': i.url, 'type': i.type, 'header': i.header,
                 'params': i.params, 'body': i.body,'re': i.re})
        for i in result_postcon:
            data_postcon.append(
                {'seqid': i.seqid, 'name': i.name, 'url': i.url, 'type': i.type, 'header': i.header,
                 'params': i.params, 'body': i.body, 'time': i.time})
        result = models.Apicommon.objects.filter(project=0)
        data_common = []
        for i in result:
            data_common.append({'id': i.id, 'key': i.key, 'value': i.value})
        result = models.Apicommon.objects.filter(project=pid.get("project_id"))
        data_procommon = []
        for i in result:
            data_procommon.append({'id': i.id, 'key': i.key, 'value': i.value})
        return render(req, 'api/apilist.html',
                      {'name':name.get('name'),'proname':pro_name.get('name'),'pagenum':pagenum[:len(pagenum)-1],
                       'data': data, 'id': cid, 'data_param': data_param, 'data_postcon': data_postcon,
                       "data_procommon":data_procommon,"data_common":data_common})


# 用例
def case(req):
    if req.method == 'POST':
        opt = req.POST.get('opt')
        if opt == 'add':  # 添加用例
            case_id = req.POST.get('name')
            case_param = req.POST.get('params')
            case_restype = req.POST.get('restype')
            case_response = req.POST.get('response')
            case_body = req.POST.get('body')
            case_name = req.POST.get('pname')
            case_re = req.POST.get('re')
            case_seqid = models.ApiCase.objects.filter(cname=case_id).count() + 1
            cname = models.ApiList.objects.get(id=case_id)
            logger.info('用例新增信息为%s,%s,%s,%s,%s,%s,%s' % (case_id, case_param, case_restype, case_response, case_body,case_name,case_re))
            try:
                obj = models.ApiCase(seqid=case_seqid, params=case_param, response=case_response, cname=cname,
                                     restype=case_restype, body=case_body,name=case_name,re=case_re)
                obj.save()
            except Exception as e:
                logger.error(e)
                return HttpResponse(e, status=502)
        elif opt == 'edit':  # 修改用例
            case_seqid = req.POST.get('seqid')
            case_id = req.POST.get('name')
            case_params = req.POST.get('params')
            case_restype = req.POST.get('restype')
            case_response = req.POST.get('response')
            case_body = req.POST.get('body')
            case_name = req.POST.get('pname')
            case_re = req.POST.get('re')
            # if not common.isdict(case_body):
            #     return HttpResponse('body不为字典形式！', status=502)
            cname = models.ApiList.objects.get(id=case_id)
            logger.info('用例修改信息为%s,%s,%s,%s,%s,%s,%s' % (case_id, case_params, case_restype, case_response, case_body,case_name,case_re))
            try:
                obj = models.ApiCase.objects.get(seqid=case_seqid, cname=cname)
                obj.params = case_params
                obj.body = case_body
                obj.restype = case_restype
                obj.response = case_response
                obj.name=case_name
                obj.re=case_re
                obj.save()
            except Exception as e:
                logger.error(e)
                return HttpResponse(e, status=502)
        elif opt == 'order':  # 用例排序
            number = int(req.POST.get('number'))
            cid = req.POST.get('name')
            with transaction.atomic():
                models.ApiCase.objects.filter(cname=cid).delete()
                case_cname = models.ApiList.objects.get(id=cid)
                for i in range(0, number):
                    case_param = req.POST.get('allTableData[%d][params]' % i)
                    case_body = req.POST.get('allTableData[%d][body]' % i)
                    case_restype = req.POST.get('allTableData[%d][restype]' % i)
                    case_response = req.POST.get('allTableData[%d][response]' % i)
                    case_name = req.POST.get('allTableData[%d][name]' % i)
                    case_re = req.POST.get('allTableData[%d][re]' % i)
                    case_seqid = i + 1
                    models.ApiCase.objects.create(seqid=case_seqid, params=case_param, response=case_response,
                                                  cname=case_cname, restype=case_restype, body=case_body,
                                                  name=case_name,re=case_re)
        elif opt == 'info':  # 用例详情
            seqid = req.POST.get('seqid')
            cid = req.POST.get('name')
            _case = models.ApiCase.objects.filter(cname=cid, seqid=seqid)[0]
            re = {'params': _case.params, 'body': _case.body, 'restype': _case.restype, 'response': _case.response,'name':_case.name,'re':_case.re}
            return JsonResponse(re)
        return HttpResponse("ok")


# 获取API接口列表
def getlist(req):
    if req.method == 'GET':
        pro_name = req.GET.get('projectname')
        logger.info("获取的项目为：%s" % pro_name)
        data = []
        if len(pro_name) != 0:
            _pro = models.Apiproject.objects.filter(name=pro_name).values('id')
            pid = [i['id'] for i in _pro][0]
            result = models.ApiList.objects.filter(project_id=pid)
            for i in result:
                data.append({'id': i.id, 'name': i.name, 'url': i.url, 'type': i.type, 'header': i.header})
        return HttpResponse(json.dumps(data), content_type="application/json")
    else:
        pass


# 接口
def api(req):
    if req.method == 'POST':
        opt = req.POST.get('opt')
        if opt == 'add':  # 添加接口
            msg=[]
            api_name = req.POST.get('name')
            msg.append(common.check('text', api_name))
            api_url = req.POST.get('url')
            msg.append(common.check('url', api_url))
            api_type = req.POST.get('type')
            msg.append(common.check('type', api_type,api_url))
            api_header = req.POST.get('header')
            msg.append(common.check('header', api_header))
            api_project = req.POST.get('project')
            err_msg = [x for x in msg if x is not None]
            if err_msg:
                return HttpResponse(err_msg[0], status=502)
            if len(api_project)==0:
                _cn=models.Apiproject.objects.all().count()
                if _cn==0:
                    return HttpResponse("还没有项目，请先添加项目", status=502)
                return HttpResponse("项目信息不能为空，请选择", status=502)
            # 查找在同一项目下用例名称是否已经存在
            _num = models.ApiList.objects.filter(project_id=api_project).filter(name=api_name).count()
            if _num:
                return HttpResponse('名称重复！', status=502)
            try:
                obj = models.ApiList(name=api_name, url=api_url, type=api_type, header=api_header,
                                     project_id=api_project)
                obj.save()
            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
                # if e.args[0] == 1062:
                #     return HttpResponse('名称重复！', status=502)
        elif opt == 'edit':  # 修改接口
            # 接口名称不可修改
            msg = []
            api_id = req.POST.get('id')
            api_name = req.POST.get('name')
            api_url = req.POST.get('url')
            msg.append(common.check('url', api_url))
            api_type = req.POST.get('type')
            msg.append(common.check('type', api_type,api_url))
            api_header = req.POST.get('header')
            msg.append(common.check('header', api_header))
            api_pro = req.POST.get('project')
            err_msg = [x for x in msg if x is not None]
            if err_msg:
                return HttpResponse(err_msg[0], status=502)
            _project = models.Apiproject.objects.get(id=api_pro)
            # 如果修改了项目，查找在同一项目下用例名称是否已经存在
            old_pro = models.ApiList.objects.get(id=api_id).project
            if _project != old_pro:
                _num = models.ApiList.objects.filter(project_id=api_pro).filter(name=api_name).count()
                if _num:
                    return HttpResponse('名称重复！', status=502)
            try:
                obj = models.ApiList.objects.get(id=api_id)
                obj.name = api_name
                obj.url = api_url
                obj.type = api_type
                obj.header = api_header
                obj.project = _project
                obj.save()
            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
        elif opt == 'del':  # 删除接口
            api_id = req.POST.get('id')
            try:
                models.ApiList.objects.get(id=api_id).delete()
            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
        elif opt == 'info':  # 接口详情
            cid = req.POST.get('id')
            _api = models.ApiList.objects.filter(id=cid)[0]
            re = {'id': _api.id, 'name': _api.name, 'url': _api.url, 'type': _api.type, 'header': _api.header,
                  'project': _api.project.id}
            logger.info("接口信息为：", re)
            return JsonResponse(re)
        return HttpResponse("ok")
    elif req.method == 'GET':
        # 后置条件查找是否已经存在需要添加的接口
        api_name = req.GET.get('name')
        cid = req.GET.get('cid')
        try:
            _qry = models.ApiList.objects.get(id=cid)
            obj = models.ApiList.objects.filter(name=api_name).filter(project_id=_qry.project)[0]
            cases = models.ApiCase.objects.filter(cname_id=obj.id)
            body=[]
            param=[]
            for case in cases:
                body.append(case.body)
                param.append(case.params)
            res = {'type': obj.type, 'url': obj.url,'header':obj.header,'body':body,'param':param}
        except:
            res = {}
        return JsonResponse(res)
        # pro_id=req.GET.get('id')
        # try:
        #     obj=models.ApiList.objects.filter(project_id=pro_id)
        #     res={'type': obj.type, 'url': obj.url}
        # except:
        #     res={}
        # return JsonResponse(res)


# 参数化
def param(req):
    if req.method == 'POST':
        opt = req.POST.get('opt')
        if opt == 'add':  # 添加用例
            msg=[]
            case_id = req.POST.get('name')
            pname = req.POST.get('pname')
            purl = req.POST.get('purl')
            ptype = req.POST.get('ptype')
            pheader = req.POST.get('pheader')
            pparams = req.POST.get('pparams')
            pbody = req.POST.get('pbody')
            pre = req.POST.get('pre')
            # 在处理冷冻时间的时候，url可以为空
            try:
                p = eval(pparams)
                if not isinstance(p, dict) and 'sleep' not in p.keys():
                    msg.append(common.check('url', purl))
                    msg.append(common.check('type', ptype, purl))
            except Exception as e:
                logger.error(e)
            msg.append(common.check('header', pheader))
            err_msg = [x for x in msg if x is not None]
            if err_msg:
                return HttpResponse(err_msg[0], status=502)
            pseqid = models.ApiParam.objects.filter(cname=case_id).count() + 1
            cid = models.ApiList.objects.get(id=case_id)
            logger.info('参数化新增信息为%s,%s,%s,%s,%s,%s,%s,%s' % (case_id, pname, purl, ptype, pheader, pparams, pbody, pre))
            try:
                obj = models.ApiParam(cname=cid, seqid=pseqid, name=pname, url=purl, type=ptype, header=pheader,
                                      params=pparams,
                                      body=pbody, re=pre)
                obj.save()
            except Exception as e:
                logger.error(e)
                if e.args[0] == 1062:
                    return HttpResponse('名称重复！', status=502)
                else:
                    return HttpResponse(str(e), status=502)
        elif opt == 'edit':  # 修改用例
            msg=[]
            param_seqid = req.POST.get('seqid')
            case_id = req.POST.get('id')
            param_name = req.POST.get('pname')
            param_url = req.POST.get('purl')
            param_type = req.POST.get('ptype')
            param_header = req.POST.get('pheader')
            param_params = req.POST.get('pparams')
            param_body = req.POST.get('pbody')
            param_re = req.POST.get('pre')
            msg.append(common.check('url', param_url))
            msg.append(common.check('type', param_type,param_url))
            msg.append(common.check('header', param_header))
            err_msg = [x for x in msg if x is not None]
            if err_msg:
                return HttpResponse(err_msg[0], status=502)
            logger.info('参数化修改信息为%s,%s,%s,%s,%s,%s,%s,%s' % (
                case_id, param_name, param_url, param_type, param_params, param_body, param_re, param_header))
            cname = models.ApiList.objects.get(id=case_id)
            try:
                obj = models.ApiParam.objects.get(seqid=param_seqid, cname=cname)
                obj.name = param_name
                obj.url = param_url
                obj.type = param_type
                obj.header = param_header
                obj.params = param_params
                obj.body = param_body
                obj.re = param_re
                obj.save()
            except Exception as e:
                logger.error(e)
                if e.args[0] == 1062:
                    return HttpResponse('名称重复！', status=502)
                else:
                    return HttpResponse(str(e), status=502)
        elif opt == 'order':  # 用例排序
            number = int(req.POST.get('number'))
            cid = req.POST.get('name')
            with transaction.atomic():
                models.ApiParam.objects.filter(cname=cid).delete()
                case_cname = models.ApiList.objects.get(id=cid)
                for i in range(0, number):
                    param_name = req.POST.get('allTableData[%d][name]' % i)
                    param_url = req.POST.get('allTableData[%d][url]' % i)
                    param_type = req.POST.get('allTableData[%d][type]' % i)
                    param_header = req.POST.get('allTableData[%d][header]' % i)
                    param_params = req.POST.get('allTableData[%d][params]' % i)
                    param_body = req.POST.get('allTableData[%d][body]' % i)
                    param_re = req.POST.get('allTableData[%d][re]' % i)
                    param_seqid = i + 1
                    models.ApiParam.objects.create(seqid=param_seqid, name=param_name, url=param_url, type=param_type,
                                                   header=param_header, params=param_params, body=param_body,
                                                   re=param_re,
                                                   cname=case_cname)
        elif opt == 'info':  # 用例详情
            seqid = req.POST.get('seqid')
            cid = req.POST.get('name')
            _param = models.ApiParam.objects.filter(cname=cid, seqid=seqid)[0]
            re = {'seqid': _param.seqid, 'pname': _param.name, 'purl': _param.url, 'ptype': _param.type,
                  'pheader': _param.header,
                  'pparams': _param.params, 'pbody': _param.body, 'pre': _param.re}
            return JsonResponse(re)
        elif opt == 'import':  # 参数导入
            imname = req.POST.get('imname')
            cid = req.POST.get('name')
            logger.info('被导入的name为%s' % imname)
            logger.info('导入用例的信息为%s' % cid)
            try:
                _qry = models.ApiList.objects.get(id=cid)
                _sid = models.ApiParam.objects.filter(cname=cid).count()
                logger.info('前置条件已有最大序列值为%s' % _sid)
                param_list_to_insert = list()
                qry = models.ApiList.objects.get(name=imname, project_id=_qry.project)
                _param = models.ApiParam.objects.filter(cname=qry.id)
                for pa in _param:
                    param_list_to_insert.append(
                        models.ApiParam(seqid=pa.seqid + _sid, name=pa.name, url=pa.url, type=pa.type, header=pa.header,
                                        params=pa.params,
                                        body=pa.body, re=pa.re, cname=_qry))
                logger.info(param_list_to_insert)
                models.ApiParam.objects.bulk_create(param_list_to_insert)
            except Exception as e:
                logger.error("导入前置条件失败，失败原因是%s" % e)
                return HttpResponse('导入前置条件失败，请查看', status=502)
        return HttpResponse("ok")


# 后置条件
def postcon(req):
    if req.method == 'POST':
        opt = req.POST.get('opt')
        if opt == 'add':  # 添加
            msg=[]
            case_id = req.POST.get('name')
            pcname = req.POST.get('pcname')
            pcurl = req.POST.get('pcurl')
            pctype = req.POST.get('pctype')
            pcheader = req.POST.get('pcheader')
            pcparams = req.POST.get('pcparams')
            pcbody = req.POST.get('pcbody')
            tm = req.POST.get('time')
            #后置条件url可以为空，在处理冷冻时间的时候
            try:
                p = eval(pcparams)
                if not isinstance(p, dict) and 'sleep' not in p.keys():
                    msg.append(common.check('url', pcurl))
                    msg.append(common.check('type', pctype,pcurl))
            except Exception as e:
                logger.error(e)
            msg.append(common.check('header', pcheader))
            err_msg = [x for x in msg if x is not None]
            if err_msg:
                return HttpResponse(err_msg[0], status=502)
            pcseqid = models.ApiPostcon.objects.filter(cname=case_id).count() + 1
            logger.info(
                '后置条件新增信息为%s,%s,%s,%s,%s,%s,%s,%s' % (pcseqid, pcname, pcurl, pctype, pcparams, pcbody, tm, pcheader))
            cname = models.ApiList.objects.get(id=case_id)
            try:
                obj = models.ApiPostcon(cname=cname, seqid=pcseqid, name=pcname, url=pcurl, type=pctype,
                                        header=pcheader,
                                        params=pcparams, body=pcbody, time=tm)
                obj.save()
            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
        elif opt == 'edit':  # 修改
            logger.info('后置条件开始修改')
            msg=[]
            pc_seqid = req.POST.get('pcseqid')
            case_id = req.POST.get('name')
            pcname = req.POST.get('pcname')
            pcurl = req.POST.get('pcurl')
            pctype = req.POST.get('pctype')
            pcheader = req.POST.get('pcheader')
            pcparams = req.POST.get('pcparams')
            pcbody = req.POST.get('pcbody')
            tm = req.POST.get('time')
            # 后置条件url可以为空，在处理冷冻时间的时候
            try:
                p = eval(pcparams)
                if not isinstance(p, dict) and 'sleep' not in p.keys():
                    msg.append(common.check('url', pcurl))
                    msg.append(common.check('type', pctype, pcurl))
            except Exception as e:
                logger.error(e)
            msg.append(common.check('header', pcheader))
            err_msg=[x for x in msg if x is not None]
            if err_msg:
                return HttpResponse(err_msg[0], status=502)
            logger.info(
                '后置条件修改信息为%s,%s,%s,%s,%s,%s,%s,%s' % (pc_seqid, pcname, pcurl, pctype, pcparams, pcbody, tm, pcheader))
            cname = models.ApiList.objects.get(id=case_id)
            try:
                obj = models.ApiPostcon.objects.get(seqid=pc_seqid, cname=cname)
                obj.name = pcname
                obj.url = pcurl
                obj.type = pctype
                obj.header = pcheader
                obj.params = pcparams
                obj.body = pcbody
                obj.time = tm
                obj.save()
            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
        elif opt == 'order':  # 排序
            number = int(req.POST.get('number'))
            cid = req.POST.get('name')
            with transaction.atomic():
                models.ApiPostcon.objects.filter(cname=cid).delete()
                case_cname = models.ApiList.objects.get(id=cid)
                for i in range(0, number):
                    pc_name = req.POST.get('allTableData[%d][name]' % i)
                    pc_url = req.POST.get('allTableData[%d][url]' % i)
                    pc_type = req.POST.get('allTableData[%d][type]' % i)
                    pc_header = req.POST.get('allTableData[%d][header]' % i)
                    pc_params = req.POST.get('allTableData[%d][params]' % i)
                    pc_body = req.POST.get('allTableData[%d][body]' % i)
                    pc_time = req.POST.get('allTableData[%d][time]' % i)
                    pc_seqid = i + 1
                    models.ApiPostcon.objects.create(seqid=pc_seqid, name=pc_name, url=pc_url, type=pc_type,
                                                     header=pc_header,
                                                     params=pc_params, body=pc_body, time=pc_time,
                                                     cname=case_cname)
        elif opt == 'info':  # 详情
            seqid = req.POST.get('seqid')
            cid = req.POST.get('name')
            _pcon = models.ApiPostcon.objects.filter(cname=cid, seqid=seqid)[0]
            re = {'seqid': _pcon.seqid, 'pcname': _pcon.name, 'pcurl': _pcon.url, 'pctype': _pcon.type,
                  'pcheader': _pcon.header,
                  'pcparams': _pcon.params, 'pcbody': _pcon.body, 'time': _pcon.time}
            return JsonResponse(re)
        elif opt == 'import':  # 后置条件导入
            imname = req.POST.get('imname')
            cid = req.POST.get('name')
            logger.info('被导入的name为%s' % imname)
            logger.info('导入的name为%s' % cid)
            try:
                cname = models.ApiList.objects.get(id=cid)
                postcon_list_to_insert = list()
                _sid = models.ApiPostcon.objects.filter(cname=cname).count()
                logger.info('后置条件已有最大序列值为%s' % _sid)
                qry = models.ApiList.objects.get(name=imname, project_id=cname.project)
                _post = models.ApiPostcon.objects.filter(cname=qry.id)
                for pc in _post:
                    postcon_list_to_insert.append(
                        models.ApiPostcon(seqid=pc.seqid + _sid, name=pc.name, url=pc.url, type=pc.type,
                                          header=pc.header, params=pc.params,
                                          body=pc.body, time=pc.time, cname=cname))
                logger.info(postcon_list_to_insert)
                models.ApiPostcon.objects.bulk_create(postcon_list_to_insert)
            except Exception as e:
                logger.error("导入后置条件失败，失败原因是%s" % e)
                return HttpResponse('导入后置条件失败，请查看', status=502)
        return HttpResponse("ok")


# 项目信息
def project(req):
    if req.method == 'POST':
        opt = req.POST.get('opt')
        if opt == 'add':  # 添加
            name = req.POST.get('name')
            if len(name) == 0:
                return HttpResponse("项目名称不能为空", status=502)
            else:
                try:
                    obj = models.Apiproject(name=name)
                    obj.save()
                except Exception as e:
                    logger.error(e)
                    return HttpResponse(str(e), status=502)
        elif opt == 'info':  # 获取
            name_dic = {}
            _project = models.Apiproject.objects.all()
            for na in _project:
                name_dic[na.id] = na.name
            logger.info("获取系统的项目信息为：%s" % name_dic)
            return JsonResponse(name_dic)
        elif opt == 'query':  # 获取
            id=req.POST.get('id')
            _project = models.Apiproject.objects.get(id=id)
            res={'id':id,'name':_project.name}
            return JsonResponse(res)
        elif opt == 'edit':  # 获取
            id=req.POST.get('id')
            name=req.POST.get('name')
            if len(name) == 0:
                return HttpResponse("项目名称不能为空", status=502)
            num = models.Apiproject.objects.filter(name=name).count()
            if num != 0:
                return HttpResponse("项目已经存在，请直接添加项目用例", status=502)
            else:
                try:
                    obj = models.Apiproject.objects.get(id=id)
                    obj.name = name
                    obj.save()
                except Exception as e:
                    logger.error(e)
                    return HttpResponse(str(e), status=502)
        elif opt == 'assert':  # 验证
            name = req.POST.get('name')
            logger.info("验证项目名称：%s"%name)
            if len(name) == 0:
                return HttpResponse("项目名称不能为空!", status=502)
            num = models.Apiproject.objects.filter(name=name).count()
            if num != 0:
                return HttpResponse("项目已经存在!", status=502)
        elif opt == 'pwd':  # 验证
            password = req.POST.get('password')
            if len(password) == 0:
                return HttpResponse("密码不能为空!", status=502)
            else:
                if password!=settings.ADMINPWD:
                    return HttpResponse("密码不正确!", status=502)
        elif opt == 'del':  # 验证
            id = req.POST.get('id')
            logger.info("将要删除的项目为：%s"%id)
            try:
                models.Apiproject.objects.get(id=id).delete()
            except Exception as e:
                logger.error(e)
                return HttpResponse(e, status=502)
        elif opt=='copy':
            #对项目进行copy修改
            id = req.POST.get('id')
            name=req.POST.get('name')
            logger.info("复制项目名称为%s为项目%s"%(id,name))
            if len(name) == 0:
                return HttpResponse("项目名称不能为空", status=502)
            num = models.Apiproject.objects.filter(name=name).count()
            if num != 0:
                return HttpResponse("项目已经存在，请修改项目名称", status=502)
            try:
                with transaction.atomic():
                    _project=models.Apiproject(name=name)
                    _project.save()
                    api_obj = models.ApiList.objects.filter(project=id)
                    logger.info("获取到的apilist信息为：%s"%(api_obj))
                    case_list_to_insert = list()
                    param_list_to_insert = list()
                    postcon_list_to_insert = list()
                    for i in api_obj:
                        _list=models.ApiList(name=i.name, url=i.url, type=i.type,
                                           header=i.header, project=_project)
                        _list.save()
                        _case_obj=models.ApiCase.objects.filter(cname=i)
                        for case_obj in _case_obj:
                            case_list_to_insert.append(
                                models.ApiCase(seqid=case_obj.seqid, cname=_list, params=case_obj.params,
                                               body=case_obj.body, restype=case_obj.restype,
                                               response=case_obj.response, name=case_obj.name,
                                               re=case_obj.re))
                        _param_obj = models.ApiParam.objects.filter(cname=i)
                        for param_obj in _param_obj:
                            param_list_to_insert.append(
                                models.ApiParam(seqid=param_obj.seqid, cname=_list, params=param_obj.params,
                                                          body=param_obj.body, url=param_obj.url,
                                                          type=param_obj.type, name=param_obj.name,
                                                          re=param_obj.re,header=param_obj.header))
                        _postcon_obj = models.ApiPostcon.objects.filter(cname=i)
                        for postcon_obj in _postcon_obj:
                            postcon_list_to_insert.append(
                                models.ApiPostcon(seqid=postcon_obj.seqid, cname=_list, params=postcon_obj.params,
                                                  body=postcon_obj.body, url=postcon_obj.url,
                                                  type=postcon_obj.type, name=postcon_obj.name,
                                                  time=postcon_obj.time, header=postcon_obj.header))
                    models.ApiCase.objects.bulk_create(case_list_to_insert)
                    models.ApiParam.objects.bulk_create(param_list_to_insert)
                    models.ApiPostcon.objects.bulk_create(postcon_list_to_insert)
            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
        elif opt=='export':
            #对项目的用例导出
            id = req.POST.get('id')
            print("导出的项目名称为%s"%(id))
            try:
                with transaction.atomic():
                    api_obj = models.ApiList.objects.filter(project=id)
                    print("获取到的apilist信息为：%s"%(api_obj))
                    for i in api_obj:
                        with open('list.txt','a+') as f:
                            f.writelines({'id':i.id,'name':i.name,'url':i.url,'type':i.type,
                                          'header':i.header,'project':i.project})
                        _case_obj=models.ApiCase.objects.filter(cname=i)
                        for case_obj in _case_obj:
                            with open('case.txt','a+') as f:
                                f.writelines(
                                    {'id':case_obj.id,'seqid':case_obj.seqid, 'cname':i, 'params':case_obj.params,
                                    'body':case_obj.body, 'restype':case_obj.restype,
                                     'response':case_obj.response, 'name':case_obj.name,'re':case_obj.re})
                        _param_obj = models.ApiParam.objects.filter(cname=i)
                        for param_obj in _param_obj:
                            with open('param.txt','a+') as f:
                                f.writelines(
                                    {'id':param_obj.id,'seqid':param_obj.seqid,'cname':i,'params':param_obj.params,
                                    'body':param_obj.body,'url':param_obj.url,
                                    'type':param_obj.type,'name':param_obj.name,
                                    're':param_obj.re,'header':param_obj.header})

                        _postcon_obj = models.ApiPostcon.objects.filter(cname=i)
                        for postcon_obj in _postcon_obj:
                            with open('postcon.txt','a+') as f:
                                f.writelines(
                                    {'id':postcon_obj.id,'seqid':postcon_obj.seqid,'cname':i,
                                     'params':postcon_obj.params,'body':postcon_obj.body,'url':postcon_obj.url,
                                  'type':postcon_obj.type,'name':postcon_obj.name,
                                  'time':postcon_obj.time,'header':postcon_obj.header})
                    # shutil.make_archive('tmp', 'zip')
                    # name = 'sql.zip'

            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
    else:
        project_info = []
        _project = models.Apiproject.objects.all()
        for na in _project:
            num=models.ApiList.objects.filter(project_id=na.id).count()
            project_info.append({'id':na.id,'name':na.name,'num':num})
        logger.info("获取系统的项目信息为：%s" % project_info)
        return HttpResponse(json.dumps(project_info), content_type="application/json")
    return HttpResponse("ok")

# 公共参数信息
@csrf_exempt
def commonpara(req):
    if req.method == 'POST':
        opt = req.POST.get('opt')
        if opt == 'add':  # 添加
            key = req.POST.get('key')
            value = req.POST.get('value')
            project = req.POST.get('project')
            if project=="":
                project=0
            if len(key) == 0:
                return HttpResponse("参数key值不能为空", status=502)
            elif len(value)==0:
                return HttpResponse("参数value值不能为空", status=502)
            else:
                logger.info("添加参数信息的key值为%s，value值为%s，项目值为%s"%(key,value,project))
                num = models.Apicommon.objects.filter(key=key,project=project).count()
                if num != 0:
                    return HttpResponse("参数key值已经存在，不能重复添加")
                try:
                    obj = models.Apicommon(key=key,value=value,project=project)
                    obj.save()
                except Exception as e:
                    logger.error(e)
                    return HttpResponse(str(e), status=502)
        elif opt == 'edit':  # 编辑
            id=req.POST.get('id')
            key = req.POST.get('key')
            value = req.POST.get('value')
            project = req.POST.get('project')
            if project == "":
                project = 0
            elif len(value) == 0:
                return HttpResponse("参数value值不能为空", status=502)
            else:
                logger.info("修改参数信息的id值为%s，key值为%s，value值为%s，项目值为%s"%(id,key, value, project))
                try:
                    obj = models.Apicommon(id=id, key=key, value=value, project=project)
                    obj.save()
                    obj = models.Apicommon.objects.get(id=id)
                    # obj.key = key#不可修改
                    obj.value = value
                    obj.project = project
                    obj.save()
                except Exception as e:
                    logger.error(e)
                    return HttpResponse(str(e), status=502)
        elif opt == 'info':  # 获取信息
            id = req.POST.get('id')
            result = models.Apicommon.objects.get(id=id)
            data = {'id': result.id, 'key': result.key, 'value': result.value, 'project': result.project}
            logger.info("获取的参数信息为：%s"%data)
            return JsonResponse(data)
        elif opt == 'del':  # 删除信息
            id = req.POST.get('id')
            try:
                models.Apicommon.objects.get(id=id).delete()
            except Exception as e:
                logger.error(e)
                return HttpResponse(str(e), status=502)
    else:
        if req.method == 'GET':
            pro_name = req.GET.get('projectname')
            logger.info("获取的项目为：%s" % pro_name)
            data = []
            if len(pro_name) != 0:
                _pro = models.Apiproject.objects.filter(name=pro_name).values('id')
                pid = [i['id'] for i in _pro][0]
                result = models.Apicommon.objects.filter(project=pid)
                for i in result:
                    data.append({'id':i.id,'key': i.key, 'value': i.value})
                logger.info("获取的项目%s参数信息为：%s" % (pro_name, data))
            return HttpResponse(json.dumps(data), content_type="application/json")
    return HttpResponse("ok")

#自动生成用例api
def generate(req):
    if req.method == 'POST':
        pro=req.POST.get("pro")
        logger.debug (pro)
        return render(req,'api/generate.html',{'pro':pro})
    else:
        pro = req.GET.get("pro")
        logger.debug(pro)
        return HttpResponse(pro)
def create(req):
    if req.method=="POST":
        content=req.POST.get("content")
        logger.info("自动生成api用例的url为："+content)
        path=req.POST.get("path")or None
        logger.info("自动生成api用例的path为：" + content)
        opt=req.POST.get("opt")
        if (opt=="swagger"):
            api=swaggerapi.swaggerapi(content,path)
            html=api.gethtml()
            res=api.getinfo_bs(html)
        if (opt=="wiki"):
            api=wikiapi.getapi(content,path)
            api.login()
            html=api.gethtml()
            res=api.getinfo_bs(html)
            # res = api.getinfo_bs()
        logger.info(res)
        if 'error'in res:
            return HttpResponse(res['error'],status=502)
        return JsonResponse(res)
    return HttpResponse("ok")

def save(req):
    if req.method=="POST":
        title=req.POST.get('title').split("\n")
        logger.info ("title 信息为：%s"%title)
        method = req.POST.get('method').split("\n")
        logger.info("method 信息为：%s" %method)
        urls = req.POST.get('urlinfo').split("\n")
        logger.info("url 信息为：%s" %urls)
        param = req.POST.get('param').split("\n")
        logger.info("param 信息为：%s" %param)
        body = req.POST.get('body').split("\n")
        logger.info("body 信息为：%s" % param)
        project= req.POST.get('project')
        logger.info("project 信息为：%s" %project)
        ip = req.POST.get('ipinfo')
        logger.info("ip 信息为：%s" % ip)
        pro_id=models.Apiproject.objects.filter(name=project).values('id')[0]
        if len(title)==len(method)==len(urls)==len(param):
            try:
                for i in range(len(title)):
                    _num = models.ApiList.objects.filter(project_id=pro_id.get('id')).filter(name=title[i]).count()
                    if _num:
                        logger.error("接口%s已存在"%title[i])
                        continue
                        # return HttpResponse('名称重复！', status=502)
                    _url=urls[i].split("?")[0] #取消拼接的参数
                    if "http" not in _url:
                        _url="http://"+_url
                    if ip:
                        if ip.startswith("http"):
                            ip=ip[7:-1]
                        parsed_tuple = parse.urlparse(_url)
                        temp = list(parsed_tuple)
                        temp[1]=ip
                        url = parse.urlunparse(temp)
                    else:
                        url=_url
                    logger.info ('保存的url为：'+url)
                    obj=models.ApiList(name=title[i], url=url, type=method[i].upper(), header='',
                                         project_id=pro_id.get('id'))
                    obj.save()
            except Exception as e:
                logger.error(e)
                logger.error ('apilist新增失败')
                return HttpResponse(str(e), status=502)
            try:
                #如果接口已经添加，接口用例信息会多次添加
                for i in range(len(title)):
                    case_seqid =1
                    cname = models.ApiList.objects.filter(project_id=pro_id.get('id')).filter(name=title[i])[0]
                    if not body:
                        if method[i].lower()=='get':
                            par=param[i]
                            bd=''
                        else:
                            #判断url中是否包含参数
                            if "?" in urls[i]:
                                par = urls[i].split("?")[1]
                            else:
                                par=""
                            bd = param[i]
                        cobj=models.ApiCase(seqid=case_seqid, params=par, response='', cname=cname,
                                             restype='', body=bd)
                    else:
                        cobj = models.ApiCase(seqid=case_seqid, params=param[i], response='', cname=cname,
                                              restype='', body=body[i])
                    cobj.save()
            except Exception as e:
                logger.error(e)
                logger.error('apicase新增失败')
                return HttpResponse("apicase新增失败", status=502)

        else:
            return HttpResponse ("用例长度不一致，请修改",status=502)
    return HttpResponse("ok")

# 执行用例
def runcase(req):
    relist = []
    if req.method == 'GET':
        seqid = req.GET.get('seqid')
        id = req.GET.get('name')
        rtype = req.GET.get('type')
        project=req.GET.get('project')
        _pro = models.Apiproject.objects.filter(name=project).values('id')
        pid = [i['id'] for i in _pro][0]
        logger.info("调试类型为%s，序号为%s，编号为%s，project为%s" % (rtype,seqid, id, project))
        common = {}
        procomm = {}
        _common = models.Apicommon.objects.filter(project=0)
        for i in _common:
            common[i.key] = i.value
        _procomm = models.Apicommon.objects.filter(project=pid)
        for i in _procomm:
            procomm[i.key] = i.value
        re = RUN(id, rtype, seqid,common=common,procomm=procomm)
        re.runtest(relist)
    else:
        number = int(req.POST.get('number'))
        data=req.POST.get('data')
        project=req.POST.get('project')
        _pro = models.Apiproject.objects.filter(name=project).values('id')
        pid = [i['id'] for i in _pro][0]
        logger.info("调试用例获取的project为%s，data为%s，number为%s"%(project,data,number))
        common={}
        procomm={}
        _common=models.Apicommon.objects.filter(project=0)
        for i in _common:
            common[i.key]=i.value
        _procomm=models.Apicommon.objects.filter(project=pid)
        for i in _procomm:
            procomm[i.key]=i.value
        for i in range(0, number):
            id = req.POST.get('data[%d][id]' % i)
            re = RUN(id,common=common,procomm=procomm)
            re.runtest(relist)
    logger.info("用例返回结果为%s"%relist)
    # for i in relist:
    if len(relist)==0:
        relist=[{'name': '调试失败', 'result': '用例没有添加详细用例信息，请添加'}]
    return HttpResponse(json.dumps(relist), content_type="application/json")


def runall(req):
    relist = []
    if req.method == 'POST':
        t_begin = time.time()
        cases = req.POST.get('cases')
        cases = json.loads(cases)
        project = req.POST.get('project')
        _pro = models.Apiproject.objects.filter(name=project).values('id')
        pid = [i['id'] for i in _pro][0]
        logger.info("运行用例获取的project为%s，case为%s" % (project,cases))
        commoninfo = {}
        procomm = {}
        _common = models.Apicommon.objects.filter(project=0)
        for i in _common:
            commoninfo[i.key] = i.value
        _procomm = models.Apicommon.objects.filter(project=pid)
        for i in _procomm:
            procomm[i.key] = i.value
        for ca in cases:
            id = ca['id']
            re = RUN(id,common=commoninfo,procomm=procomm)
            re.runtest(relist)
        t_end = time.time()
        now = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime(t_begin))
        filename = os.path.join(settings.RESULT_DIRS + "\\result" + now + ".html")
        # logger.info("用例生成的文件名为%s"%filename)
        logger.info("执行用例的结果为%s"%relist)
        fp = open(filename, 'wb')
        res = htmlreport.result(results=relist, t_begin=t_begin,t_end=t_end, stream=fp,title=project+"-API自动化测试报告")
        res.generatereport()
        fp.close()
        return HttpResponseRedirect(settings.RESULT_URL + os.path.basename(filename))
    if req.method == 'GET':
        project = req.GET.get('project')
        isdd = req.GET.get('isdd')
        _pro = models.Apiproject.objects.filter(name=project).values('id')
        pid = [i['id'] for i in _pro][0]
        logger.info("运行用例获取的project为%s" % (project))
        commoninfo = {}
        procomm = {}
        _common = models.Apicommon.objects.filter(project=0)
        for i in _common:
            commoninfo[i.key] = i.value
        _procomm = models.Apicommon.objects.filter(project=pid)
        for i in _procomm:
            procomm[i.key] = i.value
        logger.info("项目%s运行用例" % project)
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        lockfilepath = os.path.join(path, "api", "logs", project + "-lock.txt")
        if os.path.exists(lockfilepath):
            return HttpResponse("脚本正在运行中，请稍后再运行")
        else:
            filename=""
            try:
                lockfile = open(lockfilepath, 'w+')
                lockfile.close()
                filename = ""
                fail=[]
                allnum=""
                now = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime(time.time()))
                t_begin = time.time()
                cases = models.ApiList.objects.filter(project_id=pid)
                for ca in cases:
                    id = ca.id
                    re = RUN(id,common=commoninfo,procomm=procomm)
                    re.runtest(relist)
                allnum=len(relist)
                fail = [x for x in relist if x['result'] == 'fail']
                t_end = time.time()
                run_time = t_end - t_begin
                filename = os.path.join(settings.RESULT_DIRS + "\\result" + now + ".html")
                # logger.info("用例生成的文件名为%s" % filename)
                logger.info("执行用例的结果为%s" % relist)
                fp = open(filename, 'wb')
                res = htmlreport.result(results=relist, time=run_time, stream=fp,title=project+"-API自动化测试报告")
                res.generatereport()
            except Exception as e:
                logger.error(e)
            finally:
                try:
                    os.remove(lockfilepath)
                except Exception as e:
                    logger.error(e)
            if filename != "":
                msgUrl = "http://%s:8899/api/result/result%s.html" % (common.getip(), now)
                if isdd:
                    rb = robot.Robot()
                    rb.sendlink('【%s】API自动化' % project, '点击查看结果', msgUrl)
                    if fail:
                        num=len(fail)
                        err=''
                        for i in fail:
                            err += '用例名：%s，用例编号：%s\n' % (i["name"], i["seqid"])
                        rb.sendtext('项目【%s】共运行%s条用例，其中失败%s条,失败用例详情如下：\n%s' % (project,allnum,num,err))
                    else:
                        rb.sendtext('项目【%s】共运行%s条用例，用例运行通过'%(project,allnum))
                return HttpResponse("脚本已运行完成，结果请查看地址：【%s】" % msgUrl)
            else:
                if isdd:
                    rb = robot.Robot()
                    rb.sendtext('【%s】API自动化脚本运行失败' % project)
                return HttpResponse("脚本运行失败")
