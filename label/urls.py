from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('micrograph', views.micrograph, name='micrograph'),
    path('average', views.average, name='average'),
    path('upload', views.upload, name='upload'),
]
