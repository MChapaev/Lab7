from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_record, name='create'),
    path('delete/', views.delete_client, name='delete'),
    path('view/', views.view_records, name='view'),
    path('update/', views.update_user, name='update'),
]