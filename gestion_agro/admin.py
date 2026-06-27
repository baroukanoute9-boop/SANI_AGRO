from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from .models import (
    Utilisateur, Producteur, Commercant, Transporteur, Administrateur,
    Produits, FluxProduit, Reservation, Paiement, Caution, Mission,
    Livraison, Litige, Statistique
)

# =========================================================================
# 🎨 PERSONNALISATION DU PANEL ADMIN
# =========================================================================

admin.site.site_header = "SANI-AGRO | Direction générale Mali"
admin.site.site_title = "SANI-AGRO Administration"
admin.site.index_title = "Système de Pilotage Interconnecté de l'Agroalimentaire"

# =========================================================================
# 👤 1. GESTION DES UTILISATEURS
# =========================================================================

@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "role", "localisation", "telephone", "user_link")
    list_filter = ("role", "localisation")
    search_fields = ("nom", "email", "telephone")
    readonly_fields = ("user",)
    fieldsets = (
        ("Informations personnelles", {
            "fields": ("user", "nom", "email", "telephone")
        }),
        ("Rôle et localisation", {
            "fields": ("role", "localisation")
        }),
    )
    
    def user_link(self, obj):
        if obj.user:
            return mark_safe(f'<a href="/admin/auth/user/{obj.user.id}/change/" target="_blank">{obj.user.username}</a>')
        return "-"
    user_link.short_description = "Compte Django"


# =========================================================================
# 🌾 2. PROFILS UTILISATEURS
# =========================================================================

@admin.register(Producteur)
class ProducteurAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "localisation", "telephone", "produits_count", "commandes_count")
    search_fields = ("profil__nom", "profil__email")
    readonly_fields = ("profil",)
    
    def nom(self, obj): 
        return obj.profil.nom
    nom.short_description = "Nom du producteur"
    
    def email(self, obj): 
        return obj.profil.email
    email.short_description = "Email"
    
    def localisation(self, obj): 
        return obj.profil.localisation
    localisation.short_description = "Localisation"
    
    def telephone(self, obj): 
        return obj.profil.telephone
    telephone.short_description = "Téléphone"
    
    def produits_count(self, obj):
        return obj.produits.count()
    produits_count.short_description = "Nombre de produits"
    
    def commandes_count(self, obj):
        return Reservation.objects.filter(fluxproduit__produit__producteur=obj).count()
    commandes_count.short_description = "Commandes reçues"


@admin.register(Commercant)
class CommercantAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "entreprise", "adresse_boutique", "localisation", "telephone", "commandes_count")
    search_fields = ("profil__nom", "entreprise")
    readonly_fields = ("profil",)
    
    def nom(self, obj): 
        return obj.profil.nom
    nom.short_description = "Nom du commerçant"
    
    def email(self, obj): 
        return obj.profil.email
    email.short_description = "Email"
    
    def localisation(self, obj): 
        return obj.profil.localisation
    localisation.short_description = "Localisation"
    
    def telephone(self, obj): 
        return obj.profil.telephone
    telephone.short_description = "Téléphone"
    
    def commandes_count(self, obj):
        return obj.reservations.count()
    commandes_count.short_description = "Commandes passées"


@admin.register(Transporteur)
class TransporteurAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "type_vehicule", "capacite_transport_int", "disponibilite", "solde", "localisation", "telephone", "missions_count")
    list_filter = ("disponibilite", "type_vehicule")
    search_fields = ("profil__nom", "profil__email")
    readonly_fields = ("profil",)
    
    def nom(self, obj): 
        return obj.profil.nom
    nom.short_description = "Nom du transporteur"
    
    def email(self, obj): 
        return obj.profil.email
    email.short_description = "Email"
    
    def localisation(self, obj): 
        return obj.profil.localisation
    localisation.short_description = "Localisation"
    
    def telephone(self, obj): 
        return obj.profil.telephone
    telephone.short_description = "Téléphone"
    
    def missions_count(self, obj):
        return obj.missions.count()
    missions_count.short_description = "Missions effectuées"


@admin.register(Administrateur)
class AdministrateurAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "localisation", "telephone")
    search_fields = ("profil__nom", "profil__email")
    readonly_fields = ("profil",)
    
    def nom(self, obj): 
        return obj.profil.nom
    nom.short_description = "Nom de l'administrateur"
    
    def email(self, obj): 
        return obj.profil.email
    email.short_description = "Email"
    
    def localisation(self, obj): 
        return obj.profil.localisation
    localisation.short_description = "Localisation"
    
    def telephone(self, obj): 
        return obj.profil.telephone
    telephone.short_description = "Téléphone"


# =========================================================================
# 📦 3. PRODUITS ET STOCKS
# =========================================================================

@admin.register(Produits)
class ProduitsAdmin(admin.ModelAdmin):
    list_display = ("apercu_photo", "nom_produit", "categorie", "quantite_dispo", "unite_mesure", "prix_unitaire", "producteur", "zone_production", "date_disponibilite", "statut_disponibilite")
    list_editable = ("quantite_dispo", "prix_unitaire")
    list_filter = ("categorie", "producteur", "date_disponibilite")
    search_fields = ("nom_produit", "producteur__profil__nom", "categorie")
    list_per_page = 25
    readonly_fields = ("apercu_photo",)
    fieldsets = (
        ("Informations générales", {
            "fields": ("nom_produit", "categorie", "producteur")
        }),
        ("Stock et prix", {
            "fields": ("quantite_dispo", "unite_mesure", "prix_unitaire")
        }),
        ("Provenance et disponibilité", {
            "fields": ("zone_production", "date_disponibilite")
        }),
        ("Image", {
            "fields": ("image_produit", "apercu_photo")
        }),
    )
    
    def apercu_photo(self, obj):
        if obj.image_produit:
            return mark_safe(f'<img src="{obj.image_produit.url}" style="width:60px;height:60px;border-radius:8px;object-fit:cover;border:2px solid #d9eee0;"/>')
        return mark_safe('<span style="color:#9ca3af;font-style:italic;">📷 Pas de photo</span>')
    apercu_photo.short_description = "Aperçu"
    
    def statut_disponibilite(self, obj):
        from django.utils import timezone
        if obj.quantite_dispo == 0:
            return mark_safe('<span style="color:#dc3545;font-weight:bold;">⛔ Épuisé</span>')
        elif obj.date_disponibilite and obj.date_disponibilite < timezone.now().date():
            return mark_safe('<span style="color:#b89a6a;font-weight:bold;">⚠️ Date dépassée</span>')
        elif obj.quantite_dispo < 50:
            return mark_safe('<span style="color:#b89a6a;font-weight:bold;">⚠️ Stock faible</span>')
        else:
            return mark_safe('<span style="color:#2b8c5e;font-weight:bold;">✅ Disponible</span>')
    statut_disponibilite.short_description = "Statut"


@admin.register(FluxProduit)
class FluxProduitAdmin(admin.ModelAdmin):
    list_display = ("id", "produit", "zone_depart", "zone_arrivee", "quantite", "date_flux")
    list_filter = ("zone_depart", "zone_arrivee", "date_flux")
    search_fields = ("produit__nom_produit", "zone_depart", "zone_arrivee")
    readonly_fields = ("date_flux",)
    fieldsets = (
        ("Informations sur le flux", {
            "fields": ("produit", "quantite")
        }),
        ("Itinéraire", {
            "fields": ("zone_depart", "zone_arrivee")
        }),
        ("Date", {
            "fields": ("date_flux",)
        }),
    )


# =========================================================================
# 📋 4. COMMANDES ET RÉSERVATIONS
# =========================================================================

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "commercant_nom", "produit_nom", "quantite", "statut_reservation", "date_reservation", "transporteur_info", "prix_transport_propose")
    list_editable = ("statut_reservation",)
    list_filter = ("statut_reservation", "date_reservation")
    search_fields = ("commercant__profil__nom", "fluxproduit__produit__nom_produit", "nom_chauffeur", "telephone_chauffeur")
    readonly_fields = ("date_reservation",)
    list_per_page = 25
    fieldsets = (
        ("Informations générales", {
            "fields": ("fluxproduit", "commercant", "quantite")
        }),
        ("Statut", {
            "fields": ("statut_reservation", "date_reservation")
        }),
        ("Transport", {
            "fields": ("transporteur", "nom_chauffeur", "telephone_chauffeur", "type_vehicule", "prix_transport_propose")
        }),
    )
    
    def commercant_nom(self, obj):
        return obj.commercant.profil.nom
    commercant_nom.short_description = "Commerçant"
    
    def produit_nom(self, obj):
        return obj.fluxproduit.produit.nom_produit
    produit_nom.short_description = "Produit"
    
    def transporteur_info(self, obj):
        if obj.transporteur:
            return f"{obj.transporteur.profil.nom} ({obj.nom_chauffeur})"
        return "-"
    transporteur_info.short_description = "Transporteur/Chauffeur"


# =========================================================================
# 💰 5. PAIEMENTS
# =========================================================================

@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("id", "reservation_id", "commercant_nom", "montant_paiement", "mode_paiement", "transaction_id", "date_paiement", "statut", "statut_colore")
    list_filter = ("mode_paiement", "statut", "date_paiement")
    search_fields = ("reservation__commercant__profil__nom", "transaction_id")
    readonly_fields = ("date_paiement",)
    list_per_page = 25
    fieldsets = (
        ("Informations générales", {
            "fields": ("reservation", "montant_paiement")
        }),
        ("Mode de paiement", {
            "fields": ("mode_paiement", "transaction_id")
        }),
        ("Statut", {
            "fields": ("statut", "date_paiement")
        }),
    )
    
    def commercant_nom(self, obj):
        return obj.reservation.commercant.profil.nom
    commercant_nom.short_description = "Commerçant"
    
    def reservation_id(self, obj):
        return f"#{obj.reservation.id}"
    reservation_id.short_description = "Réservation"
    
    def statut_colore(self, obj):
        if obj.statut == "VALIDE":
            return mark_safe('<span style="color:#2b8c5e;font-weight:bold;">✅ Validé</span>')
        elif obj.statut == "EN_ATTENTE":
            return mark_safe('<span style="color:#b89a6a;font-weight:bold;">⏳ En attente</span>')
        else:
            return mark_safe('<span style="color:#dc3545;font-weight:bold;">❌ {obj.statut}</span>')
    statut_colore.short_description = "Statut"


# =========================================================================
# 🏦 6. CAUTIONS
# =========================================================================

@admin.register(Caution)
class CautionAdmin(admin.ModelAdmin):
    list_display = ("id", "transporteur_nom", "montant_caution", "etat_caution", "reservation_id", "date_depot")
    list_editable = ("etat_caution",)
    list_filter = ("etat_caution", "date_depot")
    search_fields = ("transporteur__profil__nom", "reservation__commercant__profil__nom")
    readonly_fields = ("date_depot",)
    
    def transporteur_nom(self, obj):
        return obj.transporteur.profil.nom if obj.transporteur else "-"
    transporteur_nom.short_description = "Transporteur"
    
    def reservation_id(self, obj):
        return f"#{obj.reservation.id}" if obj.reservation else "-"
    reservation_id.short_description = "Réservation"


# =========================================================================
# 🚛 7. MISSIONS
# =========================================================================

@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("id", "reservation_id", "transporteur_nom", "statut_mission", "date_assignation")
    list_editable = ("statut_mission",)
    list_filter = ("statut_mission", "date_assignation")
    search_fields = ("transporteur__profil__nom", "reservation__commercant__profil__nom")
    readonly_fields = ("date_assignation",)
    
    def transporteur_nom(self, obj):
        return obj.transporteur.profil.nom
    transporteur_nom.short_description = "Transporteur"
    
    def reservation_id(self, obj):
        return f"#{obj.reservation.id}"
    reservation_id.short_description = "Réservation"


# =========================================================================
# 📦 8. LIVRAISONS
# =========================================================================

@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ("id", "mission_id", "date_depart_prevue", "date_arrivee_prevue", "etat_livraison", "statut_colore")
    list_editable = ("etat_livraison",)
    list_filter = ("etat_livraison", "date_depart_prevue")
    search_fields = ("mission__transporteur__profil__nom",)
    fieldsets = (
        ("Mission", {
            "fields": ("mission",)
        }),
        ("Dates prévues", {
            "fields": ("date_depart_prevue", "date_arrivee_prevue")
        }),
        ("Suivi", {
            "fields": ("etat_livraison", "observations")
        }),
    )
    
    def mission_id(self, obj):
        return f"#{obj.mission.id}"
    mission_id.short_description = "Mission"
    
    def statut_colore(self, obj):
        if obj.etat_livraison == "LIVREE":
            return mark_safe('<span style="color:#2b8c5e;font-weight:bold;">✅ Livrée</span>')
        elif obj.etat_livraison == "EN_TRANSIT":
            return mark_safe('<span style="color:#3b8c9e;font-weight:bold;">🚚 En transit</span>')
        elif obj.etat_livraison == "CHARGEE":
            return mark_safe('<span style="color:#b89a6a;font-weight:bold;">📦 Chargée</span>')
        else:
            return mark_safe('<span style="color:#7a9a8a;font-weight:bold;">⏳ En attente</span>')
    statut_colore.short_description = "Statut"


# =========================================================================
# ⚖️ 9. LITIGES
# =========================================================================

@admin.register(Litige)
class LitigeAdmin(admin.ModelAdmin):
    list_display = ("id", "mission_id", "motif_court", "statut_litige", "date_creation")
    list_editable = ("statut_litige",)
    list_filter = ("statut_litige", "date_creation")
    search_fields = ("mission__transporteur__profil__nom", "motif")
    readonly_fields = ("date_creation",)
    fieldsets = (
        ("Mission", {
            "fields": ("mission",)
        }),
        ("Motif", {
            "fields": ("motif",)
        }),
        ("Statut", {
            "fields": ("statut_litige", "date_creation")
        }),
    )
    
    def mission_id(self, obj):
        return f"#{obj.mission.id}"
    mission_id.short_description = "Mission"
    
    def motif_court(self, obj):
        return obj.motif[:50] + "..." if len(obj.motif) > 50 else obj.motif
    motif_court.short_description = "Motif"


# =========================================================================
# 📊 10. STATISTIQUES
# =========================================================================

@admin.register(Statistique)
class StatistiqueAdmin(admin.ModelAdmin):
    list_display = ("id_statistique", "total_missions", "total_litiges", "chiffre_affaires_global", "date_mise_a_jour")
    list_filter = ("date_mise_a_jour",)
    readonly_fields = ("id_statistique", "date_mise_a_jour")
    fieldsets = (
        ("Statistiques générales", {
            "fields": ("total_missions", "total_litiges", "chiffre_affaires_global")
        }),
        ("Date", {
            "fields": ("date_mise_a_jour",)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # ✅ Empêcher l'ajout manuel car les statistiques sont calculées automatiquement
    
    def has_delete_permission(self, request, obj=None):
        return False  # ✅ Empêcher la suppression des statistiques


# =========================================================================
# 🎯 11. ACTIONS PERSONNALISÉES
# =========================================================================

@admin.action(description="🔄 Marquer les réservations comme validées")
def valider_reservations(modeladmin, request, queryset):
    updated = queryset.update(statut_reservation="VALIDÉE")
    modeladmin.message_user(request, f"{updated} réservation(s) validée(s) avec succès.")

@admin.action(description="❌ Marquer les réservations comme annulées")
def annuler_reservations(modeladmin, request, queryset):
    updated = queryset.update(statut_reservation="ANNULÉE")
    modeladmin.message_user(request, f"{updated} réservation(s) annulée(s).")

@admin.action(description="✅ Marquer les paiements comme validés")
def valider_paiements(modeladmin, request, queryset):
    updated = queryset.update(statut="VALIDE")
    modeladmin.message_user(request, f"{updated} paiement(s) validé(s).")


# =========================================================================
# 🔄 12. ENREGISTREMENT DES ACTIONS
# =========================================================================

# ✅ Ajout des actions personnalisées
ReservationAdmin.actions = [valider_reservations, annuler_reservations]
PaiementAdmin.actions = [valider_paiements]


# =========================================================================
# 📈 13. INLINES (Affichage des relations dans un même écran)
# =========================================================================

class ProduitInline(admin.TabularInline):
    model = Produits
    extra = 1
    fields = ("nom_produit", "categorie", "quantite_dispo", "prix_unitaire")
    show_change_link = True


class ReservationInline(admin.TabularInline):
    model = Reservation
    extra = 1
    fields = ("fluxproduit", "quantite", "statut_reservation")
    show_change_link = True


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 1
    fields = ("montant_paiement", "mode_paiement", "statut")
    show_change_link = True


# ✅ Ajout des inlines aux admin appropriés
ProducteurAdmin.inlines = [ProduitInline]
CommercantAdmin.inlines = [ReservationInline]
TransporteurAdmin.inlines = [ReservationInline]
ReservationAdmin.inlines = [PaiementInline]


# =========================================================================
# 🏷️ 14. CONFIGURATION DES PERMISSIONS
# =========================================================================

# ✅ Limiter les actions pour certains modèles
StatistiqueAdmin.actions = []  # Aucune action en masse pour les statistiques