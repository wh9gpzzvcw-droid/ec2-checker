"""
=============================================================================
Modélisation d'éléments en béton armé selon l'Eurocode 2 (EN 1992-1-1)
Modèle du treillis de Ritter-Mörsch pour l'effort tranchant
=============================================================================
"""

import math
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# DATACLASSES MATÉRIAUX
# =============================================================================

@dataclass
class Beton:
    """
    Caractéristiques du béton selon EN 1992-1-1, §3.1.

    fck      : Résistance caractéristique cylindrique [MPa]
    fck_cube : Résistance caractéristique cubique     [MPa]
    gamma_c  : Coefficient partiel matériau béton     [-]  (§2.4.2.4 : γc = 1.5)
    """
    fck: float
    fck_cube: float
    gamma_c: float = 1.5

    @property
    def fcd(self) -> float:
        """fcd = αcc · fck / γc  –  EC2 Eq.(3.15), αcc = 1.0"""
        return 1.0 * self.fck / self.gamma_c

    @property
    def fcm(self) -> float:
        """fcm = fck + 8  –  EC2 Tableau 3.1"""
        return self.fck + 8.0

    @property
    def fctm(self) -> float:
        """
        Résistance moyenne en traction [MPa]  –  EC2 Tableau 3.1
            fck ≤ 50 MPa : fctm = 0.30 · fck^(2/3)
            fck > 50 MPa : fctm = 2.12 · ln(1 + fcm/10)
        """
        if self.fck <= 50:
            return 0.30 * (self.fck ** (2.0 / 3.0))
        return 2.12 * math.log(1.0 + self.fcm / 10.0)

    @property
    def Ecm(self) -> float:
        """Ecm = 22 · (fcm/10)^0.3  [GPa]  –  EC2 Tableau 3.1"""
        return 22.0 * ((self.fcm / 10.0) ** 0.3)

    def __repr__(self) -> str:
        return (f"Beton(fck={self.fck} MPa | fcd={self.fcd:.2f} MPa | "
                f"fctm={self.fctm:.2f} MPa | Ecm={self.Ecm:.1f} GPa)")


@dataclass
class Acier:
    """
    Caractéristiques de l'acier d'armature selon EN 1992-1-1, §3.2.

    fyk     : Limite élastique caractéristique [MPa]
    Es      : Module d'élasticité              [GPa]  (§3.2.7 : Es = 200 GPa)
    gamma_s : Coefficient partiel matériau     [-]   (§2.4.2.4 : γs = 1.15)
    """
    fyk: float
    Es: float = 200.0
    gamma_s: float = 1.15

    @property
    def fyd(self) -> float:
        """fyd = fyk / γs  –  EC2 §3.2.7"""
        return self.fyk / self.gamma_s

    def __repr__(self) -> str:
        return f"Acier(fyk={self.fyk} MPa | fyd={self.fyd:.2f} MPa)"


# =============================================================================
# CLASSE MÈRE – ÉLÉMENT EN BÉTON ARMÉ
# =============================================================================

class ElementBetonArme:
    """
    Classe de base centralisant matériaux et coefficients partiels EC2.

    beton   : Instance Beton
    acier   : Instance Acier
    c_nom   : Enrobage nominal [mm]  –  EC2 §4
    """

    def __init__(self, beton: Beton, acier: Acier, c_nom: float = 35.0):
        self.beton   = beton
        self.acier   = acier
        self.c_nom   = c_nom
        self.gamma_G = 1.35   # Actions permanentes  –  EN 1990 Tableau A1.2(B)
        self.gamma_Q = 1.50   # Actions variables

    def combinaison_ELU(self, G_k: float, Q_k: float) -> float:
        """Ed = γG·Gk + γQ·Qk  –  EN 1990 Eq.(6.10)"""
        return self.gamma_G * G_k + self.gamma_Q * Q_k


# =============================================================================
# CLASSE FILLE – LONGRINE
# =============================================================================

class Longrine(ElementBetonArme):
    """
    Longrine (poutre de fondation) à section rectangulaire – EC2 §6.2.3.

    Paramètres géométriques :
        b        : Largeur de section              [mm]
        h        : Hauteur totale                  [mm]

    Armatures longitudinales :
        n_long   : Nombre de barres longitudinales
        phi_long : Diamètre des barres long.       [mm]
        Asl      : Aire d'acier tendu (calculée si None) [mm²]

    Armatures transversales :
        phi_etr  : Diamètre des étriers            [mm]
        n_bras   : Nombre de bras (2 pour cadre simple)
        s        : Espacement des étriers           [mm]

    Modèle treillis :
        theta    : Angle bielle comprimée           [°]  –  21.8° ≤ θ ≤ 45°
    """

    def __init__(
        self,
        beton: Beton,
        acier: Acier,
        b: float,
        h: float,
        n_long: int,
        phi_long: float,
        Asl: Optional[float]  = None,
        phi_etr: float        = 8.0,
        n_bras: int           = 2,
        s: float              = 150.0,
        theta: float          = 35.0,
        c_nom: float          = 35.0,
    ):
        super().__init__(beton, acier, c_nom)

        self.b        = b
        self.h        = h
        self.phi_long = phi_long
        self.phi_etr  = phi_etr
        self.n_long   = n_long
        self.n_bras   = n_bras
        self.s        = s

        # Hauteur utile : d = h - c_nom - φ_étrier - φ_long/2
        self.d = h - c_nom - phi_etr - phi_long / 2.0

        # Aire d'acier longitudinal
        self.Asl = Asl if Asl is not None else (
            n_long * math.pi * (phi_long ** 2) / 4.0
        )

        # Aire d'un étrier (tous bras)
        self.Asw = n_bras * math.pi * (phi_etr ** 2) / 4.0

        if not (21.8 <= theta <= 45.0):
            raise ValueError(f"θ = {theta}° hors limites EC2 [21.8° ; 45°].")
        self.theta = theta

    # ------------------------------------------------------------------
    # Propriétés dérivées
    # ------------------------------------------------------------------

    @property
    def rho_l(self) -> float:
        """ρl = Asl / (bw·d)  ≤ 0.02  –  EC2 §6.2.2(1)"""
        return min(self.Asl / (self.b * self.d), 0.02)

    @property
    def Asw_sur_s(self) -> float:
        """Densité d'armatures transversales Asw/s [mm²/mm]"""
        return self.Asw / self.s

    # ------------------------------------------------------------------
    # Vérification cisaillement
    # ------------------------------------------------------------------

    def check_shear(
        self,
        VEd: float,
        NEd: float   = 0.0,
        verbose: bool = True,
    ) -> dict:
        """
        Vérification de l'effort tranchant  –  EC2 §6.2.3.

        ──────────────────────────────────────────────────────────────────
        MODÈLE DU TREILLIS DE RITTER-MÖRSCH GÉNÉRALISÉ
        ──────────────────────────────────────────────────────────────────
        La poutre est assimilée à un treillis :
          • Membrure supérieure comprimée  → béton
          • Membrure inférieure tendue     → armatures longitudinales
          • Montants                       → étriers (inclinés à α = 90°)
          • Diagonales comprimées          → bielles béton inclinées à θ

        Deux vérifications EC2 §6.2.3 :
          (1) VEd ≤ VRd,max  →  résistance des bielles comprimées
          (2) VEd ≤ VRd,s   →  plastification des armatures transversales

        ──────────────────────────────────────────────────────────────────
        FORMULES
        ──────────────────────────────────────────────────────────────────

        z   = 0.9·d                        bras de levier interne [mm]
        ν1  = 0.6·(1 − fck/250)            réduction béton fissuré  –  Eq.(6.6N)
        αcw = 1.0 (sans précontrainte)     –  §6.2.3(3) Note 1

        VRd,max = αcw · bw · z · ν1 · fcd / (cotθ + tanθ)   –  Eq.(6.9)
        VRd,s   = (Asw/s) · z · fywd · cotθ                  –  Eq.(6.8)

        ρw,min  = 0.08·√fck / fyk   –  taux minimal étriers  –  Eq.(9.5N)
        sl,max  = 0.75·d            –  espacement maximal     –  §9.2.2(6)

        Paramètres :
            VEd   : Effort tranchant de calcul  [kN]
            NEd   : Effort normal de calcul     [kN]  (+ = compression)
            verbose : Impression du rapport si True

        Retourne :
            dict contenant toutes les grandeurs de calcul et les statuts.
        """

        # ── Géométrie ─────────────────────────────────────────────────────
        bw = self.b
        d  = self.d
        z  = 0.9 * d            # Bras de levier interne [mm]

        # ── Angle treillis ────────────────────────────────────────────────
        theta_rad = math.radians(self.theta)
        cot_theta = math.cos(theta_rad) / math.sin(theta_rad)
        tan_theta = math.tan(theta_rad)

        # ── Matériaux ─────────────────────────────────────────────────────
        fcd  = self.beton.fcd
        fck  = self.beton.fck
        fywd = self.acier.fyd   # Résistance de calcul étriers [MPa]

        # ── Coefficient αcw (EC2 §6.2.3(3) Note 1) ───────────────────────
        Ac       = bw * self.h
        sigma_cp = (NEd * 1000.0) / Ac if NEd != 0 else 0.0  # [MPa]
        if sigma_cp <= 0:
            alpha_cw = 1.0
        elif sigma_cp <= 0.25 * fcd:
            alpha_cw = 1.0 + sigma_cp / fcd
        elif sigma_cp <= 0.5 * fcd:
            alpha_cw = 1.25
        else:
            alpha_cw = max(2.5 * (1.0 - sigma_cp / fcd), 0.0)

        # ── ν1 : réduction résistance béton fissuré (Eq. 6.6N) ───────────
        nu1 = 0.6 * (1.0 - fck / 250.0)

        # ════════════════════════════════════════════════════════════════
        # VRd,max  –  Eq.(6.9)
        # VRd,max = αcw · bw · z · ν1 · fcd / (cotθ + tanθ)
        # Le dénominateur = 1/(sinθ·cosθ) représente la sollicitation
        # de la bielle diagonale : plus θ est petit, plus VRd,max croît.
        # ════════════════════════════════════════════════════════════════
        VRd_max   = (alpha_cw * bw * z * nu1 * fcd) / (cot_theta + tan_theta)
        VRd_max_kN = VRd_max / 1000.0

        # ════════════════════════════════════════════════════════════════
        # VRd,s  –  Eq.(6.8)
        # VRd,s = (Asw/s) · z · fywd · cotθ
        # Sur une longueur z·cotθ il y a (z·cotθ/s) étriers actifs,
        # chacun reprenant Asw·fywd → force totale = (Asw/s)·z·fywd·cotθ
        # ════════════════════════════════════════════════════════════════
        VRd_s    = self.Asw_sur_s * z * fywd * cot_theta
        VRd_s_kN = VRd_s / 1000.0

        # ── Taux minimal armatures transversales (Eq. 9.5N) ──────────────
        rho_w_min = (0.08 * math.sqrt(fck)) / self.acier.fyk
        rho_w     = self.Asw / (self.s * bw)   # α = 90° → sin(α) = 1

        # ── Espacement maximal (§9.2.2(6)) ───────────────────────────────
        s_max = 0.75 * d

        # ── Taux d'utilisation ────────────────────────────────────────────
        tau_max = VEd / VRd_max_kN
        tau_s   = VEd / VRd_s_kN

        # ── Statuts ───────────────────────────────────────────────────────
        ok_VRd_max = tau_max <= 1.0
        ok_VRd_s   = tau_s   <= 1.0
        ok_rho_w   = rho_w   >= rho_w_min
        ok_s_max   = self.s  <= s_max
        ok_global  = ok_VRd_max and ok_VRd_s and ok_rho_w and ok_s_max

        return {
            # Efforts
            "VEd_kN"        : VEd,
            "VRd_max_kN"    : round(VRd_max_kN, 2),
            "VRd_s_kN"      : round(VRd_s_kN,   2),
            # Taux d'utilisation
            "tau_VRd_max"   : round(tau_max, 4),
            "tau_VRd_s"     : round(tau_s,   4),
            # Statuts
            "ok_VRd_max"    : ok_VRd_max,
            "ok_VRd_s"      : ok_VRd_s,
            "ok_rho_w_min"  : ok_rho_w,
            "ok_s_max"      : ok_s_max,
            "ok_global"     : ok_global,
            # Paramètres intermédiaires
            "nu1"           : round(nu1,       4),
            "alpha_cw"      : round(alpha_cw,  4),
            "z_mm"          : round(z,         1),
            "cot_theta"     : round(cot_theta, 4),
            "sigma_cp_MPa"  : round(sigma_cp,  3),
            "rho_w"         : round(rho_w,     6),
            "rho_w_min"     : round(rho_w_min, 6),
            "s_max_mm"      : round(s_max,     1),
            "fcd_MPa"       : round(fcd,       2),
            "fywd_MPa"      : round(fywd,      2),
            "d_mm"          : round(d,         1),
            "Asw_mm2"       : round(self.Asw,  2),
        }

    def scan_theta(
        self,
        VEd: float,
        NEd: float = 0.0,
        pas: float = 0.5,
    ) -> list[dict]:
        """
        Balaye l'angle θ de 21.8° à 45° et retourne les taux d'utilisation
        pour chaque valeur.  Utilisé pour le graphique de sensibilité.

        Paramètres :
            VEd : Effort tranchant de calcul [kN]
            NEd : Effort normal de calcul    [kN]
            pas : Pas angulaire              [°]

        Retourne :
            Liste de dict  { "theta", "tau_VRd_max", "tau_VRd_s", "ok" }
        """
        resultats = []
        theta_original = self.theta

        angles = [round(21.8 + i * pas, 2)
                  for i in range(int((45.0 - 21.8) / pas) + 2)
                  if 21.8 + i * pas <= 45.0]

        for theta_t in angles:
            self.theta = theta_t
            r = self.check_shear(VEd, NEd, verbose=False)
            resultats.append({
                "theta"       : theta_t,
                "tau_VRd_max" : r["tau_VRd_max"],
                "tau_VRd_s"   : r["tau_VRd_s"],
                "ok"          : r["ok_VRd_max"] and r["ok_VRd_s"],
            })

        self.theta = theta_original
        return resultats

    # ------------------------------------------------------------------
    # Vérification flexion — EC2 §6.1
    # ------------------------------------------------------------------

    def check_bending(
        self,
        MEd: float,
        verbose: bool = True,
    ) -> dict:
        """
        Vérification de la flexion simple rectangulaire – EC2 §6.1.

        ──────────────────────────────────────────────────────────────────
        MÉTHODE DES CONTRAINTES RECTANGULAIRES ÉQUIVALENTES (diagramme
        rectangulaire simplifié EC2 §3.1.7)
        ──────────────────────────────────────────────────────────────────

        Hypothèses :
          • Section rectangulaire b × h, armatures tendues Asl
          • Béton  : bloc rectangulaire de hauteur x·λ, contrainte η·fcd
            λ = 0.8  (fck ≤ 50 MPa)   –  EC2 §3.1.7(3)
            η = 1.0  (fck ≤ 50 MPa)   –  EC2 §3.1.7(3)
          • Acier tendu : contrainte fyd (plastification)

        Équilibre des forces horizontales (armatures seules en traction) :
            Fc = η·fcd · b · λ·x  =  Ft = Asl · fyd
            → x = Asl·fyd / (η·fcd·b·λ)

        Moment résistant :
            MRd = Asl·fyd · (d − λ·x/2)   –  bras de levier interne

        Vérification pivot A (déformation limite acier) :
            εs = εcu3 · (d − x) / x ≥ 0  (section sous-armée si εs > 0)
            εcu3 = 3.5‰  (fck ≤ 50 MPa)   –  EC2 Tableau 3.1

        Taux d'armature maximal (§9.2.1.1) :
            Asl ≤ 0.04·Ac

        Paramètres :
            MEd   : Moment fléchissant de calcul [kN·m]
            verbose : Rapport si True

        Retourne :
            dict contenant toutes les grandeurs et statuts.
        """

        bw  = self.b
        d   = self.d
        fcd = self.beton.fcd
        fyd = self.acier.fyd
        fck = self.beton.fck

        # Coefficients bloc rectangulaire
        lam = 0.8 if fck <= 50 else (0.8 - (fck - 50) / 400.0)
        eta = 1.0 if fck <= 50 else (1.0 - (fck - 50) / 200.0)

        # Hauteur de l'axe neutre (m vert équilibre des forces)
        x = (self.Asl * fyd) / (eta * fcd * bw * lam)

        # Vérification domaine (section sous-armée)
        eps_cu3 = 3.5e-3          # déformation ultime béton EC2 Tab.3.1
        eps_s   = eps_cu3 * (d - x) / x if x > 0 else float("inf")
        eps_yd  = fyd / (self.acier.Es * 1000.0)   # Es en GPa → MPa
        sous_arme = eps_s >= eps_yd                 # pivot A ou B

        # Moment résistant [N·mm] puis [kN·m]
        MRd_Nmm  = self.Asl * fyd * (d - lam * x / 2.0)
        MRd_kNm  = MRd_Nmm / 1e6

        # Moment réduit (μ = MEd / (η·fcd·b·d²))
        MEd_Nmm  = MEd * 1e6
        mu_Ed    = MEd_Nmm  / (eta * fcd * bw * d**2)
        mu_Rd    = MRd_Nmm  / (eta * fcd * bw * d**2)

        # Taux d'armature maximal §9.2.1.1
        Asl_max  = 0.04 * bw * self.h
        ok_asl   = self.Asl <= Asl_max

        # Taux d'utilisation et statuts
        tau_M    = MEd / MRd_kNm if MRd_kNm > 0 else float("inf")
        ok_MRd   = tau_M <= 1.0
        ok_global = ok_MRd and ok_asl and sous_arme

        if verbose:
            print(f"=== Vérification Flexion EC2 §6.1 ===")
            print(f"  d          = {d:.1f} mm")
            print(f"  x (axe n.) = {x:.1f} mm")
            print(f"  MRd        = {MRd_kNm:.2f} kN·m")
            print(f"  MEd        = {MEd:.2f} kN·m")
            print(f"  τ = MEd/MRd= {tau_M:.3f}  {'✓' if ok_MRd else '✗'}")

        return {
            # Efforts
            "MEd_kNm"     : MEd,
            "MRd_kNm"     : round(MRd_kNm, 2),
            # Taux
            "tau_MRd"     : round(tau_M, 4),
            # Statuts
            "ok_MRd"      : ok_MRd,
            "ok_asl_max"  : ok_asl,
            "sous_arme"   : sous_arme,
            "ok_global"   : ok_global,
            # Paramètres intermédiaires
            "x_mm"        : round(x, 2),
            "lam"         : round(lam, 4),
            "eta"         : round(eta, 4),
            "mu_Ed"       : round(mu_Ed, 4),
            "mu_Rd"       : round(mu_Rd, 4),
            "eps_s_permil": round(eps_s * 1000, 3),
            "eps_yd_permil": round(eps_yd * 1000, 3),
            "fyd_MPa"     : round(fyd, 2),
            "fcd_MPa"     : round(fcd, 2),
            "d_mm"        : round(d, 1),
            "Asl_mm2"     : round(self.Asl, 2),
            "Asl_max_mm2" : round(Asl_max, 1),
        }

    # ------------------------------------------------------------------
    # Vérification flèche — EC2 §7.4
    # ------------------------------------------------------------------

    def check_deflection(
        self,
        MEd_ser: float,
        L: float,
        quasi_perm: float = 0.3,
        support: str = "bi-appui",
    ) -> dict:
        """
        Vérification de la flèche différée – EC2 §7.4.

        ──────────────────────────────────────────────────────────────────
        MÉTHODE INTERPOLÉE  (EC2 §7.4.3, Eq. 7.18)
        ──────────────────────────────────────────────────────────────────

        La courbure est interpolée entre l'état non fissuré (état I) et
        l'état fissuré (état II) par le coefficient ζ (Eq. 7.19).

        Hauteur de la zone neutre :
          État I  (section brute) :   x_I  = h/2  (approx. rectangulaire)
          État II (section fissurée) : équation du 2ème ordre
            b·x_II²/2 = αe·Asl·(d − x_II)   avec αe = Es/Ecm

        Rigidité de courbure (1/r) :
          (1/r)_I   = MEd_ser / (Ecm · I_I)
          (1/r)_II  = MEd_ser / (Es  · Asl · (d − x_II/3))   ← approx.
          (1/r)     = ζ·(1/r)_II + (1−ζ)·(1/r)_I

        Coefficient de fissuration ζ (Eq. 7.19) :
          ζ = 1 − β·(Mcr/MEd_ser)²   (≥ 0 si MEd_ser > Mcr)
          β = 0.5  (chargement répété / durée)   –  EC2 §7.4.3(4)
          Mcr = fctm · I_I / (h/2)   –  moment de première fissuration

        Flèche :
          f = κ · (1/r) · L²   avec κ = 1/8 (charge uniformément répartie)
          κ = 1/16 pour console

        Flèche différée : coefficient φ multiplicateur du fluage
          φ_∞  = 2.0  (valeur forfaitaire courante)
          f_long = f_inst · (1 + φ_∞ · quasi_perm)

        Limite EC2 §7.4.1(4) :
          f_adm = L/250  (flèche totale active)

        Paramètres :
            MEd_ser     : Moment de service (quasi-permanent) [kN·m]
            L           : Portée            [m]
            quasi_perm  : Fraction de charge quasi-permanente ψ2 (ex : 0.3)
            support     : "bi-appui" | "console" | "encastre-appui"

        Retourne :
            dict avec flèches, limites et statuts.
        """

        bw   = self.b
        h    = self.h
        d    = self.d
        Asl  = self.Asl
        Ecm  = self.beton.Ecm * 1000.0   # GPa → MPa  (N/mm²)
        Es   = self.acier.Es  * 1000.0   # GPa → MPa
        fctm = self.beton.fctm
        L_mm = L * 1000.0                 # m → mm

        alphae = Es / Ecm                 # rapport modulaire

        # ── Moment d'inertie état I (section brute rectangulaire) ─────────
        I_I  = bw * h**3 / 12.0           # [mm⁴]

        # ── Hauteur zone neutre état I ────────────────────────────────────
        x_I  = h / 2.0

        # ── Moment de fissuration ─────────────────────────────────────────
        Mcr  = fctm * I_I / (h / 2.0)    # [N·mm]
        Mcr_kNm = Mcr / 1e6

        # ── Zone neutre état II : b·x²/2 = αe·Asl·(d − x) ──────────────
        # Forme quadratique : (b/2)·x² + αe·Asl·x − αe·Asl·d = 0
        a_coef = bw / 2.0
        b_coef = alphae * Asl
        c_coef = -alphae * Asl * d
        disc   = b_coef**2 - 4.0 * a_coef * c_coef
        x_II   = (-b_coef + math.sqrt(disc)) / (2.0 * a_coef)

        # ── Moment d'inertie état II (armatures seules) ──────────────────
        I_II   = bw * x_II**3 / 3.0 + alphae * Asl * (d - x_II)**2   # [mm⁴]

        # ── Rigidités de courbure [1/mm] ──────────────────────────────────
        MEd_Nmm  = MEd_ser * 1e6
        curv_I   = MEd_Nmm / (Ecm * I_I)
        curv_II  = MEd_Nmm / (Ecm * I_II)

        # ── Coefficient ζ (Eq. 7.19) ──────────────────────────────────────
        beta = 0.5    # charge de longue durée
        if MEd_Nmm <= Mcr:
            zeta  = 0.0
            curv  = curv_I
        else:
            zeta  = max(0.0, 1.0 - beta * (Mcr / MEd_Nmm)**2)
            curv  = zeta * curv_II + (1.0 - zeta) * curv_I

        # ── Coefficient κ suivant le type d'appui ─────────────────────────
        kappa_map = {
            "bi-appui"       : 1.0 / 8.0,
            "console"        : 1.0 / 2.0,
            "encastre-appui" : 1.0 / 16.0,
        }
        kappa = kappa_map.get(support, 1.0 / 8.0)

        # ── Flèche instantanée [mm] ───────────────────────────────────────
        f_inst = kappa * curv * L_mm**2

        # ── Flèche différée (fluage + retrait) ───────────────────────────
        phi_infini = 2.0                  # coefficient de fluage forfaitaire
        f_long     = f_inst * (1.0 + phi_infini * quasi_perm)

        # ── Limite EC2 §7.4.1(4) ─────────────────────────────────────────
        f_adm  = L_mm / 250.0            # flèche totale admissible

        # ── Statuts ───────────────────────────────────────────────────────
        ok_inst = f_inst <= f_adm
        ok_long = f_long <= f_adm
        ok_global = ok_long

        return {
            # Flèches
            "f_inst_mm"    : round(f_inst, 2),
            "f_long_mm"    : round(f_long, 2),
            "f_adm_mm"     : round(f_adm,  2),
            # Taux
            "tau_f_inst"   : round(f_inst / f_adm, 4),
            "tau_f_long"   : round(f_long / f_adm, 4),
            # Statuts
            "ok_inst"      : ok_inst,
            "ok_long"      : ok_long,
            "ok_global"    : ok_global,
            # Fissuration
            "fissure"      : MEd_Nmm > Mcr,
            "Mcr_kNm"      : round(Mcr_kNm, 2),
            "zeta"         : round(zeta, 4),
            # Paramètres intermédiaires
            "x_I_mm"       : round(x_I, 1),
            "x_II_mm"      : round(x_II, 2),
            "I_I_mm4"      : round(I_I, 0),
            "I_II_mm4"     : round(I_II, 0),
            "curv_I_1pmm"  : round(curv_I, 10),
            "curv_II_1pmm" : round(curv_II, 10),
            "curv_1pmm"    : round(curv, 10),
            "kappa"        : kappa,
            "phi_inf"      : phi_infini,
            "alphae"       : round(alphae, 3),
            "Ecm_MPa"      : round(Ecm, 1),
            "fctm_MPa"     : round(fctm, 3),
            "L_m"          : L,
            "support"      : support,
        }
