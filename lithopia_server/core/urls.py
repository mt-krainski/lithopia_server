from django.urls import path

from . import views

urlpatterns = [
    path('', views.summary, name='summary'),
    path('<int:id>', views.summary, name='summary_by_id'),
    path('get_image/<str:name>', views.get_image, name='get_image')
]