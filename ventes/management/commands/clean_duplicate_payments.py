# ventes/management/commands/clean_duplicate_payments.py

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
from django.db import transaction
from ventes.models import VenteFacilite, PaiementVente
from decimal import Decimal
from collections import defaultdict


class Command(BaseCommand):
    help = 'Clean duplicate payments for the same vente and same month'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vente_id',
            type=int,
            help='Clean only a specific vente ID',
            required=False
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
            required=False
        )
        parser.add_argument(
            '--show-details',
            action='store_true',
            help='Show detailed information about duplicates',
            required=False
        )

    def clean_vente(self, vente, dry_run=False, show_details=False):
        """Clean duplicate payments for a single vente"""
        results = {
            'vente_id': vente.id,
            'total_payments': 0,
            'unique_months': 0,
            'duplicate_months': 0,
            'duplicates_found': 0,
            'duplicates_deleted': 0,
            'payments_kept': 0,
            'duplicate_details': [],
            'errors': []
        }
        
        # Get all payments for this vente
        payments = vente.paiements.all().order_by('month_index', 'date_paiement')
        results['total_payments'] = payments.count()
        
        # Group payments by month_index
        payments_by_month = defaultdict(list)
        for payment in payments:
            if payment.month_index is not None:
                payments_by_month[payment.month_index].append(payment)
        
        results['unique_months'] = len(payments_by_month)
        
        duplicates_found = False
        payments_to_delete = []
        
        for month_index, payment_list in payments_by_month.items():
            if len(payment_list) > 1:
                duplicates_found = True
                results['duplicate_months'] += 1
                results['duplicates_found'] += len(payment_list) - 1
                
                # Sort by date (oldest first) to keep the first payment
                sorted_payments = sorted(payment_list, key=lambda p: p.date_paiement)
                
                # Keep the first payment
                keep_payment = sorted_payments[0]
                results['payments_kept'] += 1
                
                # Prepare details
                duplicate_info = {
                    'month_index': month_index,
                    'month_number': month_index + 1,
                    'keep_payment_id': keep_payment.id,
                    'keep_payment_montant': float(keep_payment.montant),
                    'keep_payment_date': keep_payment.date_paiement,
                    'duplicates': []
                }
                
                for payment in sorted_payments[1:]:
                    results['duplicates_deleted'] += 1
                    duplicate_info['duplicates'].append({
                        'id': payment.id,
                        'montant': float(payment.montant),
                        'date_paiement': payment.date_paiement
                    })
                    payments_to_delete.append(payment)
                    
                    if not dry_run:
                        payment.delete()
                
                results['duplicate_details'].append(duplicate_info)
        
        if duplicates_found and not dry_run:
            # Recalculate vente totals
            with transaction.atomic():
                # Calculate total paid from remaining payments
                total_paid = vente.paiements.filter(status="paid").aggregate(
                    total=Sum('montant')
                )['total'] or Decimal('0')
                
                vente.montant_paye_effectif = total_paid
                vente.montant_restant = max(Decimal('0'), vente.montant_total - total_paid)
                vente.solde_regle = vente.montant_restant <= 0
                
                # Update mois_status based on remaining payments
                mois_status = ["pending"] * vente.nombre_mois
                for payment in vente.paiements.filter(status="paid"):
                    if payment.month_index is not None and payment.month_index < len(mois_status):
                        mois_status[payment.month_index] = "paid"
                
                vente.mois_status = mois_status
                vente.save()
        
        results['duplicates_found'] = len(payments_to_delete) > 0
        
        if show_details and results['duplicate_details']:
            self.stdout.write(f"\n  📋 Details for vente {vente.id}:")
            for detail in results['duplicate_details']:
                self.stdout.write(f"    Month {detail['month_number']}:")
                self.stdout.write(f"      ✅ Kept: Payment {detail['keep_payment_id']} ({detail['keep_payment_montant']} DA on {detail['keep_payment_date']})")
                for dup in detail['duplicates']:
                    self.stdout.write(f"      ❌ Duplicate: Payment {dup['id']} ({dup['montant']} DA on {dup['date_paiement']})")
        
        return results

    def handle(self, *args, **options):
        vente_id = options.get('vente_id')
        dry_run = options.get('dry_run', False)
        show_details = options.get('show_details', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️ DRY RUN MODE - No changes will be made"))
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("🔍 CLEANING DUPLICATE PAYMENTS"))
        self.stdout.write("="*70)
        
        # Get ventes to process
        if vente_id:
            try:
                ventes = VenteFacilite.objects.filter(id=vente_id)
                if not ventes.exists():
                    self.stdout.write(self.style.ERROR(f"❌ Vente with ID {vente_id} not found"))
                    return
            except VenteFacilite.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Vente with ID {vente_id} not found"))
                return
        else:
            # Get only ventes that have payments
            ventes = VenteFacilite.objects.filter(
                paiements__isnull=False
            ).distinct().order_by('id')
        
        total_ventes = ventes.count()
        self.stdout.write(f"📊 Found {total_ventes} ventes with payments\n")
        
        all_results = []
        total_duplicates_found = 0
        total_duplicates_deleted = 0
        total_errors = 0
        ventes_with_duplicates = 0
        
        for idx, vente in enumerate(ventes.iterator(), 1):
            self.stdout.write(f"[{idx}/{total_ventes}] Processing vente {vente.id}...", ending='')
            
            try:
                result = self.clean_vente(vente, dry_run, show_details)
                all_results.append(result)
                
                if result['duplicates_found']:
                    ventes_with_duplicates += 1
                    total_duplicates_found += result['duplicates_found']
                    total_duplicates_deleted += result['duplicates_deleted']
                    self.stdout.write(
                        self.style.WARNING(
                            f" 🔴 Found {result['duplicates_found']} duplicate(s), "
                            f"deleted {result['duplicates_deleted']}"
                        )
                    )
                else:
                    self.stdout.write(" ✅ No duplicates found")
                    
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f" ❌ Error: {str(e)}")
                )
        
        # Summary
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("✅ CLEANUP COMPLETE"))
        self.stdout.write("="*70)
        self.stdout.write(f"  Total ventes processed: {total_ventes}")
        self.stdout.write(f"  Ventes with duplicates: {ventes_with_duplicates}")
        self.stdout.write(f"  Total duplicate payments found: {total_duplicates_found}")
        self.stdout.write(f"  Total duplicate payments deleted: {total_duplicates_deleted}")
        self.stdout.write(f"  Total errors: {total_errors}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️ DRY RUN - No changes were made"))
        
        # Show ventes with duplicates summary
        ventes_with_dup = [r for r in all_results if r['duplicates_found']]
        if ventes_with_dup and not show_details:
            self.stdout.write("\n" + "="*70)
            self.stdout.write("📋 Ventes with duplicate payments:")
            for r in ventes_with_dup:
                self.stdout.write(f"  Vente {r['vente_id']}: {r['duplicates_found']} duplicates (Month {', '.join([str(d['month_number']) for d in r['duplicate_details']])})")
        
        self.stdout.write("="*70 + "\n")