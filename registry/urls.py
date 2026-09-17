# -*- coding: utf-8 -*-
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'registry'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Shaxslar
    path('shaxslar/', views.ShaxsListView.as_view(), name='shaxs_list'),
    path('shaxslar/yangi/', views.ShaxsCreateView.as_view(), name='shaxs_create'),
    path('shaxslar/<int:pk>/', views.ShaxsDetailView.as_view(), name='shaxs_detail'),
    path(
        'shaxslar/<int:pk>/tahrirlash/',
        views.ShaxsUpdateView.as_view(), name='shaxs_update',
    ),
    path(
        'shaxslar/<int:pk>/ochirish/',
        views.ShaxsDeleteView.as_view(), name='shaxs_delete',
    ),

    # Mahallalar
    path('mahallalar/', views.MahallaListView.as_view(), name='mahalla_list'),
    path(
        'mahallalar/<int:pk>/',
        views.MahallaDetailView.as_view(), name='mahalla_detail',
    ),
    path(
        'mahallalar/<int:pk>/tahrirlash/',
        views.MahallaUpdateView.as_view(), name='mahalla_update',
    ),

    # Ma'lumotnoma jadvallari (hudud, mahalla, oila, lug'atlar) - umumiy CRUD
    path(
        'malumotnoma/',
        views.MalumotnomaIndexView.as_view(), name='malumotnoma',
    ),
    path(
        'malumotnoma/<slug:kalit>/',
        views.JadvalListView.as_view(), name='jadval_list',
    ),
    path(
        'malumotnoma/<slug:kalit>/yangi/',
        views.JadvalCreateView.as_view(), name='jadval_create',
    ),
    path(
        'malumotnoma/<slug:kalit>/<int:pk>/tahrirlash/',
        views.JadvalUpdateView.as_view(), name='jadval_update',
    ),
    path(
        'malumotnoma/<slug:kalit>/<int:pk>/ochirish/',
        views.JadvalDeleteView.as_view(), name='jadval_delete',
    ),

    # Forma uchun yordamchi so'rov (mahalla -> oilalar)
    path('api/oilalar/', views.OilaTanlovView.as_view(), name='oila_tanlov'),

    # Tizimga kirish/chiqish
    path(
        'kirish/',
        auth_views.LoginView.as_view(
            template_name='registry/login.html', redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('chiqish/', auth_views.LogoutView.as_view(), name='logout'),
]
