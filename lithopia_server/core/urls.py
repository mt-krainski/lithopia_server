from django.urls import path

from . import views

urlpatterns = [
    path('', views.summary, name='summary'),
    path('<int:id>', views.summary, name='summary_by_id'),
    path('get_image/<str:name>', views.get_image, name='get_image'),
    path('histogram/<str:name>', views.get_histogram, name='histogram'),
    path('histogram_metrics/<str:name>', views.get_histogram_metrics, name='hist_metrics'),
    path('create_reference', views.create_reference, name='create_reference'),
    path('diff_image/<str:name>', views.get_diff_image, name='diff_image')
]
