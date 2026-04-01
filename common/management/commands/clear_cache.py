# common/management/commands/clear_cache.py

from django.core.management.base import BaseCommand
from common.cache_manager import CacheManager

class Command(BaseCommand):
    help = 'Clear all application cache'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Clear cache for specific app (dashboard, achats, ventes, etc.)'
        )
        parser.add_argument(
            '--pattern',
            type=str,
            help='Clear cache keys matching pattern'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear all cache'
        )
    
    def handle(self, *args, **options):
        if options['all']:
            self.stdout.write("Clearing ALL cache...")
            CacheManager.clear_all_cache()
            self.stdout.write(self.style.SUCCESS("All cache cleared!"))
        
        elif options['app']:
            self.stdout.write(f"Clearing cache for app: {options['app']}")
            if CacheManager.clear_app_cache(options['app']):
                self.stdout.write(self.style.SUCCESS(f"Cache for {options['app']} cleared!"))
            else:
                self.stdout.write(self.style.WARNING(f"App {options['app']} not found"))
        
        elif options['pattern']:
            self.stdout.write(f"Clearing cache pattern: {options['pattern']}")
            CacheManager.clear_pattern(options['pattern'])
            self.stdout.write(self.style.SUCCESS(f"Pattern {options['pattern']} cleared!"))
        
        else:
            self.stdout.write("Please specify --all, --app, or --pattern")