from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('sentinel_credentials', views.sentinel_credentials, name='sentinel_credentials'),
    path('update_sentinel_credentials', views.update_sentinel_credentials, name='update_sentinel_credentials'),
]