from django.urls import path
from . import views

urlpatterns = [
    # 📑 Passerelles d'accès publiques et authentification
    path('', views.index, name='index'),
    path('connexion/', views.login_select, name='login_select'),
    path('inscription/', views.register_select, name='register_select'),
    path('deconnexion/', views.user_logout, name='user_logout'),
    
    # 🔀 Aiguillage
    path('portal/', views.portal_aiguillage, name='portal_aiguillage'),
    
    # 🌾 Espace Producteur
    path('dashboard/producteur/', views.dashboard_producteur, name='dashboard_producteur'),
    path('dashboard/producteur/ajouter/', views.ajouter_produit, name='ajouter_produit'),
    path('dashboard/producteur/stocks/', views.voir_stocks, name='mes_stocks'),
    path('dashboard/producteur/commandes/', views.commandes_recues, name='commandes_recues'),
    path('dashboard/producteur/historique/', views.historique_ventes, name='historique_ventes'),
    path('dashboard/producteur/reajuster/', views.reajuster_stock_produit, name='reajuster_stock_produit'),
    path('dashboard/producteur/modifier/<int:produit_id>/', views.modifier_produit, name='modifier_produit'),
    path('dashboard/producteur/supprimer/<int:produit_id>/', views.supprimer_produit, name='supprimer_produit'),
    path('dashboard/producteur/decision/<int:reservation_id>/<str:action>/', 
         views.decider_commande_producteur, name='decider_commande_producteur'),
    
    # 🏪 Espace Commerçant
    path('dashboard/commercant/', views.dashboard_commercant, name='dashboard_commercant'),
    path('dashboard/commercant/commander/', views.passer_commande, name='passer_commande'),
    path('dashboard/commercant/annuler/<int:reservation_id>/', 
         views.annuler_commande, name='annuler_commande'),
    path('dashboard/commercant/transport/<int:reservation_id>/<str:decision>/', 
         views.decider_offre_transport, name='decider_offre_transport'),
    
    # 🚛 Espace Transporteur
    path('dashboard/transporteur/', views.dashboard_transporteur, name='dashboard_transporteur'),
    path('dashboard/transporteur/soumettre/<int:reservation_id>/', 
         views.soumettre_offre_transport, name='soumettre_offre_transport'),
    path('dashboard/transporteur/livraison/<int:reservation_id>/statut/<str:statut>/', 
         views.changer_statut_livraison, name='changer_statut_livraison'),
    
    # 🛡️ Espace Administrateur
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    
    # 🌐 Marché Public
    path('marche/', views.marche_public, name='marche_public'),
    path('marche/commander/', views.passer_commande, name='passer_commande'),
    
    # 💳 Paiements
    path('paiement/<int:reservation_id>/', views.zone_paiement, name='zone_paiement'),
    path('recu/<int:commande_id>/', views.recu_paiement, name='recu_paiement'),
]