from django.contrib import admin

from .models import Mahalla, Oila, Shaxs


@admin.register(Mahalla)
class MahallaAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'hudud', 'kodi', 'shaxslar_soni')
    search_fields = ('nomi', 'hudud', 'kodi')


@admin.register(Oila)
class OilaAdmin(admin.ModelAdmin):
    list_display = ('oila_unikal_id', 'mahalla', 'oila_azolari_soni')
    list_filter = ('mahalla',)
    search_fields = ('oila_unikal_id',)


@admin.register(Shaxs)
class ShaxsAdmin(admin.ModelAdmin):
    list_display = (
        'fio', 'jshshir', 'jinsi', 'yoshi', 'ijtimoiy_toifa', 'oila',
        'uchrashuv_qatnashgan',
    )
    list_filter = ('jinsi', 'ijtimoiy_toifa', 'oila__mahalla', 'uchrashuv_qatnashgan')
    search_fields = ('fio', 'jshshir')
    date_hierarchy = 'uchrashuv_sana'
