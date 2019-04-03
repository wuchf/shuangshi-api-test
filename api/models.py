from django.db import models


# Create your models here.
class Apiproject(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class ApiList(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200)
    type = models.CharField(max_length=10)
    header = models.CharField(max_length=2000, default="")
    project = models.ForeignKey(Apiproject, on_delete=models.CASCADE)


class ApiCase(models.Model):
    id = models.AutoField(primary_key=True)
    seqid = models.IntegerField()
    cname = models.ForeignKey(ApiList, on_delete=models.CASCADE)
    params = models.CharField(max_length=500, default='')
    body = models.CharField(max_length=2000, null=True)
    restype = models.CharField(max_length=100)
    response = models.CharField(max_length=500)
    name = models.CharField(max_length=100, null=True)
    re = models.CharField(max_length=500, null=True)


class ApiParam(models.Model):
    id = models.AutoField(primary_key=True)
    seqid = models.IntegerField()
    cname = models.ForeignKey(ApiList, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200)
    type = models.CharField(max_length=100)
    header=models.CharField(max_length=2000,default="")
    params = models.CharField(max_length=500)
    body = models.CharField(max_length=2000, null=True)
    re = models.CharField(max_length=500)


class ApiPostcon(models.Model):
    id = models.AutoField(primary_key=True)
    seqid = models.IntegerField()
    cname = models.ForeignKey(ApiList, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200, null=True)
    type = models.CharField(max_length=100)
    header = models.CharField(max_length=2000,default="")
    params = models.CharField(max_length=500, null=True)
    body = models.CharField(max_length=2000, null=True)
    time = models.CharField(max_length=5, null=True)

class Apicommon(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    project = models.IntegerField()