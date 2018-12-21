from django.urls import path

from . import views

urlpatterns = [
    path('', views.acquisition_page, name='acquisition_page'),
]