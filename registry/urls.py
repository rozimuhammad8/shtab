from django.urls import path

from . import views

app_name = 'registry'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('shaxslar/', views.ShaxsListView.as_view(), name='shaxs_list'),
    path('shaxslar/<int:pk>/', views.ShaxsDetailView.as_view(), name='shaxs_detail'),
    path('mahallalar/', views.MahallaListView.as_view(), name='mahalla_list'),
    path('mahallalar/<int:pk>/', views.MahallaDetailView.as_view(), name='mahalla_detail'),
]
