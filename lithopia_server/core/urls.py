from django.urls import path

from . import views

urlpatterns = [
    path('', views.summary, name='summary'),
    path('<int:id>', views.summary, name='summary_by_id'),
    path('get_image/<str:name>', views.get_image, name='get_image'),
    path('special_image/<str:image_type>/<str:name>', views.get_special_image, name='special_image'),
    path('create_reference', views.create_reference, name='create_reference'),
    path('get_latest_entry_stamp', views.get_latest_entry_stamp, name='get_latest_entry_stamp'),
]
