# inventaire/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import (
    SessionInventaire, ProduitInventaire, 
    MouvementInventaire, EcartInventaire
)
from .serializers import (
    SessionInventaireSerializer, SessionInventaireDetailSerializer,
    ProduitInventaireSerializer, ComptageBarreSerializer,
    EcartInventaireSerializer
)
from produits.models import Produit
from parametres.models import Magasin
from decimal import Decimal
from rest_framework.permissions import IsAuthenticated

class SessionInventaireViewSet(viewsets.ModelViewSet):
    """Manage inventory sessions"""
    
    queryset = SessionInventaire.objects.all()
    serializer_class = SessionInventaireSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SessionInventaireDetailSerializer
        return SessionInventaireSerializer
    
    def perform_create(self, serializer):
        with transaction.atomic():
            # Create session
            session = serializer.save(
                compteur_par=self.request.user.get_full_name() or self.request.user.username
            )
            
            # Get all products in this store
            produits = Produit.objects.filter(
                magasins__contains=[{'id': session.magasin.id}]
            )
            
            # Create inventory entries for each product
            for produit in produits:
                quantite = produit.get_quantite_par_magasin(session.magasin.id)
                valeur = quantite * (produit.prix_achat or 0)
                
                ProduitInventaire.objects.create(
                    session=session,
                    produit=produit,
                    quantite_attendue=quantite,
                    valeur_attendue=valeur
                )
            
            # Update session totals
            session.total_produits_attendus = produits.count()
            session.save()
            
            return session
    
    @action(detail=True, methods=['post'])
    def scan_barcode(self, request, pk=None):
        """Scan a barcode during inventory"""
        session = self.get_object()
        
        if session.est_termine or session.est_annule:
            return Response(
                {"error": "Session déjà terminée ou annulée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ComptageBarreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        barcode = serializer.validated_data['barcode']
        
        # Find product by barcode
        produit = Produit.objects.filter(
            codes_barres__contains=[barcode]
        ).first()
        
        if not produit:
            return Response(
                {"error": "Produit non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create inventory entry
        inventaire, created = ProduitInventaire.objects.get_or_create(
            session=session,
            produit=produit,
            defaults={
                'quantite_attendue': produit.get_quantite_par_magasin(session.magasin.id)
            }
        )
        
        # Update counted quantity
        ancienne_quantite = inventaire.quantite_comptee
        inventaire.quantite_comptee += 1
        inventaire.calculer_ecarts()
        
        # Record movement
        MouvementInventaire.objects.create(
            produit_inventaire=inventaire,
            type_mouvement='count',
            ancienne_quantite=ancienne_quantite,
            nouvelle_quantite=inventaire.quantite_comptee,
            codes_barres_scannes=[barcode],
            effectue_par=request.user.get_full_name() or request.user.username
        )
        
        # Update session totals
        session.total_produits_comptes = ProduitInventaire.objects.filter(
            session=session,
            quantite_comptee__gt=0
        ).count()
        session.save()
        
        return Response({
            'produit': {
                'id': produit.id,
                'nom': produit.nom,
                'code_barre': barcode
            },
            'quantite_comptee': inventaire.quantite_comptee,
            'quantite_attendue': inventaire.quantite_attendue,
            'ecart': inventaire.quantite_ecart
        })
    
    @action(detail=True, methods=['post'])
    def confirm_product(self, request, pk=None):
        """Confirm counting for a product"""
        session = self.get_object()
        
        if session.est_termine or session.est_annule:
            return Response(
                {"error": "Session déjà terminée ou annulée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        produit_id = request.data.get('produit_id')
        
        try:
            inventaire = ProduitInventaire.objects.get(
                session=session,
                produit_id=produit_id
            )
        except ProduitInventaire.DoesNotExist:
            return Response(
                {"error": "Produit non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Mark as verified
        inventaire.est_verifie = True
        inventaire.save()
        
        # Record verification movement
        MouvementInventaire.objects.create(
            produit_inventaire=inventaire,
            type_mouvement='verify',
            ancienne_quantite=inventaire.quantite_comptee,
            nouvelle_quantite=inventaire.quantite_comptee,
            effectue_par=request.user.get_full_name() or request.user.username
        )
        
        # Check if there's a discrepancy
        if inventaire.quantite_ecart != 0:
            # Create discrepancy record
            ecart_type = 'excess' if inventaire.quantite_ecart > 0 else 'missing'
            EcartInventaire.objects.create(
                produit_inventaire=inventaire,
                type_ecart=ecart_type,
                quantite=abs(inventaire.quantite_ecart),
                valeur=abs(inventaire.valeur_ecart),
                declare_par=request.user.get_full_name() or request.user.username
            )
            
            # Update session totals
            if ecart_type == 'missing':
                session.total_produits_manquants += abs(inventaire.quantite_ecart)
            else:
                session.total_produits_excedents += abs(inventaire.quantite_ecart)
            session.save()
        
        return Response({
            'success': True,
            'message': 'Produit confirmé',
            'quantite_comptee': inventaire.quantite_comptee,
            'quantite_attendue': inventaire.quantite_attendue,
            'ecart': inventaire.quantite_ecart
        })
    
    @action(detail=True, methods=['post'])
    def finish_session(self, request, pk=None):
        """Finish inventory session"""
        session = self.get_object()
        
        if session.est_termine:
            return Response(
                {"error": "Session déjà terminée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Check all products are verified
            unverified = ProduitInventaire.objects.filter(
                session=session,
                est_verifie=False
            ).exists()
            
            if unverified:
                return Response(
                    {"error": "Tous les produits doivent être vérifiés"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Apply adjustments to actual stock
            for inventaire in ProduitInventaire.objects.filter(session=session):
                if inventaire.quantite_ecart != 0:
                    # Adjust actual stock
                    try:
                        if inventaire.quantite_ecart > 0:
                            # Add excess items
                            inventaire.produit.increment_quantite_par_magasin(
                                session.magasin.id,
                                session.magasin.nom,
                                inventaire.quantite_ecart
                            )
                        else:
                            # Remove missing items
                            inventaire.produit.decrement_quantite_par_magasin(
                                session.magasin.id,
                                abs(inventaire.quantite_ecart)
                            )
                    except Exception as e:
                        return Response(
                            {"error": f"Erreur lors de l'ajustement: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Finish session
            session.terminer()
        
        return Response({
            'success': True,
            'message': 'Inventaire terminé avec succès'
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get inventory statistics"""
        session = self.get_object()
        
        # Get all inventory items
        inventaires = ProduitInventaire.objects.filter(session=session)
        
        # Calculate statistics
        produits_verifies = inventaires.filter(est_verifie=True).count()
        produits_non_verifies = inventaires.filter(est_verifie=False).count()
        
        produits_avec_ecart = inventaires.exclude(quantite_ecart=0).count()
        
        valeur_totale_attendue = inventaires.aggregate(
            total=models.Sum('valeur_attendue')
        )['total'] or 0
        
        valeur_totale_comptee = inventaires.aggregate(
            total=models.Sum('valeur_comptee')
        )['total'] or 0
        
        ecart_valeur = valeur_totale_comptee - valeur_totale_attendue
        
        return Response({
            'produits_totaux': inventaires.count(),
            'produits_verifies': produits_verifies,
            'produits_non_verifies': produits_non_verifies,
            'produits_avec_ecart': produits_avec_ecart,
            'valeur_totale_attendue': valeur_totale_attendue,
            'valeur_totale_comptee': valeur_totale_comptee,
            'ecart_valeur': ecart_valeur,
            'taux_avancement': session.taux_avancement
        })


class EcartInventaireViewSet(viewsets.ModelViewSet):
    """Manage inventory discrepancies"""
    
    queryset = EcartInventaire.objects.all()
    serializer_class = EcartInventaireSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a discrepancy"""
        ecart = self.get_object()
        
        if ecart.statut != 'pending':
            return Response(
                {"error": "Cet écart a déjà été traité"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        resolution = request.data.get('resolution')
        if not resolution:
            return Response(
                {"error": "La résolution est requise"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ecart.resoudre(
            resolution=resolution,
            resolved_by=request.user.get_full_name() or request.user.username
        )
        
        return Response({
            'success': True,
            'message': 'Écart résolu avec succès'
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a discrepancy"""
        ecart = self.get_object()
        
        if ecart.statut != 'pending':
            return Response(
                {"error": "Cet écart a déjà été traité"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason')
        if not reason:
            return Response(
                {"error": "La raison est requise"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ecart.rejeter(reason)
        
        return Response({
            'success': True,
            'message': 'Écart rejeté'
        })