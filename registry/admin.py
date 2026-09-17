# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db.models import Count

from .models import (
    Hudud, IjtimoiyHolatTuri, IjtimoiyToifa, Mahalla, MuammoToifasi,
    MurojaatSababi, Oila, Shaxs, ShaxsIjtimoiyHolat, Xizmat, XizmatTuri,
)


@admin.register(Hudud)
class HududAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'nomi_kiril', 'mahallalar_soni')
    search_fields = ('nomi', 'nomi_kiril')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_mahalla=Count('mahallalar'))

    @admin.display(description='Mahallalar soni', ordering='_mahalla')
    def mahallalar_soni(self, obj):
        return obj._mahalla


@admin.register(Mahalla)
class MahallaAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'kodi', 'hudud', 'nomi_kiril', 'shaxslar_soni')
    list_filter = ('hudud',)
    search_fields = ('nomi', 'nomi_kiril', 'kodi')
    list_select_related = ('hudud',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_shaxs=Count('shaxslar'))

    @admin.display(description='Shaxslar soni', ordering='_shaxs')
    def shaxslar_soni(self, obj):
        return obj._shaxs


@admin.register(Oila)
class OilaAdmin(admin.ModelAdmin):
    list_display = ('unikal_id', 'mahalla', 'azolari_soni')
    list_filter = ('mahalla__hudud',)
    search_fields = ('unikal_id',)
    list_select_related = ('mahalla',)
    autocomplete_fields = ('mahalla',)


class XizmatInline(admin.TabularInline):
    model = Xizmat
    extra = 0
    autocomplete_fields = ('turi',)


class IjtimoiyHolatInline(admin.TabularInline):
    model = ShaxsIjtimoiyHolat
    extra = 0
    autocomplete_fields = ('turi',)


@admin.register(Shaxs)
class ShaxsAdmin(admin.ModelAdmin):
    list_display = (
        'fio', 'jshshir', 'jinsi', 'yoshi', 'mahalla', 'ijtimoiy_toifa',
        'uchrashuvda_qatnashgan', 'xizmat_korsatilgan',
    )
    list_filter = (
        'jinsi', 'ijtimoiy_toifa', 'muammo_toifasi', 'murojaat_sababi',
        'uchrashuvda_qatnashgan', 'xizmat_korsatilgan', 'asosiy_arizachi',
        'reestrdan_chiqqan', 'takroriy_jshshir', 'mahalla__hudud',
    )
    search_fields = ('fio', 'fio_kiril', 'jshshir', 'oila__unikal_id')
    list_select_related = ('mahalla', 'oila', 'ijtimoiy_toifa')
    autocomplete_fields = (
        'oila', 'mahalla', 'ijtimoiy_toifa', 'muammo_toifasi', 'murojaat_sababi',
    )
    date_hierarchy = 'uchrashuv_sana'
    inlines = (XizmatInline, IjtimoiyHolatInline)
    readonly_fields = (
        'fio_kiril', 'tartib_raqami', 'kerakli_xizmatlar_soni',
        'korsatilgan_xizmatlar_soni', 'yaratilgan_vaqt', 'yangilangan_vaqt',
    )
    fieldsets = (
        ("Shaxsiy ma'lumotlar", {
            'fields': (
                'fio', 'fio_kiril', 'jshshir', 'jinsi', 'tugilgan_sana', 'yoshi',
            ),
        }),
        ('Manzil va oila', {
            'fields': ('mahalla', 'oila', 'asosiy_arizachi', 'tartib_raqami'),
        }),
        ('Ijtimoiy reestr', {
            'fields': ('ijtimoiy_toifa', 'muammo_toifasi', 'reestrdan_chiqqan'),
        }),
        ('Uchrashuv va xizmat', {
            'fields': (
                'uchrashuv_sana', 'uchrashuvda_qatnashgan',
                'xizmat_sana', 'xizmat_korsatilgan',
                'kerakli_xizmatlar_soni', 'korsatilgan_xizmatlar_soni',
            ),
        }),
        ('Murojaat', {
            'fields': ('murojaat_sababi', 'murojaat_izohi'),
        }),
        ('Muammo', {
            'fields': ('muammo_aniqlanmagan',),
        }),
        ('Tizim', {
            'classes': ('collapse',),
            'fields': ('yaratilgan_vaqt', 'yangilangan_vaqt'),
        }),
    )


@admin.register(XizmatTuri)
class XizmatTuriAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'kod', 'ota_turi', 'summasi_bor', 'tartib')
    list_filter = ('summasi_bor',)
    search_fields = ('nomi', 'nomi_kiril', 'kod')
    ordering = ('tartib',)


@admin.register(IjtimoiyHolatTuri)
class IjtimoiyHolatTuriAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'kod', 'tartib', 'shaxslar_soni')
    search_fields = ('nomi', 'nomi_kiril', 'kod')
    ordering = ('tartib',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_shaxs=Count('shaxslar'))

    @admin.display(description='Shaxslar soni', ordering='_shaxs')
    def shaxslar_soni(self, obj):
        return obj._shaxs


@admin.register(Xizmat)
class XizmatAdmin(admin.ModelAdmin):
    list_display = ('shaxs', 'turi', 'holat', 'soni', 'summa_mln')
    list_filter = ('holat', 'turi')
    search_fields = ('shaxs__fio', 'shaxs__jshshir')
    list_select_related = ('shaxs', 'turi')
    autocomplete_fields = ('shaxs', 'turi')


@admin.register(IjtimoiyToifa)
class IjtimoiyToifaAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'nomi_kiril', 'shaxslar_soni')
    search_fields = ('nomi', 'nomi_kiril')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_shaxs=Count('shaxslar'))

    @admin.display(description='Shaxslar soni', ordering='_shaxs')
    def shaxslar_soni(self, obj):
        return obj._shaxs


@admin.register(MuammoToifasi)
class MuammoToifasiAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'nomi_kiril', 'shaxslar_soni')
    search_fields = ('nomi', 'nomi_kiril')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_shaxs=Count('shaxslar'))

    @admin.display(description='Shaxslar soni', ordering='_shaxs')
    def shaxslar_soni(self, obj):
        return obj._shaxs


@admin.register(MurojaatSababi)
class MurojaatSababiAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'tavsifi', 'tartib', 'faol', 'shaxslar_soni')
    list_filter = ('faol',)
    search_fields = ('nomi', 'tavsifi')
    ordering = ('tartib', 'nomi')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_shaxs=Count('shaxslar'))

    @admin.display(description='Shaxslar soni', ordering='_shaxs')
    def shaxslar_soni(self, obj):
        return obj._shaxs
