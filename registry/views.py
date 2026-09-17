from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

from .models import Mahalla, Oila, Shaxs


class DashboardView(ListView):
    """Bosh sahifa: umumiy statistika + mahallalar bo'yicha taqsimot."""

    template_name = 'registry/dashboard.html'
    context_object_name = 'mahallalar'

    def get_queryset(self):
        return (
            Mahalla.objects
            .annotate(shaxslar_soni_ann=Count('oilalar__azolar', distinct=True))
            .order_by('-shaxslar_soni_ann')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['jami_shaxslar'] = Shaxs.objects.count()
        ctx['jami_oilalar'] = Oila.objects.count()
        ctx['jami_mahallalar'] = Mahalla.objects.count()
        ctx['toifalar'] = (
            Shaxs.objects
            .values('ijtimoiy_toifa')
            .annotate(soni=Count('id'))
            .order_by('-soni')
        )
        ctx['uchrashuvda_qatnashgan'] = Shaxs.objects.filter(
            uchrashuv_qatnashgan=True
        ).count()
        return ctx


class ShaxsListView(ListView):
    """Qidiruv va filtrlash imkoniyatli shaxslar ro'yxati."""

    model = Shaxs
    template_name = 'registry/shaxs_list.html'
    context_object_name = 'shaxslar'
    paginate_by = getattr(settings, 'PAGE_SIZE', 25)

    def get_queryset(self):
        qs = Shaxs.objects.select_related('oila', 'oila__mahalla')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(fio__icontains=q) | Q(jshshir__icontains=q))

        mahalla_id = self.request.GET.get('mahalla')
        if mahalla_id:
            qs = qs.filter(oila__mahalla_id=mahalla_id)

        toifa = self.request.GET.get('toifa')
        if toifa:
            qs = qs.filter(ijtimoiy_toifa=toifa)

        jinsi = self.request.GET.get('jinsi')
        if jinsi:
            qs = qs.filter(jinsi=jinsi)

        return qs.order_by('fio')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['mahallalar'] = Mahalla.objects.order_by('nomi')
        ctx['toifalar'] = (
            Shaxs.objects.exclude(ijtimoiy_toifa='')
            .values_list('ijtimoiy_toifa', flat=True).distinct().order_by('ijtimoiy_toifa')
        )
        ctx['soragi'] = self.request.GET
        return ctx


class ShaxsDetailView(DetailView):
    model = Shaxs
    template_name = 'registry/shaxs_detail.html'
    context_object_name = 'shaxs'

    def get_queryset(self):
        return Shaxs.objects.select_related('oila', 'oila__mahalla')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['oila_azolari'] = (
            self.object.oila.azolar.exclude(pk=self.object.pk).order_by('tartib_raqami')
        )
        return ctx


class MahallaListView(ListView):
    model = Mahalla
    template_name = 'registry/mahalla_list.html'
    context_object_name = 'mahallalar'

    def get_queryset(self):
        return (
            Mahalla.objects
            .annotate(shaxslar_soni_ann=Count('oilalar__azolar', distinct=True))
            .order_by('nomi')
        )


class MahallaDetailView(DetailView):
    model = Mahalla
    template_name = 'registry/mahalla_detail.html'
    context_object_name = 'mahalla'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['shaxslar'] = (
            Shaxs.objects.filter(oila__mahalla=self.object)
            .select_related('oila').order_by('fio')
        )
        return ctx
