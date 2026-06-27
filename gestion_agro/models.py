from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Utilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="utilisateur_profile")
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=[
        ("PRODUCTEUR", "Producteur"),
        ("COMMERCANT", "Commerçant"),
        ("TRANSPORTEUR", "Transporteur"),
        ("ADMIN", "Administrateur"),
    ])
    localisation = models.CharField(max_length=150, blank=True, default="Non précisée")
    telephone = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"{self.nom} ({self.role})"


class Producteur(models.Model):
    profil = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, primary_key=True, related_name='profil_producteur')

    def __str__(self):
        return self.profil.nom


class Commercant(models.Model):
    profil = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name="commercant", primary_key=True)
    entreprise = models.CharField(max_length=150, blank=True, null=True)
    adresse_boutique = models.CharField(max_length=250, blank=True, null=True)

    def __str__(self):
        return self.profil.nom


class Transporteur(models.Model):
    profil = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name="transporteur", primary_key=True)
    type_vehicule = models.CharField(max_length=80, blank=True, null=True)
    capacite_transport_int = models.IntegerField(default=0)
    disponibilite = models.BooleanField(default=True)
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.profil.nom} - {self.type_vehicule or 'Transporteur'}"


class Administrateur(models.Model):
    profil = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name="administrateur", primary_key=True)

    def __str__(self):
        return self.profil.nom


class Produits(models.Model):
    producteur = models.ForeignKey(Producteur, on_delete=models.CASCADE, related_name="produits")
    nom_produit = models.CharField(max_length=150)
    categorie = models.CharField(max_length=80)
    quantite_dispo = models.IntegerField(default=0)
    unite_mesure = models.CharField(max_length=20, default="kg")
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    image_produit = models.ImageField(upload_to="produits/", blank=True, null=True)
    zone_production = models.CharField(max_length=150, blank=True, null=True)
    date_disponibilite = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.nom_produit


class FluxProduit(models.Model):
    produit = models.ForeignKey(Produits, on_delete=models.CASCADE)
    zone_depart = models.CharField(max_length=150)
    zone_arrivee = models.CharField(max_length=150)
    quantite = models.IntegerField()
    date_flux = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Flux {self.id} - {self.produit.nom_produit}"



class Reservation(models.Model):

    STATUTS = [
         ("EN_ATTENTE", "En attente"),
    ("VALIDEE", "Validée"),
    ("PAYEE", "Payée"),
    ("PROPOSITION_TRANSPORT", "Proposition transport"),
    ("CHARGEE", "Chargée"),
    ("EN_TRANSIT", "En transit"),
    ("LIVREE", "Livrée"),
    ("ANNULEE", "Annulée"),
    ]

    fluxproduit = models.ForeignKey(
        FluxProduit,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    commercant = models.ForeignKey(
        Commercant,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    transporteur = models.ForeignKey(
        Transporteur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations"
    )

    quantite = models.PositiveIntegerField()

    statut_reservation = models.CharField(
        max_length=30,
        choices=STATUTS,
        default="EN_ATTENTE"
    )

    date_reservation = models.DateTimeField(auto_now_add=True)

    # Informations du chauffeur
    nom_chauffeur = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    telephone_chauffeur = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    type_vehicule = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    prix_transport_propose = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"Réservation N°{self.id}"



class Paiement(models.Model):

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="paiements"
    )

    montant_paiement = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    mode_paiement = models.CharField(max_length=30)

    transaction_id = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )

    date_paiement = models.DateTimeField(
        auto_now_add=True
    )

    statut = models.CharField(
        max_length=20,
        default="EN_ATTENTE"
    )

    def __str__(self):
        return f"Paiement {self.id}"

class Caution(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="cautions", blank=True, null=True)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE, related_name="cautions", blank=True, null=True)
    montant_caution = models.DecimalField(max_digits=12, decimal_places=2)
    etat_caution = models.CharField(max_length=20, default="ACTIVE")
    date_depot = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Caution {self.id}"


class Mission(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="missions")
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE, related_name="missions")
    statut_mission = models.CharField(max_length=20, default="EN_ATTENTE")
    date_assignation = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Mission {self.id} - {self.transporteur.profil.nom}"


class Livraison(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="livraisons")
    date_depart_prevue = models.DateTimeField(blank=True, null=True)
    date_arrivee_prevue = models.DateTimeField(blank=True, null=True)
    etat_livraison = models.CharField(max_length=20, default="EN_ATTENTE")
    observations = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Livraison {self.id}"


class Litige(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="litiges")
    motif = models.TextField()
    statut_litige = models.CharField(max_length=20, default="OUVERT")
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Litige {self.id}"


class Statistique(models.Model):
    id_statistique = models.AutoField(primary_key=True)
    total_missions = models.IntegerField(default=0)
    total_litiges = models.IntegerField(default=0)
    chiffre_affaires_global = models.FloatField(default=0.0)
    date_mise_a_jour = models.DateTimeField(auto_now=True)