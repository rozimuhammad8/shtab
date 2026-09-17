# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from .forms import MahallaForm, ShaxsForm, XizmatFormSet
from .malumotnoma import JADVALLAR, jadval_olish
from .models import (
    IjtimoiyHolatTuri, IjtimoiyToifa, Mahalla, MurojaatSababi, Oila, Shaxs,
    Xizmat, XizmatTuri,
)


class DashboardView(ListView):
    """Bosh sahifa: umumiy statistika va mahallalar bo'yicha taqsimot."""

    template_name = 'registry/dashboard.html'
    context_object_name = 'mahallalar'
    extra_context = {'bolim': 'dashboard'}

    def get_queryset(self):
        return (
            Mahalla.objects
            .annotate(shaxslar_soni_ann=Count('shaxslar'))
            .order_by('-shaxslar_soni_ann')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['jami_shaxslar'] = Shaxs.objects.count()
        ctx['jami_oilalar'] = Oila.objects.count()
        ctx['jami_mahallalar'] = Mahalla.objects.count()
        ctx['uchrashuvda_qatnashgan'] = Shaxs.objects.filter(
            uchrashuvda_qatnashgan=True
        ).count()
        ctx['xizmat_korsatilgan'] = Shaxs.objects.filter(
            xizmat_korsatilgan=True
        ).count()
        ctx['toifalar'] = (
            IjtimoiyToifa.objects
            .annotate(soni=Count('shaxslar'))
            .order_by('-soni')
        )
        ctx['ijtimoiy_holatlar'] = (
            IjtimoiyHolatTuri.objects
            .annotate(soni=Count('shaxslar'))
            .filter(soni__gt=0)
            .order_by('-soni')
        )
        ctx['xizmat_yigindisi'] = (
            XizmatTuri.objects
            .annotate(
                kerakli=Count('xizmatlar', filter=Q(xizmatlar__holat=Xizmat.KERAKLI)),
                korsatilgan=Count(
                    'xizmatlar', filter=Q(xizmatlar__holat=Xizmat.KORSATILGAN),
                ),
                summa=Sum(
                    'xizmatlar__summa_mln',
                    filter=Q(xizmatlar__holat=Xizmat.KORSATILGAN),
                ),
            )
            .order_by('tartib')
        )
        return ctx


class ShaxsListView(ListView):
    """Qidiruv va filtrlash imkoniyatli shaxslar ro'yxati."""

    model = Shaxs
    template_name = 'registry/shaxs_list.html'
    context_object_name = 'shaxslar'
    extra_context = {'bolim': 'shaxslar'}
    paginate_by = getattr(settings, 'PAGE_SIZE', 25)

    def get_queryset(self):
        qs = Shaxs.objects.select_related(
            'mahalla', 'oila', 'ijtimoiy_toifa', 'murojaat_sababi',
        )

        soragi = self.request.GET
        q = soragi.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(fio__icontains=q)
                | Q(jshshir__icontains=q)
                | Q(oila__unikal_id__icontains=q)
            )

        if mahalla_id := soragi.get('mahalla'):
            qs = qs.filter(mahalla_id=mahalla_id)
        if toifa_id := soragi.get('toifa'):
            qs = qs.filter(ijtimoiy_toifa_id=toifa_id)
        if jinsi := soragi.get('jinsi'):
            qs = qs.filter(jinsi=jinsi)
        if holat_id := soragi.get('holat'):
            qs = qs.filter(ijtimoiy_holatlari__turi_id=holat_id)
        if sabab_id := soragi.get('sabab'):
            qs = qs.filter(murojaat_sababi_id=sabab_id)
        if soragi.get('uchrashuv') == '1':
            qs = qs.filter(uchrashuvda_qatnashgan=True)
        if soragi.get('xizmat') == '1':
            qs = qs.filter(xizmat_korsatilgan=True)

        return qs.order_by('fio')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['mahallalar'] = Mahalla.objects.order_by('nomi')
        ctx['toifalar'] = IjtimoiyToifa.objects.order_by('nomi')
        ctx['ijtimoiy_holatlar'] = IjtimoiyHolatTuri.objects.order_by('nomi')
        ctx['murojaat_sabablari'] = MurojaatSababi.objects.all()
        ctx['jinslar'] = Shaxs.JINSI_TANLOVLARI
        ctx['soragi'] = self.request.GET
        # Sahifalash havolalarida `page` dan tashqari barcha filtrlar saqlanadi.
        parametrlar = self.request.GET.copy()
        parametrlar.pop('page', None)
        ctx['filtr_qatori'] = parametrlar.urlencode()
        return ctx


class ShaxsDetailView(DetailView):
    model = Shaxs
    template_name = 'registry/shaxs_detail.html'
    context_object_name = 'shaxs'
    extra_context = {'bolim': 'shaxslar'}

    def get_queryset(self):
        return Shaxs.objects.select_related(
            'mahalla', 'mahalla__hudud', 'oila', 'ijtimoiy_toifa',
            'muammo_toifasi', 'murojaat_sababi',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        xizmatlar = self.object.xizmatlar.select_related('turi').order_by(
            'turi__tartib'
        )
        ctx['kerakli_xizmatlar'] = [
            x for x in xizmatlar if x.holat == Xizmat.KERAKLI
        ]
        ctx['korsatilgan_xizmatlar'] = [
            x for x in xizmatlar if x.holat == Xizmat.KORSATILGAN
        ]
        ctx['ijtimoiy_holatlar'] = self.object.ijtimoiy_holatlari.select_related(
            'turi'
        ).order_by('turi__tartib')
        ctx['oila_azolari'] = (
            self.object.oila.azolar
            .exclude(pk=self.object.pk)
            .order_by('-asosiy_arizachi', 'tartib_raqami')
        )
        return ctx


class MahallaListView(ListView):
    model = Mahalla
    template_name = 'registry/mahalla_list.html'
    context_object_name = 'mahallalar'
    extra_context = {'bolim': 'mahallalar'}

    def get_queryset(self):
        return (
            Mahalla.objects
            .select_related('hudud')
            .annotate(
                shaxslar_soni_ann=Count('shaxslar', distinct=True),
                oilalar_soni_ann=Count('oilalar', distinct=True),
            )
            .order_by('nomi')
        )


class MahallaDetailView(DetailView):
    model = Mahalla
    template_name = 'registry/mahalla_detail.html'
    context_object_name = 'mahalla'
    extra_context = {'bolim': 'mahallalar'}

    def get_queryset(self):
        return Mahalla.objects.select_related('hudud')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        shaxslar = self.object.shaxslar.select_related('oila', 'ijtimoiy_toifa')
        ctx['shaxslar'] = shaxslar.order_by('fio')
        ctx['oilalar_soni'] = self.object.oilalar.count()
        ctx['toifalar'] = (
            IjtimoiyToifa.objects
            .filter(shaxslar__mahalla=self.object)
            .annotate(soni=Count('shaxslar'))
            .order_by('-soni')
        )
        return ctx


# ==========================================================================
# Tahrirlash (CRUD) ko'rinishlari
#
# Bazada F.I.O., JSHSHIR va ijtimoiy holat kabi maxfiy ma'lumotlar bor,
# shu sababli o'zgartirish faqat tizimga kirgan foydalanuvchiga ruxsat etiladi.
# ==========================================================================


class ShaxsFormMixin:
    """`Shaxs` formasi va unga tegishli xizmatlar formsetini birga boshqaradi."""

    model = Shaxs
    form_class = ShaxsForm
    template_name = 'registry/shaxs_form.html'
    extra_context = {'bolim': 'shaxslar'}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if 'xizmatlar' not in ctx:
            ctx['xizmatlar'] = self._formset()
        return ctx

    def _formset(self, bogla=False):
        kwargs = {'instance': self.object}
        if bogla:
            kwargs.update(data=self.request.POST)
        return XizmatFormSet(**kwargs)

    def form_valid(self, form):
        formset = XizmatFormSet(self.request.POST, instance=form.instance)
        # Shaxs hali saqlanmagan bo'lsa ham formsetni tekshirib olamiz, shunda
        # xatolar bir vaqtda ko'rsatiladi.
        if not formset.is_valid():
            return self.render_to_response(
                self.get_context_data(form=form, xizmatlar=formset)
            )

        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

        messages.success(self.request, self.muvaffaqiyat_xabari % self.object.fio)
        return super(ShaxsFormMixin, self).form_valid(form)

    def form_invalid(self, form):
        formset = XizmatFormSet(self.request.POST, instance=form.instance)
        formset.is_valid()   # xatolarni to'plash uchun
        messages.error(self.request, "Formada xatolar bor - quyida ko'rsatilgan.")
        return self.render_to_response(
            self.get_context_data(form=form, xizmatlar=formset)
        )

    def get_success_url(self):
        return reverse('registry:shaxs_detail', args=[self.object.pk])


class ShaxsCreateView(LoginRequiredMixin, ShaxsFormMixin, CreateView):
    muvaffaqiyat_xabari = "«%s» bazaga qo'shildi."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sarlavha'] = "Yangi shaxs qo'shish"
        ctx['tugma_matni'] = "Qo'shish"
        return ctx

    def _formset(self, bogla=False):
        # `CreateView` da `self.object` hali `None`.
        return XizmatFormSet(
            **({'data': self.request.POST} if bogla else {})
        )


class ShaxsUpdateView(LoginRequiredMixin, ShaxsFormMixin, UpdateView):
    muvaffaqiyat_xabari = "«%s» yozuvi saqlandi."

    def get_queryset(self):
        return Shaxs.objects.select_related('mahalla', 'oila')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sarlavha'] = "Yozuvni tahrirlash"
        ctx['tugma_matni'] = "Saqlash"
        return ctx


class ShaxsDeleteView(LoginRequiredMixin, DeleteView):
    model = Shaxs
    template_name = 'registry/shaxs_confirm_delete.html'
    context_object_name = 'shaxs'
    extra_context = {'bolim': 'shaxslar'}
    success_url = reverse_lazy('registry:shaxs_list')

    def get_queryset(self):
        return Shaxs.objects.select_related('mahalla', 'oila')

    def form_valid(self, form):
        messages.success(self.request, f"«{self.object.fio}» yozuvi o'chirildi.")
        return super().form_valid(form)


class MahallaUpdateView(LoginRequiredMixin, UpdateView):
    """MFY nomini tuzatish (manba fayldagi nomlar to'liq to'g'ri emas)."""

    model = Mahalla
    form_class = MahallaForm
    template_name = 'registry/mahalla_form.html'
    context_object_name = 'mahalla'
    extra_context = {'bolim': 'mahallalar'}

    def form_valid(self, form):
        javob = super().form_valid(form)
        messages.success(self.request, f"«{self.object.nomi}» saqlandi.")
        return javob

    def get_success_url(self):
        return reverse('registry:mahalla_detail', args=[self.object.pk])


class OilaTanlovView(LoginRequiredMixin, View):
    """Tanlangan mahalladagi oilalar ro'yxatini JSON ko'rinishida qaytaradi.

    Tahrirlash formasida mahalla o'zgartirilganda oilalar ochiluvchi ro'yxati
    sahifani qayta yuklamasdan yangilanadi (`ui.js` ishlatadi).
    """

    def get(self, request):
        mahalla_id = request.GET.get('mahalla')
        if not mahalla_id:
            return JsonResponse({'oilalar': []})
        oilalar = (
            Oila.objects
            .filter(mahalla_id=mahalla_id)
            .order_by('unikal_id')
            .values('id', 'unikal_id', 'azolari_soni')
        )
        return JsonResponse({'oilalar': [
            {
                'id': o['id'],
                'matn': "Oila #{}{}".format(
                    o['unikal_id'],
                    f" ({o['azolari_soni']} a'zo)" if o['azolari_soni'] else '',
                ),
            }
            for o in oilalar
        ]})


# ==========================================================================
# Ma'lumotnoma (lug'at) jadvallari uchun umumiy CRUD
#
# `malumotnoma.JADVALLAR` ro'yxatidagi har bir jadval uchun bir xil
# ro'yxat/qo'shish/tahrirlash/o'chirish sahifalari ishlatiladi.
# ==========================================================================


class JadvalMixin(LoginRequiredMixin):
    """URL dagi `kalit` bo'yicha jadval sozlamasini topadi."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.jadval = jadval_olish(kwargs.get('kalit'))

    def dispatch(self, request, *args, **kwargs):
        if self.jadval is None:
            raise Http404("Bunday ma'lumotnoma jadvali yo'q")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.jadval.queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['jadval'] = self.jadval
        ctx['bolim'] = 'malumotnoma'
        return ctx


class JadvalFormMixin(JadvalMixin):
    """Qo'shish/tahrirlash uchun - jadvalning ModelForm'ini beradi.

    `JadvalDeleteView` bu mixinni ishlatmaydi: `DeleteView` tasdiqlash uchun
    bo'sh `Form` dan foydalanadi, ModelForm esa bo'sh POST'da yaroqsiz bo'lib
    o'chirishni to'sib qo'yadi.
    """

    def get_form_class(self):
        return self.jadval.form


class MalumotnomaIndexView(LoginRequiredMixin, TemplateView):
    """Barcha ma'lumotnoma jadvallari ro'yxati (yozuvlar soni bilan)."""

    template_name = 'registry/malumotnoma_index.html'
    extra_context = {'bolim': 'malumotnoma'}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['jadvallar'] = [
            {'jadval': j, 'soni': j.model.objects.count()} for j in JADVALLAR
        ]
        ctx['shaxslar_soni'] = Shaxs.objects.count()
        return ctx


class JadvalListView(JadvalMixin, ListView):
    template_name = 'registry/malumotnoma_list.html'
    context_object_name = 'qatorlar'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q and self.jadval.qidiruv:
            shart = Q()
            for maydon in self.jadval.qidiruv:
                shart |= Q(**{f'{maydon}__icontains': q})
            qs = qs.filter(shart)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['soragi'] = self.request.GET
        parametrlar = self.request.GET.copy()
        parametrlar.pop('page', None)
        ctx['filtr_qatori'] = parametrlar.urlencode()
        return ctx


class JadvalCreateView(JadvalFormMixin, CreateView):
    template_name = 'registry/malumotnoma_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sarlavha'] = f"Yangi: {self.jadval.birlik.lower()}"
        ctx['tugma_matni'] = "Qo'shish"
        return ctx

    def form_valid(self, form):
        javob = super().form_valid(form)
        messages.success(self.request, f"«{self.object}» qo'shildi.")
        return javob

    def get_success_url(self):
        return reverse('registry:jadval_list', args=[self.jadval.kalit])


class JadvalUpdateView(JadvalFormMixin, UpdateView):
    template_name = 'registry/malumotnoma_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sarlavha'] = f"Tahrirlash: {self.jadval.birlik.lower()}"
        ctx['tugma_matni'] = 'Saqlash'
        return ctx

    def form_valid(self, form):
        javob = super().form_valid(form)
        messages.success(self.request, f"«{self.object}» saqlandi.")
        return javob

    def get_success_url(self):
        return reverse('registry:jadval_list', args=[self.jadval.kalit])


class JadvalDeleteView(JadvalMixin, DeleteView):
    template_name = 'registry/malumotnoma_confirm_delete.html'
    context_object_name = 'obyekt'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # O'chirishdan oldin bog'liq yozuvlar sonini ko'rsatamiz.
        bogliqlar = []
        for rel in self.object._meta.related_objects:
            # Teskari ko'p-ko'p bog'lanishlar o'tish jadvali orqali allaqachon
            # hisobga olinadi va ularda `on_delete` bo'lmaydi.
            if rel.many_to_many:
                continue
            nomi = rel.get_accessor_name()
            menejer = getattr(self.object, nomi, None)
            if menejer is None or not hasattr(menejer, 'count'):
                continue
            soni = menejer.count()
            if soni:
                bogliqlar.append({
                    'nomi': rel.related_model._meta.verbose_name_plural,
                    'soni': soni,
                    'kaskad': getattr(rel.on_delete, '__name__', '') == 'CASCADE',
                })
        ctx['bogliqlar'] = bogliqlar
        return ctx

    def form_valid(self, form):
        nomi = str(self.object)
        try:
            javob = super().form_valid(form)
        except ProtectedError:
            # Masalan, ishlatilayotgan ijtimoiy toifani o'chirish mumkin emas.
            messages.error(
                self.request,
                f"«{nomi}» o'chirilmadi: unga bog'langan yozuvlar bor. "
                f"Avval o'sha yozuvlarda boshqa qiymat tanlang.",
            )
            return redirect('registry:jadval_list', kalit=self.jadval.kalit)
        messages.success(self.request, f"«{nomi}» o'chirildi.")
        return javob

    def get_success_url(self):
        return reverse('registry:jadval_list', args=[self.jadval.kalit])
