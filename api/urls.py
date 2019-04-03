from django.conf import settings
from django.conf.urls import url
from django.views.static import serve
from django.conf import settings
from . import views

urlpatterns = [
    # ex: /sixin/
    url(r'^$', views.index, name='index'),
    url(r'^caselist$', views.caselist, name='caselist'),
    url(r'^getlist$', views.getlist, name='getlist'),
    url(r'^api$', views.api, name='api'),
    url(r'^case$', views.case, name='case'),
    url(r'^param$', views.param, name='param'),
    url(r'^postcon$', views.postcon, name='postcon'),
    url(r'^runcase$', views.runcase, name='runcase'),
    url(r'^runall$', views.runall, name='runall'),
    # url(r'^test$', views.test, name='test'),
    url(r'^project$', views.project, name='project'),
    url(r'^common$', views.commonpara, name='common'),
    url(r'^result/(?P<path>.*)$', serve, {'document_root': settings.RESULT_DIRS}),
    url(r'^log/(?P<path>.*)$', serve, {'document_root': settings.LOGS}),
    url(r'^generate$', views.generate, name='generate'),
    url(r'^create', views.create, name='create'),
    url(r'^save$',views.save,name='save'),
]
