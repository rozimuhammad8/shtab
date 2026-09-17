# -*- coding: utf-8 -*-
"""
Tahrirlash formalari.

Barcha `<select>` maydonlariga `data-select` atributi qo'yiladi - `ui.js`
shu atribut bo'yicha ularni iOS uslubidagi maxsus ochiluvchi ro'yxatga
aylantiradi. `data-label` esa tugmaning chap tomonida turadigan doimiy
yorliqni beradi (faqat filtr panelida ishlatiladi).
"""
from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory
from django.urls import reverse

from .models import (
    Hudud, IjtimoiyHolatTuri, IjtimoiyToifa, Mahalla, MuammoToifasi,
    MurojaatSababi, Oila, Shaxs, Xizmat, XizmatTuri,
)


class SanaInput(forms.DateInput):
    """Brauzerning o'z sana tanlagichi ishlatiladi."""

    input_type = 'date'

    def __init__(self, attrs=None):
        super().__init__(attrs={'class': 'input', **(attrs or {})}, format='%Y-%m-%d')


# ===========================================================================
# Shaxs formasi
# ===========================================================================

class ShaxsForm(forms.ModelForm):
    """Shaxs yozuvini qo'shish va tahrirlash formasi."""

    class Meta:
        model = Shaxs
        fields = [
            'fio', 'jshshir', 'jinsi', 'tugilgan_sana', 'yoshi',
            'mahalla', 'oila', 'asosiy_arizachi',
            'ijtimoiy_toifa', 'muammo_toifasi', 'reestrdan_chiqqan',
            'uchrashuv_sana', 'uchrashuvda_qatnashgan',
            'xizmat_sana', 'xizmat_korsatilgan',
            'murojaat_sababi', 'murojaat_izohi',
            'ijtimoiy_holatlar',
            'muammo_aniqlanmagan',
        ]
        widgets = {
            'fio': forms.TextInput(attrs={
                'placeholder': 'FAMILIYA ISM OTASINING ISMI',
                'autocomplete': 'off',
            }),
            'jshshir': forms.TextInput(attrs={
                'placeholder': '14 xonali raqam',
                'inputmode': 'numeric',
                'maxlength': '14',
                'autocomplete': 'off',
            }),
            'jinsi': forms.Select(attrs={'data-select': ''}),
            'tugilgan_sana': SanaInput(),
            'yoshi': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '120'}),
            'mahalla': forms.Select(attrs={'data-select': ''}),
            'oila': forms.Select(attrs={'data-select': ''}),
            'ijtimoiy_toifa': forms.Select(attrs={'data-select': ''}),
            'muammo_toifasi': forms.Select(attrs={'data-select': ''}),
            'murojaat_sababi': forms.Select(attrs={'data-select': ''}),
            'murojaat_izohi': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "Fuqaro nima so'ragan (masalan: uy-joy ta'miri)",
            }),
            'uchrashuv_sana': SanaInput(),
            'xizmat_sana': SanaInput(),
            'ijtimoiy_holatlar': forms.SelectMultiple(attrs={
                'data-select': '',
                'data-placeholder': 'Belgi tanlanmagan',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bo'sh tanlov matnlari o'zbekchada bo'lsin.
        self.fields['jinsi'].choices = [('', '— Tanlanmagan —')] + list(
            Shaxs.JINSI_TANLOVLARI
        )
        self.fields['ijtimoiy_toifa'].empty_label = '— Toifa tanlanmagan —'
        self.fields['muammo_toifasi'].empty_label = '— Izoh tanlanmagan —'
        self.fields['murojaat_sababi'].empty_label = '— Sabab tanlanmagan —'

        # Querysetlar aniq belgilanadi (ortiqcha so'rovlar bo'lmasligi uchun).
        self.fields['mahalla'].queryset = Mahalla.objects.select_related('hudud')
        self.fields['ijtimoiy_toifa'].queryset = IjtimoiyToifa.objects.all()
        self.fields['muammo_toifasi'].queryset = MuammoToifasi.objects.all()
        self.fields['ijtimoiy_holatlar'].queryset = IjtimoiyHolatTuri.objects.order_by(
            'tartib'
        )

        # Faqat faol sabablar ko'rinadi; joriy yozuvda tanlangan sabab
        # nofaol qilingan bo'lsa ham ro'yxatda qoladi (yo'qolib qolmasligi uchun).
        shart = Q(faol=True)
        if self.instance.pk and self.instance.murojaat_sababi_id:
            shart |= Q(pk=self.instance.murojaat_sababi_id)
        self.fields['murojaat_sababi'].queryset = MurojaatSababi.objects.filter(shart)

        # 4 000 dan ortiq oila bor - ro'yxatni joriy shaxsning mahallasi bilan
        # cheklaymiz, aks holda ochiluvchi ro'yxat ishlatib bo'lmas holga keladi.
        mahalla_id = (
            self.data.get(self.add_prefix('mahalla'))
            or (self.instance.mahalla_id if self.instance.pk else None)
            or self.initial.get('mahalla')
        )
        oila_qs = Oila.objects.select_related('mahalla')
        if mahalla_id:
            oila_qs = oila_qs.filter(mahalla_id=mahalla_id)
        elif not self.instance.pk:
            oila_qs = Oila.objects.none()
        self.fields['oila'].queryset = oila_qs
        self.fields['oila'].empty_label = '— Oila tanlanmagan —'
        self.fields['oila'].help_text = (
            "Ro'yxatda tanlangan mahalladagi oilalar ko'rinadi - "
            "mahallani o'zgartirsangiz, ro'yxat avtomatik yangilanadi."
        )
        # Mahalla o'zgarganda `ui.js` shu manzildan yangi oilalar ro'yxatini oladi.
        self.fields['mahalla'].widget.attrs['data-oila-manba'] = reverse(
            'registry:oila_tanlov'
        )

        self.fields['ijtimoiy_holatlar'].help_text = (
            "Bir nechta belgini tanlash mumkin"
        )

    def clean_jshshir(self):
        """JSHSHIR faqat 14 xonali raqam bo'lishi mumkin (yoki bo'sh)."""
        qiymat = (self.cleaned_data.get('jshshir') or '').strip()
        if not qiymat:
            return ''
        if not qiymat.isdigit() or len(qiymat) != 14:
            raise forms.ValidationError(
                "JSHSHIR 14 xonali raqamdan iborat bo'lishi kerak."
            )
        return qiymat

    def clean(self):
        tozalangan = super().clean()
        oila = tozalangan.get('oila')
        mahalla = tozalangan.get('mahalla')

        # Oila boshqa mahallada bo'lsa - bu ma'lumotni buzadi.
        if oila and mahalla and oila.mahalla_id != mahalla.pk:
            self.add_error(
                'oila',
                f"Tanlangan oila «{oila.mahalla.nomi}» mahallasiga tegishli. "
                f"Mahalla va oila bir xil bo'lishi kerak.",
            )

        sana = tozalangan.get('tugilgan_sana')
        uchrashuv = tozalangan.get('uchrashuv_sana')
        if sana and uchrashuv and uchrashuv < sana:
            self.add_error(
                'uchrashuv_sana',
                "Uchrashuv sanasi tug'ilgan sanadan oldin bo'lishi mumkin emas.",
            )
        return tozalangan


class XizmatForm(forms.ModelForm):
    """Formset ichidagi bitta xizmat qatori."""

    class Meta:
        model = Xizmat
        fields = ['turi', 'holat', 'soni', 'summa_mln']
        widgets = {
            'turi': forms.Select(attrs={'data-select': ''}),
            'holat': forms.Select(attrs={'data-select': ''}),
            'soni': forms.NumberInput(attrs={'min': '1', 'step': '1'}),
            'summa_mln': forms.NumberInput(attrs={
                'step': '0.001', 'min': '0', 'placeholder': '0.000',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['turi'].queryset = XizmatTuri.objects.order_by('tartib')
        self.fields['turi'].empty_label = '— Xizmat turi —'
        self.fields['holat'].choices = [('', '— Holat —')] + list(
            Xizmat.HOLAT_TANLOVLARI
        )
        self.fields['soni'].required = False
        self.fields['summa_mln'].required = False

    def clean_soni(self):
        return self.cleaned_data.get('soni') or 1


XizmatFormSet = inlineformset_factory(
    Shaxs, Xizmat, form=XizmatForm, extra=0, can_delete=True,
)


# ===========================================================================
# Ma'lumotnoma (lug'at) jadvallari formalari
# ===========================================================================

class HududForm(forms.ModelForm):
    class Meta:
        model = Hudud
        fields = ['nomi', 'nomi_kiril']
        widgets = {
            'nomi': forms.TextInput(attrs={'placeholder': 'ANDIJON TUMANI'}),
            'nomi_kiril': forms.TextInput(attrs={'placeholder': 'АНДИЖОН ТУМАНИ'}),
        }


class MahallaForm(forms.ModelForm):
    """MFY nomini tahrirlash - lotin yozuvidagi nomni tuzatish uchun ham."""

    class Meta:
        model = Mahalla
        fields = ['nomi', 'kodi', 'hudud', 'nomi_kiril']
        widgets = {
            'nomi': forms.TextInput(attrs={'placeholder': "MFY nomi (lotin yozuvida)"}),
            'kodi': forms.NumberInput(attrs={'min': '1'}),
            'hudud': forms.Select(attrs={'data-select': ''}),
            'nomi_kiril': forms.TextInput(attrs={'placeholder': 'МФЙ номи'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nomi_kiril'].help_text = (
            "Manba fayldagi asl yozuv - solishtirish uchun saqlanadi."
        )
        self.fields['nomi'].help_text = (
            "Masalan «ИТТИФОК» uchun to'g'ri lotin yozuvi — «ITTIFOQ»."
        )


class OilaForm(forms.ModelForm):
    class Meta:
        model = Oila
        fields = ['unikal_id', 'mahalla', 'azolari_soni']
        widgets = {
            'unikal_id': forms.TextInput(attrs={
                'placeholder': '32049833', 'autocomplete': 'off',
            }),
            'mahalla': forms.Select(attrs={'data-select': ''}),
            'azolari_soni': forms.NumberInput(attrs={'min': '1', 'max': '30'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mahalla'].queryset = Mahalla.objects.select_related('hudud')
        self.fields['azolari_soni'].help_text = (
            "Ixtiyoriy - manba faylda ko'rsatilgan son."
        )


class IjtimoiyToifaForm(forms.ModelForm):
    class Meta:
        model = IjtimoiyToifa
        fields = ['nomi', 'nomi_kiril']
        widgets = {
            'nomi': forms.TextInput(attrs={'placeholder': "Kambag'al"}),
            'nomi_kiril': forms.TextInput(attrs={'placeholder': 'Камбағал'}),
        }


class MuammoToifasiForm(forms.ModelForm):
    class Meta:
        model = MuammoToifasi
        fields = ['nomi', 'nomi_kiril']
        widgets = {
            'nomi': forms.TextInput(attrs={'placeholder': 'Ishsiz yoki norasmiy band'}),
            'nomi_kiril': forms.TextInput(attrs={'placeholder': 'Ишсиз'}),
        }


class MurojaatSababiForm(forms.ModelForm):
    class Meta:
        model = MurojaatSababi
        fields = ['nomi', 'tavsifi', 'tartib', 'faol']
        widgets = {
            'nomi': forms.TextInput(attrs={
                'placeholder': "Ish bilan ta'minlash",
            }),
            'tavsifi': forms.TextInput(attrs={
                'placeholder': 'Ixtiyoriy qisqa tushuntirish',
            }),
            'tartib': forms.NumberInput(attrs={'min': '0', 'max': '999'}),
        }


class XizmatTuriForm(forms.ModelForm):
    class Meta:
        model = XizmatTuri
        fields = ['nomi', 'kod', 'ota_turi', 'summasi_bor', 'tartib', 'nomi_kiril']
        widgets = {
            'nomi': forms.TextInput(attrs={'placeholder': 'Doimiy ishga joylashtirish'}),
            'kod': forms.TextInput(attrs={'placeholder': 'doimiy_ish'}),
            'ota_turi': forms.Select(attrs={'data-select': ''}),
            'tartib': forms.NumberInput(attrs={'min': '0', 'max': '999'}),
            'nomi_kiril': forms.TextInput(attrs={'placeholder': 'Доимий ишга'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ota_turi'].empty_label = "— Yuqori tur yo'q —"
        qs = XizmatTuri.objects.order_by('tartib')
        if self.instance.pk:
            # O'zini o'ziga "ota" qilib qo'yishning oldi olinadi.
            qs = qs.exclude(pk=self.instance.pk)
        self.fields['ota_turi'].queryset = qs
        self.fields['kod'].help_text = (
            "Barqaror kod - import buyrug'i shu kod bo'yicha xizmat turini topadi. "
            "Mavjud turlarda o'zgartirmaslik tavsiya etiladi."
        )


class IjtimoiyHolatTuriForm(forms.ModelForm):
    class Meta:
        model = IjtimoiyHolatTuri
        fields = ['nomi', 'kod', 'tartib', 'nomi_kiril']
        widgets = {
            'nomi': forms.TextInput(attrs={'placeholder': 'Ish bilan band'}),
            'kod': forms.TextInput(attrs={'placeholder': 'ish_bilan_band'}),
            'tartib': forms.NumberInput(attrs={'min': '0', 'max': '999'}),
            'nomi_kiril': forms.TextInput(attrs={'placeholder': 'Иш билан банд'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kod'].help_text = (
            "Barqaror kod - import buyrug'i shu kod bo'yicha belgini topadi."
        )
