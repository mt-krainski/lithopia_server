from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('quicklook', views.quicklook, name='quicklook'),
    path('download_latest', views.download_latest, name='download_latest'),
    path('download_status', views.download_status, name='download_status'),
]