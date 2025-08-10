from rest_framework import generics, permissions,status,filters
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, timedelta
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta
from django.utils.timezone import localtime,datetime

from rest_framework.permissions import IsAuthenticated

class AchatListCreateAPIView(generics.ListCreateAPIView):
    queryset = Achat.objects.all()
    serializer_class = AchatSerializer
    permission_classes = [permissions.IsAuthenticated]

class AchatRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Achat.objects.all()
    serializer_class = AchatSerializer
    permission_classes = [permissions.IsAuthenticated]


# class AchatGroupeListCreateAPIView(generics.ListCreateAPIView):
#     queryset = AchatGroupe.objects.all().order_by('-date')
#     serializer_class = AchatGroupeSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['fournisseur','date']
    
#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())

#         serializer = self.get_serializer(queryset, many=True)

#         total_achats = queryset.count()
#         somme_totale = sum([ag.total for ag in queryset])
#         somme_payee = sum([ag.somme_payee for ag in queryset])
#         somme_restante = sum([ag.somme_restante for ag in queryset])

#         return Response({
#             'nombre_achats': total_achats,
#             'somme_totale': "%.2f" % somme_totale,
#             'somme_payee': "%.2f" % somme_payee,
#             'somme_restante': "%.2f" % somme_restante,
#             'achats_groupes': serializer.data
#         }, status=status.HTTP_200_OK)
#     def get_queryset(self):
#       queryset = AchatGroupe.objects.all()
#       request = self.request
#       periode = request.query_params.get('periode')
#       date_from = request.query_params.get('date_from')  # format: YYYY-MM-DD
#       date_to = request.query_params.get('date_to')      # format: YYYY-MM-DD

#       today = date.today()

#     # 📌 Intervalle personnalisé prioritaire
#       if date_from and date_to:
#     # Étend la date_to jusqu'à la fin de la journée
#         date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
#         date_to_extended = datetime.combine(date_to_dt, datetime.max.time())
#         date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
#         date_from_start = datetime.combine(date_from_dt, datetime.min.time())

#         date_from_aware = timezone.make_aware(date_from_start)
#         date_to_aware = timezone.make_aware(date_to_extended)

#         queryset = queryset.filter(date__range=(date_from_aware, date_to_aware))

#       elif periode == "today":
#        local_today = localtime(now()).date()
#        start_of_day = timezone.make_aware(datetime.combine(local_today, datetime.min.time()))
#        end_of_day = timezone.make_aware(datetime.combine(local_today, datetime.max.time()))
#        queryset = queryset.filter(date__range=(start_of_day, end_of_day))
#       elif periode == "yesterday":
#         queryset = queryset.filter(date=today - timedelta(days=1))
#       elif periode == "this_week":
#         start = today - timedelta(days=today.weekday())
#         queryset = queryset.filter(date__gte=start)
#       elif periode == "this_month":
#         start = today.replace(day=1)
#         queryset = queryset.filter(date__gte=start)
#       elif periode == "last_month":
#         first_day_this_month = today.replace(day=1)
#         last_month = first_day_this_month - timedelta(days=1)
#         start = last_month.replace(day=1)
#         end = last_month
#         queryset = queryset.filter(date__range=(start, end))
#       elif periode == "this_year":
#         start = today.replace(month=1, day=1)
#         queryset = queryset.filter(date__gte=start)

#       return queryset
    
from django.db.models import Q

class AchatGroupeListCreateAPIView(generics.ListCreateAPIView):
    queryset = AchatGroupe.objects.all().order_by('-date')
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['fournisseur', 'date']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        total_achats = queryset.count()
        somme_totale = sum([ag.total for ag in queryset])
        somme_payee = sum([ag.somme_payee for ag in queryset])
        somme_restante = sum([ag.somme_restante for ag in queryset])

        return Response({
            'nombre_achats': total_achats,
            'somme_totale': "%.2f" % somme_totale,
            'somme_payee': "%.2f" % somme_payee,
            'somme_restante': "%.2f" % somme_restante,
            'achats_groupes': serializer.data
        }, status=status.HTTP_200_OK)

    def get_queryset(self):
        queryset = AchatGroupe.objects.all()
        request = self.request

        # 📌 New filter: produit
        produit_id = request.query_params.get('produit')

        periode = request.query_params.get('periode')
        date_from = request.query_params.get('date_from')  # format: YYYY-MM-DD
        date_to = request.query_params.get('date_to')      # format: YYYY-MM-DD

        today = date.today()

        # 📌 Intervalle personnalisé prioritaire
        if date_from and date_to:
            # Étend la date_to jusqu'à la fin de la journée
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            date_to_extended = datetime.combine(date_to_dt, datetime.max.time())
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            date_from_start = datetime.combine(date_from_dt, datetime.min.time())

            date_from_aware = timezone.make_aware(date_from_start)
            date_to_aware = timezone.make_aware(date_to_extended)

            queryset = queryset.filter(date__range=(date_from_aware, date_to_aware))

        elif periode == "today":
            local_today = localtime(now()).date()
            start_of_day = timezone.make_aware(datetime.combine(local_today, datetime.min.time()))
            end_of_day = timezone.make_aware(datetime.combine(local_today, datetime.max.time()))
            queryset = queryset.filter(date__range=(start_of_day, end_of_day))
        elif periode == "yesterday":
            queryset = queryset.filter(date=today - timedelta(days=1))
        elif periode == "this_week":
            start = today - timedelta(days=today.weekday())
            queryset = queryset.filter(date__gte=start)
        elif periode == "this_month":
            start = today.replace(day=1)
            queryset = queryset.filter(date__gte=start)
        elif periode == "last_month":
            first_day_this_month = today.replace(day=1)
            last_month = first_day_this_month - timedelta(days=1)
            start = last_month.replace(day=1)
            end = last_month
            queryset = queryset.filter(date__range=(start, end))
        elif periode == "this_year":
            start = today.replace(month=1, day=1)
            queryset = queryset.filter(date__gte=start)

        # ✅ Filter by product if provided
        if produit_id:
            queryset = queryset.filter(achats__produit_id=produit_id).distinct()

        return queryset

class AchatGroupeRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AchatGroupe.objects.all()
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]

