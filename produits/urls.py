from django.urls import path
from .views import*

urlpatterns = [
    path('produits/', ProduitListCreateAPIView.as_view(), name='produit-list-create'),
    path('produits/<int:pk>/', ProduitRetrieveUpdateDestroyAPIView.as_view(), name='produit-detail'),
      # Magasin quantity management
    path('produits/<int:produit_id>/increment-magasin/', 
         ProduitIncrementMagasinQuantityView.as_view(), 
         name='produit-increment-magasin'),
    path('produits/<int:produit_id>/decrement-magasin/', 
         ProduitDecrementMagasinQuantityView.as_view(), 
         name='produit-decrement-magasin'),
    path("produits/export-excel/", ExportProduitExcelView.as_view(), name="produits-export"),
    path("produits/import-excel/", ImportProduitExcelView.as_view(), name="produits-import"),
    path('comparaison/', ProduitComparaisonView.as_view(), name='produit-comparaison'),
    path('comparaison/detail/<int:product_id>/', ProduitDetailComparaisonView.as_view(), name='produit-comparaison-detail'),
    path('comparaison/magasin/<int:magasin_id>/', ProduitMagasinStockView.as_view(), name='produit-magasin-stock'),
     path('produits/familles/', FamillesProduitView.as_view(), name='produits-familles'), 
     path("import-prix/", importer_prix_produits, name="import-prix"),
     path('reset-quantite-codes/', ResetQuantiteCodesBarresView.as_view(), name='reset-quantite-codes'),
     path('import-excel/', ProduitImportExcelAPIView.as_view(), name='produit-import-excel'),
    path('export-excel/', ProduitExportExcelAPIView.as_view(), name='produit-export-excel'),
]
