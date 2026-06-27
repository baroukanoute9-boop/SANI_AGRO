import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.messages import get_messages
from django.contrib.auth.decorators import login_required
from .models import (
    Reservation, Produits, FluxProduit, Paiement, Producteur, 
    Utilisateur, Commercant, Transporteur, Administrateur,
    Mission, Livraison, Litige, Statistique, Caution
)
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

# =========================================================================
# 🔐 1. PASSERELLES ET AUTHENTIFICATION
# =========================================================================

def index(request):
    """Page d'accueil générale de SANI-AGRO"""
    return render(request, 'index.html')

def login_select(request):
    """Connexion avec redirection selon le rôle réel de l'utilisateur"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role", "").upper()
        
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return redirect("login_select")
        
        try:
            profil = user.utilisateur_profile
        except Utilisateur.DoesNotExist:
            messages.error(request, "Aucun profil associé à ce compte.")
            return redirect("login_select")
        
        # Vérifie que le rôle choisi correspond au rôle enregistré
        if profil.role != role:
            messages.error(
                request,
                f"Ce compte est enregistré comme {profil.role}."
            )
            return redirect("login_select")
        
        # Connexion
        login(request, user)
        
        # ✅ Redirection selon le rôle
        if role == "PRODUCTEUR":
            if hasattr(profil, "profil_producteur"):
                return redirect("dashboard_producteur")
            else:
                messages.error(request, "Profil Producteur introuvable.")
                return redirect("login_select")
                
        elif role == "COMMERCANT":
            if hasattr(profil, "commercant"):
                return redirect("dashboard_commercant")
            else:
                messages.error(request, "Profil Commerçant introuvable.")
                return redirect("login_select")
                
        elif role == "TRANSPORTEUR":
            if hasattr(profil, "transporteur"):
                return redirect("dashboard_transporteur")
            else:
                messages.error(request, "Profil Transporteur introuvable.")
                return redirect("login_select")
                
        elif role == "ADMIN":
            if hasattr(profil, "administrateur"):
                return redirect("dashboard_admin")
            else:
                messages.error(request, "Profil Administrateur introuvable.")
                return redirect("login_select")
        
        messages.error(request, "Rôle non reconnu.")
        return redirect("login_select")
    
    return render(request, "login_select.html")

def marche_public(request):
    """Catalogue public affichant les produits disponibles"""
    produits = Produits.objects.filter(quantite_dispo__gt=0).order_by('-id')
    return render(request, "marche.html", {"produits": produits})

def user_logout(request):
    """Déconnexion complète"""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('index')

def register_select(request):
    """Inscription avec création automatique du sous-profil"""
    if request.method == "POST":
        role = request.POST.get("role", "").upper()
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        localisation = request.POST.get("localisation")
        telephone = request.POST.get("telephone", "")
        
        # Vérification des doublons
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
            return render(request, "register_select.html")
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Cette adresse email est déjà utilisée.")
            return render(request, "register_select.html")
        
        try:
            # Création du compte Django
            compte_django = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Création du profil principal
            profil = Utilisateur.objects.create(
                user=compte_django,
                nom=username,
                email=email,
                role=role,
                localisation=localisation or "Non précisée",
                telephone=telephone
            )
            
            # Création du sous-profil
            if role == "PRODUCTEUR":
                Producteur.objects.create(profil=profil)
            elif role == "COMMERCANT":
                Commercant.objects.create(profil=profil)
            elif role == "TRANSPORTEUR":
                Transporteur.objects.create(profil=profil)
            elif role == "ADMIN":
                Administrateur.objects.create(profil=profil)
            else:
                compte_django.delete()
                messages.error(request, "Rôle non reconnu.")
                return render(request, "register_select.html")
            
            # Connexion automatique
            login(request, compte_django)
            
            # Redirection
            if role == "PRODUCTEUR":
                return redirect("dashboard_producteur")
            elif role == "COMMERCANT":
                return redirect("dashboard_commercant")
            elif role == "TRANSPORTEUR":
                return redirect("dashboard_transporteur")
            elif role == "ADMIN":
                return redirect("dashboard_admin")
                
        except Exception as e:
            messages.error(request, f"Erreur lors de l'inscription : {str(e)}")
    
    return render(request, "register_select.html")

# =========================================================================
# 🌾 2. MODULE PRODUCTEUR
# =========================================================================


@login_required
def dashboard_producteur(request):
    """Tableau de bord du producteur avec alertes de disponibilité"""
    try:
        profil = request.user.utilisateur_profile
    except:
        messages.error(request, "Profil utilisateur introuvable.")
        return redirect("login_select")
    
    # ✅ Vérification du rôle
    if profil.role != "PRODUCTEUR":
        messages.error(request, "Accès réservé aux producteurs.")
        return redirect("login_select")
    
    # ✅ Récupération des messages
    storage = get_messages(request)
    messages_list = list(storage)
    
    try:
        # ✅ Récupération du producteur
        try:
            p = Producteur.objects.get(profil=profil)
        except:
            p = profil.profil_producteur
            
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect("index")
    
    # ✅ Produits du producteur
    mes_produits = Produits.objects.filter(producteur=p).order_by('-id')
    
    # ================================================================
    # 🕐 1. ANNULATION AUTOMATIQUE DES COMMANDES EN ATTENTE > 4H
    # ================================================================
    now = timezone.now()
    seuil_4h = now - timedelta(hours=4)
    
    # ✅ Commandes en attente depuis plus de 4h
    commandes_expirees = Reservation.objects.filter(
        fluxproduit__produit__producteur=p,
        statut_reservation="EN_ATTENTE",
        date_reservation__lte=seuil_4h
    )
    
    for commande in commandes_expirees:
        # ✅ Annulation automatique
        commande.statut_reservation = "ANNULÉE"
        commande.save()
        
        # ✅ Restituer le stock
        if commande.fluxproduit:
            produit = commande.fluxproduit.produit
            produit.quantite_dispo += commande.fluxproduit.quantite
            produit.save()
    
    # ✅ Compter les commandes annulées automatiquement
    annulations_auto = commandes_expirees.count()
    if annulations_auto > 0:
        messages.warning(
            request, 
            f"⏰ {annulations_auto} commande(s) en attente depuis plus de 4h ont été automatiquement annulées."
        )
    
    # ================================================================
    # 📅 2. ALERTES DATE DE DISPONIBILITÉ DÉPASSÉE
    # ================================================================
    today = timezone.now().date()
    alertes_disponibilite = []
    
    for produit in mes_produits:
        # ✅ Si la date de disponibilité existe ET est dépassée ET qu'il y a du stock
        if produit.date_disponibilite and produit.date_disponibilite < today and produit.quantite_dispo > 0:
            # ✅ Calcul du nombre de jours de dépassement
            delta = today - produit.date_disponibilite
            jours_depasses = delta.days
            
            alertes_disponibilite.append({
                'id': produit.id,
                'nom': produit.nom_produit,
                'quantite': produit.quantite_dispo,
                'date_limite': produit.date_disponibilite,
                'jours_depasses': jours_depasses,
                'message': f"La date de disponibilité de '{produit.nom_produit}' est dépassée depuis {jours_depasses} jour(s) !"
            })
    
    # ✅ Toutes les commandes liées à ses produits
    toutes_commandes = Reservation.objects.filter(
        fluxproduit__produit__producteur=p
    ).select_related(
        'fluxproduit__produit',
        'commercant__profil',
        'transporteur__profil'
    ).order_by('-date_reservation')
    
    # ✅ Commandes par statut
    commandes_attente = toutes_commandes.filter(statut_reservation="EN_ATTENTE")
    commandes_validees = toutes_commandes.filter(statut_reservation="VALIDÉE")
    commandes_refusees = toutes_commandes.filter(statut_reservation="REFUSÉE")
    commandes_payees = toutes_commandes.filter(statut_reservation="PAYEE")
    commandes_livrees = toutes_commandes.filter(statut_reservation="LIVREE")
    commandes_annulees = toutes_commandes.filter(statut_reservation="ANNULÉE")
    commandes_transport = toutes_commandes.filter(statut_reservation="PROPOSITION_TRANSPORT")
    
    # ✅ Statistiques
    total_produits = mes_produits.count()
    stock_total = sum(pr.quantite_dispo for pr in mes_produits)
    commandes_attente_count = commandes_attente.count()
    
    # ✅ Calcul du chiffre d'affaires (UNIQUEMENT sur les commandes payées)
    revenus = sum(
        c.fluxproduit.quantite * c.fluxproduit.produit.prix_unitaire
        for c in commandes_payees
    )
    
    # ✅ Alertes reliquat (produits avec stock < 50 kg)
    alertes_reliquat = []
    for produit in mes_produits:
        if produit.quantite_dispo < 50 and produit.quantite_dispo > 0:
            alertes_reliquat.append({
                'id': produit.id,
                'nom': produit.nom_produit,
                'quantite': produit.quantite_dispo,
                'message': f"⚠️ Stock faible : {produit.nom_produit} ({produit.quantite_dispo} kg restants)"
            })
    
    context = {
        # ✅ Messages
        'messages': messages_list,
        
        # ✅ Données principales
        'mes_produits': mes_produits,
        'mes_commandes': toutes_commandes,
        'producteur': p,
        'user': request.user,
        'profil': profil,
        
        # ✅ Statistiques KPI
        'total_produits': total_produits,
        'stock_total': stock_total,
        'commandes_attente_count': commandes_attente_count,
        'revenus': revenus,
        
        # ✅ Alertes
        'alertes_reliquat': alertes_reliquat,
        'alertes_disponibilite': alertes_disponibilite,
        'annulations_auto': annulations_auto,
        
        # ✅ Commandes par statut
        'commandes_attente': commandes_attente,
        'commandes_validees': commandes_validees,
        'commandes_refusees': commandes_refusees,
        'commandes_payees': commandes_payees,
        'commandes_livrees': commandes_livrees,
        'commandes_annulees': commandes_annulees,
        'commandes_transport': commandes_transport,
        
        # ✅ Statistiques détaillées
        'payees_count': commandes_payees.count(),
        'livrees_count': commandes_livrees.count(),
        'validees_count': commandes_validees.count(),
        'refusees_count': commandes_refusees.count(),
        'annulees_count': commandes_annulees.count(),
        'transport_count': commandes_transport.count(),
    }
    
    return render(request, "dashboard_producteur.html", context)


@login_required
def ajouter_produit(request):
    """Ajout d'un nouveau produit"""
    try:
        utilisateur_profil = request.user.utilisateur_profile
        if utilisateur_profil.role != 'PRODUCTEUR':
            messages.error(request, "Vous devez être producteur.")
            return redirect('dashboard_producteur')
        
        try:
            p = Producteur.objects.get(profil=utilisateur_profil)
        except:
            p = utilisateur_profil.profil_producteur
            
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('dashboard_producteur')
    
    if request.method == "POST":
        nom = request.POST.get('nom_produit')
        categorie = request.POST.get('categorie')
        quantite = int(request.POST.get('quantite_dispo', 0))
        prix = float(request.POST.get('prix_unitaire', 0))
        zone = request.POST.get('zone_production')
        date_limite = request.POST.get('date_disponibilite')
        unite_mesure = request.POST.get('unite_mesure', 'kg')
        image = request.FILES.get('image_produit')
        
        # ✅ Création du produit
        produit = Produits.objects.create(
            producteur=p,
            nom_produit=nom,
            categorie=categorie,
            quantite_dispo=quantite,
            prix_unitaire=prix,
            zone_production=zone,
            date_disponibilite=date_limite,
            unite_mesure=unite_mesure,
            image_produit=image
        )
        
        messages.success(request, f"🌾 Le produit '{nom}' a été publié avec succès !")
        return redirect('dashboard_producteur')
    
    return render(request, 'ajouter_produit.html')


@login_required
def voir_stocks(request):
    """Affiche l'inventaire des stocks du producteur"""
    try:
        utilisateur_profil = request.user.utilisateur_profile
        try:
            p = utilisateur_profil.profil_producteur
        except:
            p = Producteur.objects.get(profil=utilisateur_profil)
        
        prods = Produits.objects.filter(producteur=p).order_by('-id')
        
        # ✅ Calcul du stock total
        stock_total = sum(pr.quantite_dispo for pr in prods)
        
        context = {
            'mes_produits': prods,
            'stock_total': stock_total,
            'total_produits': prods.count(),
        }
        return render(request, 'mes_stocks.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('dashboard_producteur')


@login_required
def commandes_recues(request):
    """Affiche les commandes reçues par le producteur"""
    try:
        utilisateur_profil = request.user.utilisateur_profile
        try:
            p = utilisateur_profil.profil_producteur
        except:
            p = Producteur.objects.get(profil=utilisateur_profil)
        
        cmds = Reservation.objects.filter(
            fluxproduit__produit__producteur=p
        ).select_related(
            'fluxproduit__produit',
            'commercant__profil'
        ).order_by('-date_reservation')
        
        # ✅ Statistiques
        en_attente = cmds.filter(statut_reservation="EN_ATTENTE")
        validees = cmds.filter(statut_reservation="VALIDÉE")
        payees = cmds.filter(statut_reservation="PAYEE")
        livrees = cmds.filter(statut_reservation="LIVREE")
        
        context = {
            'mes_commandes': cmds,
            'en_attente_count': en_attente.count(),
            'validees_count': validees.count(),
            'payees_count': payees.count(),
            'livrees_count': livrees.count(),
            'commandes_attente': en_attente,
            'commandes_validees': validees,
            'commandes_payees': payees,
            'commandes_livrees': livrees,
        }
        return render(request, 'commandes_recues.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('dashboard_producteur')


@login_required
def historique_ventes(request):
    """Affiche l'historique complet des ventes"""
    try:
        utilisateur_profil = request.user.utilisateur_profile
        try:
            p = utilisateur_profil.profil_producteur
        except:
            p = Producteur.objects.get(profil=utilisateur_profil)
        
        # ✅ Uniquement les commandes payées ou livrées
        cmds = Reservation.objects.filter(
            fluxproduit__produit__producteur=p
        ).filter(
            statut_reservation__in=["PAYEE", "LIVREE", "CHARGEE", "EN_TRANSIT"]
        ).select_related(
            'fluxproduit__produit',
            'commercant__profil'
        ).order_by('-date_reservation')
        
        # ✅ Calcul du total des ventes
        total_ventes = sum(
            c.fluxproduit.quantite * c.fluxproduit.produit.prix_unitaire
            for c in cmds
        )
        
        context = {
            'mes_commandes': cmds,
            'total_ventes': total_ventes,
            'total_commandes': cmds.count(),
        }
        return render(request, 'historique_ventes.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('dashboard_producteur')


@login_required
def reajuster_stock_produit(request):
    """Réajuster rapidement le stock d'un produit"""
    if request.method == "POST":
        produit_id = request.POST.get('produit_id')
        quantite_a_ajouter = int(request.POST.get('nouvelle_quantite', 0))
        
        if quantite_a_ajouter <= 0:
            messages.error(request, "La quantité doit être supérieure à 0.")
            return redirect('dashboard_producteur')
        
        try:
            produit = get_object_or_404(
                Produits, 
                id=produit_id, 
                producteur__profil=request.user.utilisateur_profile
            )
            produit.quantite_dispo += quantite_a_ajouter
            produit.save()
            
            messages.success(
                request, 
                f"✅ Stock mis à jour ! +{quantite_a_ajouter} kg pour {produit.nom_produit}."
            )
        except Exception as e:
            messages.error(request, f"Erreur lors du réajustement : {str(e)}")
    
    return redirect('dashboard_producteur')


@login_required
def modifier_produit(request, produit_id):
    """Modifier un produit existant"""
    produit = get_object_or_404(
        Produits, 
        id=produit_id, 
        producteur__profil=request.user.utilisateur_profile
    )
    
    if request.method == "POST":
        produit.nom_produit = request.POST.get('nom_produit', produit.nom_produit)
        produit.categorie = request.POST.get('categorie', produit.categorie)
        produit.quantite_dispo = int(request.POST.get('quantite_dispo', produit.quantite_dispo))
        produit.prix_unitaire = float(request.POST.get('prix_unitaire', produit.prix_unitaire))
        produit.zone_production = request.POST.get('zone_production', produit.zone_production)
        produit.date_disponibilite = request.POST.get('date_disponibilite', produit.date_disponibilite)
        produit.unite_mesure = request.POST.get('unite_mesure', produit.unite_mesure)
        
        if request.FILES.get('image_produit'):
            produit.image_produit = request.FILES.get('image_produit')
        
        produit.save()
        
        messages.success(request, f"✅ Le produit {produit.nom_produit} a été modifié.")
        return redirect('dashboard_producteur')
    
    return render(request, 'modifier_produit.html', {'produit': produit})


@login_required
def supprimer_produit(request, produit_id):
    """Supprimer définitivement un produit"""
    try:
        produit = get_object_or_404(
            Produits, 
            id=produit_id, 
            producteur__profil=request.user.utilisateur_profile
        )
        nom_prod = produit.nom_produit
        produit.delete()
        messages.warning(request, f"🗑️ Le produit '{nom_prod}' a été supprimé.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression : {str(e)}")
    
    return redirect('dashboard_producteur')


@login_required
def decider_commande_producteur(request, reservation_id, action):
    """
    Le producteur valide ou refuse la commande
    ✅ Validation : statut passe à "VALIDÉE" (en attente de paiement)
    ❌ Refus : statut passe à "REFUSÉE" et stock restitué
    """
    commande = get_object_or_404(Reservation, id=reservation_id)
    
    # ✅ Vérifier que le producteur est le propriétaire
    try:
        profil = request.user.utilisateur_profile
        p = profil.profil_producteur
        
        if commande.fluxproduit.produit.producteur != p:
            messages.error(request, "Vous n'êtes pas autorisé à gérer cette commande.")
            return redirect("dashboard_producteur")
    except:
        messages.error(request, "Profil producteur introuvable.")
        return redirect("dashboard_producteur")
    
    if action == "valider":
        # ✅ Simple validation sans ajout de montant
        commande.statut_reservation = "VALIDÉE"
        commande.save()
        
        messages.success(
            request,
            "✅ Commande validée ! Le commerçant peut maintenant procéder au paiement."
        )
        
    elif action == "refuser":
        commande.statut_reservation = "REFUSÉE"
        commande.save()
        
        # ✅ Restituer le stock
        if commande.fluxproduit:
            produit = commande.fluxproduit.produit
            produit.quantite_dispo += commande.fluxproduit.quantite
            produit.save()
        
        messages.warning(
            request,
            "❌ Commande refusée. Le stock a été remis en ligne."
        )
    else:
        messages.error(request, "Action non reconnue.")
    
    return redirect("dashboard_producteur")


# =========================================================================
# 🏪 3. MODULE COMMERÇANT
# =========================================================================

@login_required
def dashboard_commercant(request):
    """Tableau de bord du commerçant - Version synchronisée avec le template"""
    try:
        profil = request.user.utilisateur_profile
    except:
        messages.error(request, "Profil utilisateur introuvable.")
        return redirect("login_select")
    
    # ✅ Vérification du rôle
    if profil.role != "COMMERCANT":
        messages.error(request, "Accès réservé aux commerçants.")
        return redirect("login_select")
    
    # ✅ Récupération des messages
    storage = get_messages(request)
    messages_list = list(storage)
    
    try:
        comm_prof = profil.commercant
        
        # ✅ Toutes les commandes du commerçant avec les relations
        mes_commandes = Reservation.objects.filter(
            commercant=comm_prof
        ).select_related(
            'fluxproduit__produit',
            'transporteur__profil'
        ).order_by("-date_reservation")
        
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect("index")
    
    # ✅ Statistiques pour les KPI
    attente_count = mes_commandes.filter(statut_reservation="EN_ATTENTE").count()
    paiement_count = mes_commandes.filter(statut_reservation="VALIDÉE").count()
    offres_transport_count = mes_commandes.filter(statut_reservation="PROPOSITION_TRANSPORT").count()
    
    # ✅ Calcul du total des dépenses (commandes payées)
    commandes_payees = mes_commandes.filter(statut_reservation="PAYEE")
    total_depenses = sum(
        c.fluxproduit.quantite * c.fluxproduit.produit.prix_unitaire
        for c in commandes_payees
    )
    
    # ✅ Commande en cours de livraison pour la carte
    commande_active = mes_commandes.filter(
        statut_reservation__in=["CHARGEE", "EN_TRANSIT", "ACCEPTÉE"]
    ).first()
    
    # ✅ Préparation des données pour la carte
    carte_data = None
    if commande_active:
        flux = commande_active.fluxproduit
        produit = flux.produit
        
        # Récupération des zones
        zone_depart = flux.zone_depart or produit.zone_production or "Bamako"
        zone_arrivee = "Marché de Destination"
        
        # Coordonnées GPS approximatives
        GPS_COMMUNES = {
            'Bamako': [12.639, -8.002],
            'Sikasso': [11.316, -5.666],
            'Ségou': [13.432, -6.266],
            'Mopti': [14.484, -4.183],
            'Koulikoro': [12.863, -7.556],
            'Kati': [12.744, -8.071],
            'Kayes': [14.447, -11.436],
            'Koutiala': [12.392, -5.464],
            'San': [13.300, -4.900],
            'Bougouni': [11.417, -7.483],
            'Niono': [14.250, -5.983]
        }
        
        pos_depart = GPS_COMMUNES.get(zone_depart, [12.639, -8.002])
        pos_arrivee = GPS_COMMUNES.get(zone_arrivee, [11.316, -5.666])
        
        carte_data = {
            'depart': zone_depart,
            'arrivee': zone_arrivee,
            'statut': commande_active.statut_reservation,
            'chauffeur': commande_active.nom_chauffeur or "Non assigné",
            'telephone': commande_active.telephone_chauffeur or "Non renseigné",
            'lat_depart': pos_depart[0],
            'lon_depart': pos_depart[1],
            'lat_arrivee': pos_arrivee[0],
            'lon_arrivee': pos_arrivee[1],
        }
    
    context = {
        # ✅ Messages
        'messages': messages_list,
        
        # ✅ Données principales
        'mes_commandes': mes_commandes,
        'user': request.user,
        'profil': profil,
        'commercant': comm_prof,
        
        # ✅ KPI (pour les cartes statistiques)
        'attente_count': attente_count,
        'paiement_count': paiement_count,
        'offres_transport_count': offres_transport_count,
        'total_depenses': total_depenses,
        
        # ✅ Données pour la carte
        'carte_data': carte_data,
        
        # ✅ Commandes par statut (pour filtrage éventuel)
        'commandes_attente': mes_commandes.filter(statut_reservation="EN_ATTENTE"),
        'commandes_a_payer': mes_commandes.filter(statut_reservation="VALIDÉE"),
        'offres_transport': mes_commandes.filter(statut_reservation="PROPOSITION_TRANSPORT"),
        'commandes_payees': commandes_payees,
        'commandes_livraison': mes_commandes.filter(statut_reservation__in=["CHARGEE", "EN_TRANSIT", "ACCEPTÉE"]),
        'commandes_livrees': mes_commandes.filter(statut_reservation="LIVREE"),
    }
    
    return render(request, "dashboard_commercant.html", context)

@login_required
def passer_commande(request):
    """Passer une nouvelle commande"""
    produit_id = request.GET.get('produit_id') or request.POST.get('produit_id')
    
    if not produit_id:
        messages.error(request, "Aucun produit sélectionné.")
        return redirect('marche_public')
    
    produit = get_object_or_404(Produits, id=produit_id)
    
    if request.method == "POST":
        quantite_demandee = int(request.POST.get('quantite_achat', 1))
        
        if quantite_demandee > produit.quantite_dispo:
            messages.error(request, "Stock insuffisant.")
            return redirect('marche_public')
        
        try:
            commercant_profil = request.user.utilisateur_profile.commercant
        except:
            messages.error(request, "Profil commerçant non configuré.")
            return redirect('marche_public')
        
        # Création du flux
        flux = FluxProduit.objects.create(
            produit=produit,
            quantite=quantite_demandee,
            zone_depart=produit.zone_production or "Zone Producteur",
            zone_arrivee="Marché de Destination"
        )
        
        # ✅ Création de la réservation en "EN_ATTENTE"
        Reservation.objects.create(
            commercant=commercant_profil,
            fluxproduit=flux,
            quantite=quantite_demandee,
            statut_reservation="EN_ATTENTE",
            date_reservation=timezone.now()
        )
        
        # ✅ Déduction du stock
        produit.quantite_dispo -= quantite_demandee
        produit.save()
        
        messages.success(
            request, 
            "🚀 Votre commande a été envoyée ! Attendez la validation du producteur."
        )
        return redirect('dashboard_commercant')
    
    return render(request, 'passer_commande.html', {'produit': produit})

@login_required
def zone_paiement(request, reservation_id):
    """
    Zone de paiement pour une commande validée
    ✅ Accessible UNIQUEMENT si statut = "VALIDÉE"
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # ✅ Vérification : le commerçant ne peut payer que si la commande est validée
    if reservation.statut_reservation != "VALIDÉE":
        messages.error(
            request, 
            "Cette commande n'est pas encore validée par le producteur ou a déjà été payée."
        )
        return redirect("dashboard_commercant")
    
    flux = reservation.fluxproduit
    produit = flux.produit
    total = flux.quantite * produit.prix_unitaire
    
    if request.method == "POST":
        mode_paiement = request.POST.get("methode", "Orange Money")
        
        # Création du paiement
        Paiement.objects.create(
            reservation=reservation,
            montant_paiement=total,
            mode_paiement=mode_paiement,
            transaction_id=f"TRX-{int(timezone.now().timestamp())}",
            date_paiement=timezone.now(),
            statut="VALIDE"
        )
        
        # ✅ Passage en "PAYEE" après paiement
        reservation.statut_reservation = "PAYEE"
        reservation.save()
        
        messages.success(
            request,
            "💳 Paiement effectué avec succès ! La commande est en attente de livraison."
        )
        
        return redirect("recu_paiement", commande_id=reservation.id)
    
    context = {
        "produit": produit,
        "reservation": reservation,
        "montant": total,
        "flux": flux,
    }
    return render(request, "zone_paiement.html", context)

@login_required
def recu_paiement(request, commande_id):
    """Affiche le reçu de paiement"""
    commande = get_object_or_404(Reservation, id=commande_id)
    
    try:
        paiement = Paiement.objects.get(reservation=commande)
    except Paiement.DoesNotExist:
        messages.error(request, "Aucun paiement trouvé pour cette commande.")
        return redirect("dashboard_commercant")
    
    context = {
        'commande': commande,
        'paiement': paiement,
        'produit': commande.fluxproduit.produit,
        'flux': commande.fluxproduit,
        'montant_total': commande.fluxproduit.quantite * commande.fluxproduit.produit.prix_unitaire,
    }
    return render(request, 'recu_paiement.html', context)

@login_required
def annuler_commande(request, reservation_id):
    """Annuler une commande"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # ✅ Vérifier que le commerçant est le propriétaire
    if not hasattr(request.user, "utilisateur_profile") or \
       not hasattr(request.user.utilisateur_profile, "commercant"):
        messages.error(request, "Vous devez être connecté en tant que commerçant.")
        return redirect("login_select")
    
    if reservation.commercant != request.user.utilisateur_profile.commercant:
        messages.error(request, "Vous n'êtes pas autorisé à annuler cette commande.")
        return redirect("dashboard_commercant")
    
    # ✅ Vérifier que la commande peut être annulée
    if reservation.statut_reservation in ["ANNULÉE", "LIVREE", "PAYEE"]:
        messages.error(request, "❌ Cette commande ne peut plus être annulée.")
        return redirect("dashboard_commercant")
    
    # ✅ Annulation
    reservation.statut_reservation = "ANNULÉE"
    reservation.save()
    
    # ✅ Restituer le stock si la commande n'est pas encore payée
    if reservation.statut_reservation != "PAYEE" and reservation.fluxproduit:
        produit = reservation.fluxproduit.produit
        produit.quantite_dispo += reservation.fluxproduit.quantite
        produit.save()
    
    messages.success(request, "✅ Commande annulée avec succès.")
    return redirect("dashboard_commercant")

@login_required
def decider_offre_transport(request, reservation_id, decision):
    """Accepter ou refuser une offre de transport"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if decision == "accepter":
        reservation.statut_reservation = "ACCEPTÉE"
        reservation.save()
        messages.success(
            request,
            "✅ Offre acceptée. La livraison est maintenant active."
        )
    elif decision == "refuser":
        reservation.statut_reservation = "PAYEE"
        reservation.transporteur = None
        reservation.nom_chauffeur = None
        reservation.telephone_chauffeur = None
        reservation.type_vehicule = None
        reservation.prix_transport_propose = 0
        reservation.save()
        messages.warning(request, "Offre refusée.")
    
    return redirect("dashboard_commercant")

# =========================================================================
# 🚛 4. MODULE TRANSPORTEUR
# =========================================================================

@login_required
def dashboard_transporteur(request):
    """Tableau de bord du transporteur"""
    try:
        profil = request.user.utilisateur_profile
    except:
        messages.error(request, "Profil utilisateur introuvable.")
        return redirect("login_select")
    
    # ✅ Vérification du rôle
    if profil.role != "TRANSPORTEUR":
        messages.error(request, "Accès réservé aux transporteurs.")
        return redirect("login_select")
    
    # ✅ Récupération des messages
    storage = get_messages(request)
    messages_list = list(storage)
    
    try:
        # ✅ Récupération du transporteur
        try:
            transporteur = Transporteur.objects.get(profil=profil)
        except:
            transporteur = profil.transporteur
            
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect("index")
    
    # ✅ Uniquement les commandes PAYEES sont disponibles pour les transporteurs
    missions = Reservation.objects.filter(
        statut_reservation="PAYEE"
    ).select_related(
        'fluxproduit__produit',
        'commercant__profil'
    ).order_by('-date_reservation')
    
    # ✅ Commandes en cours (acceptées par le transporteur)
    actives = Reservation.objects.filter(
        transporteur=transporteur,
        statut_reservation__in=['ACCEPTÉE', 'CHARGEE', 'EN_TRANSIT']
    ).select_related(
        'fluxproduit__produit',
        'commercant__profil'
    ).order_by('-date_reservation')
    
    # ✅ Historique des livraisons terminées
    historique = Reservation.objects.filter(
        transporteur=transporteur,
        statut_reservation='LIVREE'
    ).select_related(
        'fluxproduit__produit',
        'commercant__profil'
    ).order_by('-date_reservation')
    
    # ✅ Mes offres envoyées (PROPOSITION_TRANSPORT)
    mes_offres = Reservation.objects.filter(
        transporteur=transporteur,
        statut_reservation='PROPOSITION_TRANSPORT'
    ).select_related(
        'fluxproduit__produit',
        'commercant__profil'
    ).order_by('-date_reservation')
    
    # ✅ Calcul des revenus (uniquement sur les livraisons terminées)
    total_revenus = sum(
        r.prix_transport_propose or 0
        for r in historique
    )
    
    context = {
        'messages': messages_list,
        'user': request.user,
        'profil': profil,
        'transporteur': transporteur,
        
        # ✅ Données principales (les noms correspondent au template)
        'missions': missions,          # ✅ Pour "Fret Disponible"
        'actives': actives,            # ✅ Pour "Livraisons Actives"
        'historique': historique,      # ✅ Pour "Courses Clôturées"
        'mes_offres': mes_offres,      # ✅ Pour "Mes Offres"
        
        # ✅ Compteurs
        'missions_count': missions.count(),
        'actives_count': actives.count(),
        'historique_count': historique.count(),
        'mes_offres_count': mes_offres.count(),
        
        # ✅ Revenus
        'total_revenus': total_revenus,
    }
    
    return render(request, "dashboard_transporteur.html", context)


@login_required
def soumettre_offre_transport(request, reservation_id):
    """Soumettre une offre de transport"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # ✅ Vérifier que la commande est payée
    if reservation.statut_reservation != "PAYEE":
        messages.error(request, "Cette commande n'est pas disponible pour le transport.")
        return redirect("dashboard_transporteur")
    
    if request.method == "POST":
        nom_chauffeur = request.POST.get("nom_chauffeur")
        telephone_chauffeur = request.POST.get("telephone_chauffeur")
        type_vehicule = request.POST.get("type_vehicule")
        prix_transport = request.POST.get("prix_transport")
        
        if not all([nom_chauffeur, telephone_chauffeur, type_vehicule, prix_transport]):
            messages.error(request, "Tous les champs sont obligatoires.")
            return redirect("dashboard_transporteur")
        
        try:
            transporteur = Transporteur.objects.get(profil=request.user.utilisateur_profile)
            reservation.transporteur = transporteur
            reservation.nom_chauffeur = nom_chauffeur
            reservation.telephone_chauffeur = telephone_chauffeur
            reservation.type_vehicule = type_vehicule
            reservation.prix_transport_propose = float(prix_transport)
            reservation.statut_reservation = "PROPOSITION_TRANSPORT"
            reservation.save()
            
            messages.success(request, "✅ Offre de transport envoyée avec succès.")
        except Exception as e:
            messages.error(request, f"Erreur : {str(e)}")
    
    return redirect("dashboard_transporteur")


@login_required
def changer_statut_livraison(request, reservation_id, statut):
    """Changer le statut d'une livraison"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # ✅ Vérifier que le transporteur est le propriétaire
    try:
        transporteur = Transporteur.objects.get(profil=request.user.utilisateur_profile)
        if reservation.transporteur != transporteur:
            messages.error(request, "Vous n'êtes pas autorisé à modifier cette livraison.")
            return redirect("dashboard_transporteur")
    except:
        messages.error(request, "Profil transporteur introuvable.")
        return redirect("dashboard_transporteur")
    
    # ✅ Statuts autorisés
    statuts_autorises = ["CHARGEE", "EN_TRANSIT", "LIVREE"]
    
    if statut in statuts_autorises:
        reservation.statut_reservation = statut
        reservation.save()
        
        # ✅ Message spécifique selon le statut
        messages_success = {
            "CHARGEE": "📦 La cargaison a été chargée.",
            "EN_TRANSIT": "🚛 La cargaison est en transit.",
            "LIVREE": "✅ La cargaison a été livrée avec succès !"
        }
        messages.success(request, messages_success.get(statut, f"Statut modifié : {statut}"))
    else:
        messages.error(request, "Statut invalide.")
    
    return redirect('dashboard_transporteur')




# =========================================================================
# 🛡️ 5. MODULE ADMINISTRATEUR
# =========================================================================

@login_required
def dashboard_admin(request):
    """Tableau de bord de l'administrateur"""
    try:
        profil = request.user.utilisateur_profile
    except:
        messages.error(request, "Profil utilisateur introuvable.")
        return redirect("login_select")
    
    if profil.role != "ADMIN":
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect("login_select")
    
    storage = get_messages(request)
    messages_list = list(storage)
    
    # ✅ Statistiques générales
    context = {
        'messages_list': messages_list,
        'total_utilisateurs': Utilisateur.objects.count(),
        'total_producteurs': Producteur.objects.count(),
        'total_commercants': Commercant.objects.count(),
        'total_transporteurs': Transporteur.objects.count(),
        'total_produits': Produits.objects.count(),
        'total_reservations': Reservation.objects.count(),
        'total_paiements': Paiement.objects.count(),
        'total_missions': Mission.objects.count(),
        'total_livraisons': Livraison.objects.count(),
        'total_litiges': Litige.objects.count(),
        
        # ✅ Commandes par statut
        'en_attente_count': Reservation.objects.filter(statut_reservation="EN_ATTENTE").count(),
        'validees_count': Reservation.objects.filter(statut_reservation="VALIDÉE").count(),
        'payees_count': Reservation.objects.filter(statut_reservation="PAYEE").count(),
        'livrees_count': Reservation.objects.filter(statut_reservation="LIVREE").count(),
        'refusees_count': Reservation.objects.filter(statut_reservation="REFUSÉE").count(),
        'annulees_count': Reservation.objects.filter(statut_reservation="ANNULÉE").count(),
    }
    
    return render(request, 'dashboard_admin.html', context)

# =========================================================================
# 🔀 6. PASSERELLE D'AIGUILLAGE
# =========================================================================

@login_required
def portal_aiguillage(request):
    """Redirige l'utilisateur vers son dashboard approprié"""
    try:
        profil = request.user.utilisateur_profile
        role = profil.role
        
        if role == "PRODUCTEUR":
            return redirect("dashboard_producteur")
        elif role == "COMMERCANT":
            return redirect("dashboard_commercant")
        elif role == "TRANSPORTEUR":
            return redirect("dashboard_transporteur")
        elif role == "ADMIN":
            return redirect("dashboard_admin")
        else:
            return redirect("index")
            
    except:
        return redirect("login_select")