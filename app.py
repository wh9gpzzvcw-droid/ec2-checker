import math
import io
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from logic import Beton, Acier, Longrine

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Aliénor — verif cisaillement EC2",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# FONCTION GÉNÉRATION PDF
# =============================================================================
def generate_pdf(longrine, beton, acier, v_ed, n_ed, res,
                 b_mm, h_mm, c_nom, n_long, phi_long,
                 phi_etr, s_etr, n_bras, theta, beton_grade,
                 m_ed, res_flex, m_ed_ser, res_fl, L_portee, support_type, psi2):
    """Génère un PDF récapitulatif des vérifications EC2 §6.1 / §6.2.3 / §7.4."""
    buf = io.BytesIO()

    # ── Couleurs Aliénor ─────────────────────────────────────────────────────
    BLEU     = colors.HexColor("#2563EB")
    NOIR     = colors.HexColor("#111827")
    GRIS_F   = colors.HexColor("#374151")
    GRIS_M   = colors.HexColor("#6B7280")
    GRIS_L   = colors.HexColor("#E5E7EB")
    GRIS_BG  = colors.HexColor("#F9FAFB")
    VERT     = colors.HexColor("#065F46")
    VERT_BG  = colors.HexColor("#ECFDF5")
    VERT_BD  = colors.HexColor("#6EE7B7")
    ROUGE    = colors.HexColor("#991B1B")
    ROUGE_BG = colors.HexColor("#FEF2F2")
    ORANGE   = colors.HexColor("#92400E")

    # ── Document ──────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title="Vérification Cisaillement EC2",
        author="Aliénor — structure",
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    def sty(name, **kw):
        s = ParagraphStyle(name, **kw)
        return s

    S_title   = sty("title",   fontSize=20, fontName="Helvetica-Bold",
                    textColor=NOIR, spaceAfter=2*mm, leading=24)
    S_sub     = sty("sub",     fontSize=8,  fontName="Helvetica",
                    textColor=GRIS_M, spaceAfter=0, leading=11)
    S_section = sty("section", fontSize=10, fontName="Helvetica-Bold",
                    textColor=BLEU, spaceBefore=5*mm, spaceAfter=2*mm)
    S_label   = sty("label",   fontSize=7.5, fontName="Helvetica",
                    textColor=GRIS_M, leading=11)
    S_value   = sty("value",   fontSize=9.5, fontName="Helvetica-Bold",
                    textColor=NOIR, leading=13)
    S_mono    = sty("mono",    fontSize=8,   fontName="Courier",
                    textColor=GRIS_F, leading=12)
    S_badge   = sty("badge",   fontSize=7.5, fontName="Helvetica-Bold",
                    textColor=colors.white, alignment=TA_CENTER)
    S_ok_big  = sty("okbig",   fontSize=12, fontName="Helvetica-Bold",
                    textColor=VERT)
    S_fail_big= sty("failbig", fontSize=12, fontName="Helvetica-Bold",
                    textColor=ROUGE)
    S_normal  = sty("normal",  fontSize=8.5, fontName="Helvetica",
                    textColor=GRIS_F, leading=13)
    S_footer  = sty("footer",  fontSize=7, fontName="Helvetica",
                    textColor=GRIS_M, alignment=TA_CENTER)

    PAGE_W = A4[0] - 40*mm   # largeur utile

    story = []

    # =========================================================================
    # EN-TÊTE
    # =========================================================================
    # Bandeau bleu titre
    header_data = [[
        Paragraph("Aliénor", sty("h_brand", fontSize=16, fontName="Helvetica-Bold",
                                  textColor=colors.white, leading=20)),
        Paragraph("Vérification Cisaillement · Flexion · Flèche<br/>"
                  "<font size='9' color='#bfdbfe'>Treillis de Ritter-Mörsch — EC2 §6.2.3 · §6.1 · §7.4</font>",
                  sty("h_title", fontSize=14, fontName="Helvetica-Bold",
                      textColor=colors.white, leading=19)),
        Paragraph("EN 1992-1-1<br/>§6.2.3 · §6.1<br/>§7.4",
                  sty("h_norm", fontSize=8, fontName="Courier",
                      textColor=colors.HexColor("#BFDBFE"),
                      alignment=TA_RIGHT, leading=12)),
    ]]
    ht = Table(header_data, colWidths=[35*mm, PAGE_W - 70*mm, 35*mm])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BLEU),
        ("ROWPADDING", (0,0), (-1,-1), 5*mm),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",      (2,0), (2,0),   "RIGHT"),
        ("LINEBELOW",  (0,0), (-1,-1), 3, colors.HexColor("#1D4ED8")),
    ]))
    story.append(ht)
    story.append(Spacer(1, 4*mm))

    # Date & statut global
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    statut_ok = res["ok_global"] and (res_flex["ok_global"] if res_flex else True) and (res_fl["ok_global"] if res_fl else True)
    statut_txt = "ÉLÉMENT CONFORME" if statut_ok else "ÉCHEC DE VÉRIFICATION"
    statut_sub = ("Toutes les vérifications EC2 §6.2.3 sont satisfaites"
                  if statut_ok else
                  "Une ou plusieurs vérifications ne sont pas satisfaites")
    bg_statut = VERT_BG if statut_ok else ROUGE_BG
    bd_statut = VERT_BD if statut_ok else colors.HexColor("#FCA5A5")
    txt_statut = VERT if statut_ok else ROUGE
    icon_statut = "✓" if statut_ok else "✗"

    stat_data = [[
        Paragraph(f"<b>{icon_statut}  {statut_txt}</b><br/>"
                  f"<font size='8'>{statut_sub}</font>",
                  sty("stat_p", fontSize=11, fontName="Helvetica-Bold",
                      textColor=txt_statut, leading=16)),
        Paragraph(f"Généré le {date_str}",
                  sty("date_p", fontSize=7.5, fontName="Helvetica",
                      textColor=GRIS_M, alignment=TA_RIGHT, leading=11)),
    ]]
    st_tbl = Table(stat_data, colWidths=[PAGE_W*0.65, PAGE_W*0.35])
    st_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg_statut),
        ("BOX",        (0,0), (-1,-1), 1, bd_statut),
        ("ROWPADDING", (0,0), (-1,-1), 4*mm),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(st_tbl)
    story.append(Spacer(1, 5*mm))

    # =========================================================================
    # SECTION 1 — DONNÉES D'ENTRÉE
    # =========================================================================
    story.append(Paragraph("1 · Données d'entrée", S_section))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_L,
                             spaceAfter=3*mm))

    # Tableaux matériaux + géométrie côte à côte
    def kpi_cell(label, value, unit=""):
        return [
            Paragraph(label.upper(), S_label),
            Paragraph(f"{value} <font size='7' color='#9CA3AF'>{unit}</font>", S_value),
        ]

    mat_rows = [
        [Paragraph("MATÉRIAUX", sty("th", fontSize=7.5, fontName="Helvetica-Bold",
                                     textColor=GRIS_M)),
         Paragraph("GÉOMÉTRIE", sty("th2", fontSize=7.5, fontName="Helvetica-Bold",
                                     textColor=GRIS_M))],
        [
            Table([
                kpi_cell("Béton", beton_grade),
                kpi_cell("fck", f"{beton.fck}", "MPa"),
                kpi_cell("fcd", f"{beton.fcd:.1f}", "MPa"),
                kpi_cell("Acier", "B500S"),
                kpi_cell("fyk", "500", "MPa"),
                kpi_cell("fywd", f"{res['fywd_MPa']:.0f}", "MPa"),
            ], colWidths=[30*mm, 40*mm],
            style=TableStyle([
                ("ROWPADDING", (0,0),(-1,-1), 2.5*mm),
                ("LINEBELOW", (0,0),(-1,-2), 0.3, GRIS_L),
            ])),
            Table([
                kpi_cell("Largeur b", f"{b_mm}", "mm"),
                kpi_cell("Hauteur h", f"{h_mm}", "mm"),
                kpi_cell("Enrobage c", f"{c_nom}", "mm"),
                kpi_cell("Hauteur utile d", f"{longrine.d:.0f}", "mm"),
                kpi_cell("Bras de levier z", f"{0.9*longrine.d:.0f}", "mm"),
            ], colWidths=[38*mm, 32*mm],
            style=TableStyle([
                ("ROWPADDING", (0,0),(-1,-1), 2.5*mm),
                ("LINEBELOW", (0,0),(-1,-2), 0.3, GRIS_L),
            ])),
        ]
    ]

    cols_w = [PAGE_W/2 - 3*mm, PAGE_W/2 - 3*mm]
    mat_tbl = Table(mat_rows, colWidths=cols_w, hAlign="LEFT")
    mat_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), GRIS_BG),
        ("ROWPADDING", (0,0), (-1,0), 2*mm),
        ("BOX",   (0,0), (-1,-1), 0.5, GRIS_L),
        ("INNERGRID", (0,0), (-1,-1), 0.3, GRIS_L),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(mat_tbl)
    story.append(Spacer(1, 4*mm))

    # Ferraillage
    story.append(Paragraph("Ferraillage", sty("sub2", fontSize=8.5,
                             fontName="Helvetica-Bold", textColor=GRIS_F,
                             spaceAfter=2*mm)))
    Asl_cm2 = longrine.Asl / 100
    Asw_cm2 = longrine.Asw / 100
    ferr_data = [
        ["", "Longitudinal", "Transversal"],
        ["Détail",
         f"{n_long} barres ø{phi_long} mm",
         f"étriers ø{phi_etr} mm / {n_bras} bras / s={s_etr} mm"],
        ["Section (cm²)",
         f"Asl = {Asl_cm2:.2f} cm²  (ρl = {longrine.rho_l*100:.3f} %)",
         f"Asw = {Asw_cm2:.3f} cm²  (Asw/s = {longrine.Asw_sur_s:.3f} mm²/mm)"],
        ["Angle treillis", f"θ = {theta:.1f}°  (cot θ = {res['cot_theta']:.3f})", "—"],
    ]
    ferr_tbl = Table(ferr_data,
                     colWidths=[30*mm, (PAGE_W-30*mm)/2, (PAGE_W-30*mm)/2])
    ferr_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NOIR),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("FONTNAME",   (0,1), (0,-1), "Helvetica-Bold"),
        ("BACKGROUND", (0,1), (0,-1), GRIS_BG),
        ("ROWPADDING", (0,0), (-1,-1), 2.5*mm),
        ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",      (0,0), (0,-1), "CENTER"),
    ]))
    story.append(ferr_tbl)
    story.append(Spacer(1, 5*mm))

    # =========================================================================
    # SECTION 2 — SOLLICITATIONS
    # =========================================================================
    story.append(Paragraph("2 · Sollicitations ELU", S_section))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_L,
                             spaceAfter=3*mm))

    soll_data = [
        ["Sollicitation", "Symbole", "Valeur", "Unité"],
        ["Effort tranchant", "VEd", f"{v_ed:.2f}", "kN"],
        ["Effort normal", "NEd", f"{n_ed:.2f}", "kN  (+ = compr.)"],
        ["Moment fléchissant (ELU)", "MEd", f"{m_ed:.2f}", "kN·m"],
        ["Moment de service (ELS)", "MEd,ser", f"{m_ed_ser:.2f}", "kN·m"],
        ["Contrainte normale", "σcp", f"{res['sigma_cp_MPa']:.3f}", "MPa"],
    ]
    soll_tbl = Table(soll_data,
                     colWidths=[60*mm, 30*mm, 40*mm, PAGE_W-130*mm])
    soll_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NOIR),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8.5),
        ("FONTNAME",   (0,1), (0,-1), "Helvetica"),
        ("ROWPADDING", (0,0), (-1,-1), 2.5*mm),
        ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
        ("ALIGN",      (1,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,2), (-1,2), GRIS_BG),
        ("BACKGROUND", (0,4), (-1,4), GRIS_BG),
    ]))
    story.append(soll_tbl)
    story.append(Spacer(1, 5*mm))

    # =========================================================================
    # SECTION 3 — RÉSISTANCES CALCULÉES
    # =========================================================================
    story.append(Paragraph("3 · Résistances calculées EC2 §6.2.3", S_section))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_L,
                             spaceAfter=3*mm))

    def tau_color(v):
        if v <= 0.75: return VERT
        if v <= 1.00: return ORANGE
        return ROUGE

    def ok_str(ok):
        return ("✓  OK" if ok else "✗  NON")

    def ok_col(ok):
        return VERT if ok else ROUGE

    tau1 = res["tau_VRd_max"]
    tau2 = res["tau_VRd_s"]

    res_data = [
        ["Vérification", "Résistance", "Sollicitation", "Taux VEd/VRd", "Statut"],
        ["Bielle comprimée\nVRd,max",
         f"{res['VRd_max_kN']:.1f} kN",
         f"{v_ed:.1f} kN",
         f"{tau1:.3f}",
         ok_str(tau1 <= 1.0)],
        ["Traction acier\nVRd,s",
         f"{res['VRd_s_kN']:.1f} kN",
         f"{v_ed:.1f} kN",
         f"{tau2:.3f}",
         ok_str(tau2 <= 1.0)],
    ]
    res_tbl = Table(res_data,
                    colWidths=[45*mm, 32*mm, 32*mm, 32*mm, PAGE_W-141*mm])
    res_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NOIR),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8.5),
        ("ROWPADDING", (0,0), (-1,-1), 3*mm),
        ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
        ("ALIGN",      (1,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,2), (-1,2), GRIS_BG),
        # Couleur taux
        ("TEXTCOLOR", (3,1), (3,1), tau_color(tau1)),
        ("TEXTCOLOR", (3,2), (3,2), tau_color(tau2)),
        ("FONTNAME",  (3,1), (3,2), "Helvetica-Bold"),
        # Couleur statut
        ("TEXTCOLOR", (4,1), (4,1), ok_col(tau1 <= 1.0)),
        ("TEXTCOLOR", (4,2), (4,2), ok_col(tau2 <= 1.0)),
        ("FONTNAME",  (4,1), (4,2), "Helvetica-Bold"),
    ]))
    story.append(res_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Vérifications constructives ──────────────────────────────────────────
    ok_rho = res["ok_rho_w_min"]
    ok_s   = res["ok_s_max"]
    cons_data = [
        ["Vérification constructive", "Valeur calculée", "Limite", "Statut"],
        ["Taux d'armature minimale  ρw ≥ ρw,min",
         f"{res['rho_w']:.5f}",
         f"≥ {res['rho_w_min']:.5f}",
         ok_str(ok_rho)],
        ["Espacement max étriers  s ≤ sl,max",
         f"{s_etr} mm",
         f"≤ {res['s_max_mm']:.0f} mm",
         ok_str(ok_s)],
    ]
    cons_tbl = Table(cons_data,
                     colWidths=[75*mm, 35*mm, 35*mm, PAGE_W-145*mm])
    cons_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), GRIS_F),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ROWPADDING", (0,0), (-1,-1), 2.5*mm),
        ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
        ("ALIGN",      (1,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,2), (-1,2), GRIS_BG),
        ("TEXTCOLOR",  (3,1), (3,1), ok_col(ok_rho)),
        ("TEXTCOLOR",  (3,2), (3,2), ok_col(ok_s)),
        ("FONTNAME",   (3,1), (3,2), "Helvetica-Bold"),
    ]))
    story.append(cons_tbl)
    story.append(Spacer(1, 5*mm))

    # =========================================================================
    # SECTION 4 — VÉRIFICATION FLEXION EC2 §6.1
    # =========================================================================
    story.append(Paragraph("4 · Vérification Flexion — EC2 §6.1", S_section))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_L,
                             spaceAfter=3*mm))

    if res_flex:
        tau_M   = res_flex["tau_MRd"]
        ok_MRd  = res_flex["ok_MRd"]
        ok_asl  = res_flex["ok_asl_max"]
        ok_sous = res_flex["sous_arme"]

        flex_res_data = [
            ["Vérification", "Résistance", "Sollicitation", "Taux MEd/MRd", "Statut"],
            ["Moment résistant\nMRd",
             f"{res_flex['MRd_kNm']:.2f} kN·m",
             f"{m_ed:.2f} kN·m",
             f"{tau_M:.3f}",
             ok_str(ok_MRd)],
        ]
        flex_res_tbl = Table(flex_res_data,
                             colWidths=[45*mm, 35*mm, 35*mm, 32*mm, PAGE_W-147*mm])
        flex_res_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NOIR),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8.5),
            ("ROWPADDING", (0,0), (-1,-1), 3*mm),
            ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
            ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
            ("ALIGN",      (1,0), (-1,-1), "CENTER"),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TEXTCOLOR",  (3,1), (3,1), tau_color(tau_M)),
            ("FONTNAME",   (3,1), (3,1), "Helvetica-Bold"),
            ("TEXTCOLOR",  (4,1), (4,1), ok_col(ok_MRd)),
            ("FONTNAME",   (4,1), (4,1), "Helvetica-Bold"),
        ]))
        story.append(flex_res_tbl)
        story.append(Spacer(1, 3*mm))

        # Vérifications complémentaires flexion
        flex_cons_data = [
            ["Vérification complémentaire", "Valeur", "Condition", "Statut"],
            ["Section sous-armée (pivot A/B)  εs ≥ εyd",
             f"{res_flex['eps_s_permil']:.3f} ‰",
             f"≥ {res_flex['eps_yd_permil']:.3f} ‰",
             ok_str(ok_sous)],
            ["Taux d'armature max  Asl ≤ 4%·Ac",
             f"{res_flex['Asl_mm2']:.0f} mm²",
             f"≤ {res_flex['Asl_max_mm2']:.0f} mm²",
             ok_str(ok_asl)],
            ["Axe neutre  x",
             f"{res_flex['x_mm']:.1f} mm",
             f"hauteur utile d = {res_flex['d_mm']:.1f} mm",
             "—"],
        ]
        flex_cons_tbl = Table(flex_cons_data,
                               colWidths=[75*mm, 30*mm, 45*mm, PAGE_W-150*mm])
        flex_cons_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), GRIS_F),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWPADDING", (0,0), (-1,-1), 2.5*mm),
            ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
            ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
            ("ALIGN",      (1,0), (-1,-1), "CENTER"),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("BACKGROUND", (0,2), (-1,2), GRIS_BG),
            ("TEXTCOLOR",  (3,1), (3,1), ok_col(ok_sous)),
            ("TEXTCOLOR",  (3,2), (3,2), ok_col(ok_asl)),
            ("FONTNAME",   (3,1), (3,3), "Helvetica-Bold"),
        ]))
        story.append(flex_cons_tbl)
    else:
        story.append(Paragraph("Données de flexion non renseignées.", S_normal))
    story.append(Spacer(1, 5*mm))

    # =========================================================================
    # SECTION 5 — VÉRIFICATION FLÈCHE EC2 §7.4
    # =========================================================================
    story.append(Paragraph("5 · Vérification Flèche — EC2 §7.4", S_section))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_L,
                             spaceAfter=3*mm))

    if res_fl:
        tau_fi = res_fl["tau_f_inst"]
        tau_fd = res_fl["tau_f_long"]
        ok_fi  = res_fl["ok_inst"]
        ok_fd  = res_fl["ok_long"]

        fleche_res_data = [
            ["Vérification", "Flèche calculée", "Limite  f_adm = L/250", "Taux f/f_adm", "Statut"],
            ["Flèche instantanée  f_inst",
             f"{res_fl['f_inst_mm']:.2f} mm",
             f"{res_fl['f_adm_mm']:.1f} mm",
             f"{tau_fi:.3f}",
             ok_str(ok_fi)],
            ["Flèche différée (fluage)  f_long",
             f"{res_fl['f_long_mm']:.2f} mm",
             f"{res_fl['f_adm_mm']:.1f} mm",
             f"{tau_fd:.3f}",
             ok_str(ok_fd)],
        ]
        fleche_res_tbl = Table(fleche_res_data,
                                colWidths=[48*mm, 30*mm, 40*mm, 28*mm, PAGE_W-146*mm])
        fleche_res_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NOIR),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8.5),
            ("ROWPADDING", (0,0), (-1,-1), 3*mm),
            ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
            ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
            ("ALIGN",      (1,0), (-1,-1), "CENTER"),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("BACKGROUND", (0,2), (-1,2), GRIS_BG),
            ("TEXTCOLOR",  (3,1), (3,1), tau_color(tau_fi)),
            ("TEXTCOLOR",  (3,2), (3,2), tau_color(tau_fd)),
            ("FONTNAME",   (3,1), (3,2), "Helvetica-Bold"),
            ("TEXTCOLOR",  (4,1), (4,1), ok_col(ok_fi)),
            ("TEXTCOLOR",  (4,2), (4,2), ok_col(ok_fd)),
            ("FONTNAME",   (4,1), (4,2), "Helvetica-Bold"),
        ]))
        story.append(fleche_res_tbl)
        story.append(Spacer(1, 3*mm))

        # Paramètres de fissuration et fluage
        fiss_label = "Section fissurée" if res_fl["fissure"] else "Section non fissurée"
        fleche_cons_data = [
            ["Paramètre", "Valeur", "Paramètre", "Valeur"],
            ["Portée L", f"{L_portee:.2f} m",
             "Schéma statique", support_type],
            ["Moment fissuration Mcr", f"{res_fl['Mcr_kNm']:.2f} kN·m",
             "État de fissuration", fiss_label],
            ["Coeff. interpolation ζ", f"{res_fl['zeta']:.4f}",
             "Coeff. fluage φ∞", f"{res_fl['phi_inf']:.1f}"],
            ["xI (axe neutre brut)", f"{res_fl['x_I_mm']:.1f} mm",
             "xII (axe neutre fiss.)", f"{res_fl['x_II_mm']:.1f} mm"],
            ["Ecm", f"{res_fl['Ecm_MPa']:.0f} MPa",
             "αe = Es/Ecm", f"{res_fl['alphae']:.2f}"],
        ]
        fleche_cons_tbl = Table(fleche_cons_data,
                                 colWidths=[50*mm, 40*mm, 50*mm, PAGE_W-140*mm])
        fleche_cons_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), GRIS_F),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWPADDING", (0,0), (-1,-1), 2.5*mm),
            ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
            ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
            ("FONTNAME",   (0,1), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",   (2,1), (2,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,2), (-1,2), GRIS_BG),
            ("BACKGROUND", (0,4), (-1,4), GRIS_BG),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(fleche_cons_tbl)
    else:
        story.append(Paragraph("Données de flèche non renseignées.", S_normal))
    story.append(Spacer(1, 5*mm))

    # =========================================================================
    # SECTION 6 — PARAMÈTRES INTERMÉDIAIRES (cisaillement)
    # =========================================================================
    story.append(Paragraph("6 · Paramètres intermédiaires — Cisaillement", S_section))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_L,
                             spaceAfter=3*mm))

    params = [
        ("nu1 — béton fissuré",    f"{res['nu1']:.4f}",           "—"),
        ("alpha_cw — effort normal", f"{res['alpha_cw']:.4f}",    "—"),
        ("sigma_cp",               f"{res['sigma_cp_MPa']:.3f}",  "MPa"),
        ("cot theta",              f"{res['cot_theta']:.4f}",     "—"),
        ("fcd",                    f"{res['fcd_MPa']:.2f}",       "MPa"),
        ("fywd",                   f"{res['fywd_MPa']:.2f}",      "MPa"),
        ("d (hauteur utile)",      f"{res['d_mm']:.1f}",          "mm"),
        ("z (bras de levier)",     f"{res['z_mm']:.1f}",          "mm"),
        ("Asw (section 1 bras)",   f"{res['Asw_mm2']:.2f}",       "mm2"),
    ]
    # 3 colonnes de 3 lignes
    col_size = 3
    param_rows = [[
        Paragraph("PARAMÈTRE", sty("ph", fontSize=7, fontName="Helvetica-Bold",
                                    textColor=GRIS_M)),
        Paragraph("VALEUR", sty("ph2", fontSize=7, fontName="Helvetica-Bold",
                                 textColor=GRIS_M, alignment=TA_CENTER)),
        Paragraph("UNITÉ", sty("ph3", fontSize=7, fontName="Helvetica-Bold",
                                textColor=GRIS_M, alignment=TA_CENTER)),
        Paragraph("PARAMÈTRE", sty("ph4", fontSize=7, fontName="Helvetica-Bold",
                                    textColor=GRIS_M)),
        Paragraph("VALEUR", sty("ph5", fontSize=7, fontName="Helvetica-Bold",
                                 textColor=GRIS_M, alignment=TA_CENTER)),
        Paragraph("UNITÉ", sty("ph6", fontSize=7, fontName="Helvetica-Bold",
                                textColor=GRIS_M, alignment=TA_CENTER)),
        Paragraph("PARAMÈTRE", sty("ph7", fontSize=7, fontName="Helvetica-Bold",
                                    textColor=GRIS_M)),
        Paragraph("VALEUR", sty("ph8", fontSize=7, fontName="Helvetica-Bold",
                                 textColor=GRIS_M, alignment=TA_CENTER)),
        Paragraph("UNITÉ", sty("ph9", fontSize=7, fontName="Helvetica-Bold",
                                textColor=GRIS_M, alignment=TA_CENTER)),
    ]]
    for i in range(col_size):
        row = []
        for col in range(3):
            idx = col * col_size + i
            if idx < len(params):
                lbl, val, unt = params[idx]
                row += [
                    Paragraph(lbl, sty(f"pl{i}{col}", fontSize=8,
                                       fontName="Helvetica", textColor=GRIS_F)),
                    Paragraph(val, sty(f"pv{i}{col}", fontSize=8.5,
                                       fontName="Helvetica-Bold", textColor=NOIR,
                                       alignment=TA_CENTER)),
                    Paragraph(unt, sty(f"pu{i}{col}", fontSize=7.5,
                                       fontName="Courier", textColor=GRIS_M,
                                       alignment=TA_CENTER)),
                ]
            else:
                row += ["", "", ""]
        param_rows.append(row)

    cw = PAGE_W / 9
    param_tbl = Table(param_rows, colWidths=[cw*2, cw, cw*0.7]*3)
    param_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), GRIS_BG),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ROWPADDING", (0,0), (-1,-1), 2*mm),
        ("BOX",        (0,0), (-1,-1), 0.5, GRIS_L),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, GRIS_L),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        # Séparateurs de colonnes de paramètres plus épais
        ("LINEAFTER",  (2,0), (2,-1), 1.5, GRIS_L),
        ("LINEAFTER",  (5,0), (5,-1), 1.5, GRIS_L),
    ]))
    story.append(param_tbl)
    story.append(Spacer(1, 6*mm))

    # =========================================================================
    # PIED DE PAGE
    # =========================================================================
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_L,
                             spaceBefore=2*mm, spaceAfter=2*mm))
    footer_data = [[
        Paragraph("Aliénor — Structure ",
                  sty("f1", fontSize=7, fontName="Helvetica-Bold",
                      textColor=BLEU)),
        Paragraph(f"Vérification automatique EC2 §6.2.3 · §6.1 · §7.4  ·  {date_str}",
                  sty("f2", fontSize=7, fontName="Helvetica",
                      textColor=GRIS_M, alignment=TA_CENTER)),
        Paragraph("Note de calcul non signée\nà usage interne uniquement",
                  sty("f3", fontSize=6.5, fontName="Helvetica",
                      textColor=GRIS_M, alignment=TA_RIGHT, leading=10)),
    ]]
    foot_tbl = Table(footer_data, colWidths=[PAGE_W/3]*3)
    foot_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWPADDING", (0,0), (-1,-1), 1*mm),
    ]))
    story.append(foot_tbl)

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    buf.seek(0)
    return buf.read()


# =============================================================================
# GLOBAL CSS
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

html, body, .stApp {
    background-color: #F6F6F3 !important;
    color: #111827 !important;
    font-family: 'DM Sans', sans-serif !important;
}
section[data-testid="stSidebar"] {
    background-color: #111827 !important;
    border-right: none !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] * { color: #E5E7EB !important; font-family: 'DM Sans', sans-serif !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stNumberInput label,
section[data-testid="stSidebar"] .stSlider label {
    color: #9CA3AF !important; font-size: 0.72rem !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important; font-weight: 500 !important;
}
section[data-testid="stSidebar"] div[data-baseweb="input"] {
    background-color: #1F2937 !important; border: 1px solid #374151 !important; border-radius: 6px !important;
}
section[data-testid="stSidebar"] input {
    color: #F9FAFB !important; -webkit-text-fill-color: #F9FAFB !important; background: transparent !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #1F2937 !important; border: 1px solid #374151 !important;
    border-radius: 6px !important; color: #F9FAFB !important;
}
section[data-testid="stSidebar"] hr { border-color: #374151 !important; margin: 1rem 0 !important; }
.sidebar-logo {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    padding: 1.4rem 1.6rem 1.2rem; margin: 0 0 1.4rem 0;
}
.sidebar-logo h2 {
    font-family: 'Syne', sans-serif !important; font-weight: 800 !important;
    font-size: 1.15rem !important; color: #FFFFFF !important; margin: 0 !important;
}
.sidebar-logo span {
    font-family: 'DM Mono', monospace !important; font-size: 0.68rem !important;
    color: rgba(255,255,255,0.6) !important; letter-spacing: 0.12em !important; text-transform: uppercase !important;
}
.sidebar-section {
    font-family: 'Syne', sans-serif !important; font-size: 0.68rem !important; font-weight: 700 !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important; color: #4B5563 !important;
    padding: 0.6rem 0 0.3rem !important; border-top: 1px solid #374151; margin-top: 0.5rem !important;
}
.main .block-container { padding: 2rem 2.5rem 2rem !important; max-width: 1200px !important; }
.page-header {
    display: flex; align-items: flex-end; justify-content: space-between;
    margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #E5E7EB;
}
.page-header h1 {
    font-family: 'Syne', sans-serif !important; font-weight: 800 !important; font-size: 2rem !important;
    color: #111827 !important; margin: 0 !important; letter-spacing: -0.03em; line-height: 1.1;
}
.page-header .subtitle {
    font-family: 'DM Mono', monospace !important; font-size: 0.72rem !important;
    color: #6B7280 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; margin-top: 0.4rem;
}
.page-header .header-right { display: flex; align-items: center; gap: 0.75rem; }
.page-header .norm-badge {
    background: #111827; color: #FFFFFF !important; font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important; padding: 0.35rem 0.75rem; border-radius: 4px;
    letter-spacing: 0.08em; text-transform: uppercase;
}

/* ── Bouton PDF ──────────────────────────────────────── */
.pdf-btn-wrap .stDownloadButton > button {
    background: transparent !important;
    border: 1.5px solid #E5E7EB !important;
    border-radius: 8px !important;
    color: #374151 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.9rem !important;
    display: flex !important; align-items: center !important; gap: 0.4rem !important;
    transition: all 0.2s !important;
    width: auto !important;
}
.pdf-btn-wrap .stDownloadButton > button:hover {
    background: #F3F4F6 !important;
    border-color: #9CA3AF !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
}

.card {
    background: #FFFFFF; border-radius: 12px; padding: 1.5rem;
    border: 1px solid #E5E7EB;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.03);
    margin-bottom: 1.2rem;
}
.card-title {
    font-family: 'Syne', sans-serif !important; font-size: 0.75rem !important;
    font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase !important;
    color: #6B7280 !important; margin-bottom: 1rem !important;
}
.status-ok {
    background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
    border: 1px solid #6EE7B7; border-radius: 10px; padding: 1.2rem 1.5rem;
    display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.2rem;
}
.status-fail {
    background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
    border: 1px solid #FCA5A5; border-radius: 10px; padding: 1.2rem 1.5rem;
    display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.2rem;
}
.status-ok .status-text, .status-fail .status-text {
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important; font-size: 0.95rem !important;
}
.status-ok .status-text { color: #065F46 !important; }
.status-fail .status-text { color: #991B1B !important; }
.kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; margin-top: 1rem; }
.kpi-item { background: #F9FAFB; border-radius: 8px; padding: 0.85rem 1rem; border: 1px solid #F3F4F6; }
.kpi-label { font-family: 'DM Mono', monospace !important; font-size: 0.65rem !important;
    text-transform: uppercase !important; letter-spacing: 0.07em !important; color: #6B7280 !important; margin-bottom: 0.3rem; }
.kpi-value { font-family: 'Syne', sans-serif !important; font-size: 1.25rem !important;
    font-weight: 700 !important; color: #111827 !important; line-height: 1; }
.kpi-unit { font-family: 'DM Mono', monospace !important; font-size: 0.7rem !important;
    color: #9CA3AF !important; margin-left: 0.2rem; }
.checks-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.75rem 0; }
.check-chip {
    display: flex; align-items: center; gap: 0.3rem; background: #F9FAFB;
    border: 1px solid #E5E7EB; border-radius: 6px; padding: 0.35rem 0.7rem;
    font-family: 'DM Mono', monospace !important; font-size: 0.7rem !important; color: #374151 !important;
}
.check-chip.ok   { border-color: #6EE7B7; background: #ECFDF5; color: #065F46 !important; }
.check-chip.fail { border-color: #FCA5A5; background: #FEF2F2; color: #991B1B !important; }
div[data-baseweb="input"] { background-color: #ffffff !important; border-radius: 8px !important; border: 1px solid #E5E7EB !important; }
.main input, .main select, .main textarea { color: #111827 !important; -webkit-text-fill-color: #111827 !important; }
label { font-size: 0.78rem !important; font-weight: 500 !important; color: #374151 !important; }
.stButton > button {
    background: #111827 !important; color: #FFFFFF !important; border: none !important;
    border-radius: 8px !important; font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important; font-size: 0.85rem !important; letter-spacing: 0.04em !important;
    padding: 0.6rem 1.2rem !important; transition: all 0.2s ease !important; width: 100% !important;
}
.stButton > button:hover { background: #1F2937 !important; transform: translateY(-1px) !important; }
.stCheckbox label p { color: #111827 !important; font-weight: 500 !important; font-size: 0.85rem !important; }
.stSlider > label { font-size: 0.78rem !important; color: #374151 !important; }
.stDivider { margin: 1.5rem 0 !important; }
.info-box {
    background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 1rem 1.2rem;
    font-family: 'DM Sans', sans-serif !important; font-size: 0.82rem !important; color: #1E40AF !important; line-height: 1.5;
}
.section-title {
    font-family: 'Syne', sans-serif !important; font-size: 1.1rem !important; font-weight: 700 !important;
    color: #111827 !important; letter-spacing: -0.02em; margin-bottom: 1rem !important;
}

/* FIX icône sidebar */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarNavCollapseButton"] button,
button[data-testid="collapsedControl"] { font-size: 0 !important; color: transparent !important; }
</style>
""", unsafe_allow_html=True)

# FIX ICÔNE SIDEBAR JS
st.markdown("""
<script>
(function fixSidebarIcon() {
    const SVG_L = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E5E7EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>`;
    const SVG_R = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>`;
    function fix() {
        document.querySelectorAll('[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarNavCollapseButton"] button, button[data-testid="collapsedControl"]').forEach(btn => {
            if (btn.textContent.trim().includes('keyboard') || btn.textContent.trim().includes('arrow')) {
                const isLeft = btn.closest('[data-testid="stSidebar"]') || btn.textContent.includes('left');
                btn.innerHTML = isLeft ? SVG_L : SVG_R;
            }
        });
    }
    fix();
    new MutationObserver(fix).observe(document.body, {childList:true, subtree:true});
})();
</script>
""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h2>Aliénor</h2>
        <span>Aliénor — Structure</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">Béton</div>', unsafe_allow_html=True)
    beton_grade = st.selectbox("Classe de béton", ["C20/25", "C25/30", "C30/37", "C35/45"], index=2)
    fck_val = int(beton_grade.split('/')[0][1:])
    beton = Beton(fck=fck_val, fck_cube=fck_val + 7)
    acier = Acier(fyk=500)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.metric("fck", f"{beton.fck} MPa")
    with col_b2:
        st.metric("fcd", f"{beton.fcd:.1f} MPa")

    st.markdown('<div class="sidebar-section">Géométrie</div>', unsafe_allow_html=True)
    b_mm  = st.number_input("Largeur b (mm)", 100, 1500, 300, 50)
    h_mm  = st.number_input("Hauteur h (mm)", 200, 2000, 500, 50)
    c_nom = st.number_input("Enrobage c_nom (mm)", 15, 75, 35, 5)

    st.markdown('<div class="sidebar-section">Ferraillage longitudinal</div>', unsafe_allow_html=True)
    n_long   = st.number_input("Nb barres", 2, 20, 4)
    phi_long = st.selectbox("φ long. (mm)", [12, 14, 16, 20, 25], index=2)

    st.markdown('<div class="sidebar-section">Ferraillage transversal</div>', unsafe_allow_html=True)
    phi_etr = st.selectbox("φ étrier (mm)", [6, 8, 10], index=1)
    s_etr   = st.number_input("Espacement s (mm)", 50, 400, 150, 25)
    n_bras  = st.number_input("Nb de bras", 2, 4, 2)

    st.markdown('<div class="sidebar-section">Modèle treillis</div>', unsafe_allow_html=True)
    theta = st.slider("Angle θ (°)", 21.8, 45.0, 35.0, 0.1,
                      help="Angle bielle comprimée EC2 §6.2.3")

    st.markdown('<div class="sidebar-section">Flèche — Portée</div>', unsafe_allow_html=True)
    L_portee = st.number_input("Portée L (m)", 1.0, 30.0, 5.0, 0.5)
    support_type = st.selectbox("Conditions d'appui",
        ["bi-appui", "encastre-appui", "console"], index=0)
    psi2 = st.slider("ψ₂ (fraction quasi-perm.)", 0.0, 1.0, 0.3, 0.05,
                     help="Coefficient de combinaison quasi-permanente (EN 1990)")

# =============================================================================
# OBJET LONGRINE
# =============================================================================
longrine = Longrine(
    beton, acier, b_mm, h_mm, n_long, phi_long,
    phi_etr=phi_etr, n_bras=n_bras, s=s_etr,
    theta=theta, c_nom=c_nom
)

# =============================================================================
# EN-TÊTE PAGE + BOUTON PDF
# =============================================================================
col_hdr, col_pdf = st.columns([1, 0.18])

with col_hdr:
    st.markdown("""
    <div class="page-header" style="border-bottom:none;margin-bottom:0;padding-bottom:0;">
        <div>
            <h1>Vérification Cisaillement</h1>
            <div class="subtitle">Treillis de Ritter-Mörsch — Résistance à l'effort tranchant</div>
        </div>
        <div class="norm-badge">EN 1992-1-1 §6.2.3</div>
    </div>
    """, unsafe_allow_html=True)

# Bouton PDF — uniquement si les procédures sont OK (on le place avant la divider)
# On calcule d'abord les procédures
with st.container():
    _c1, _c2, _c3 = st.columns(3)
    with _c1: v1 = st.checkbox("✓ Actions Eurocode 1 vérifiées",   value=True)
    with _c2: v2 = st.checkbox("✓ Réservations MEP validées",       value=True)
    with _c3: v3 = st.checkbox("✓ Enrobage conforme à l'exposition", value=True)

procedures_ok = v1 and v2 and v3

# Inputs sollicitations (nécessaires pour le PDF, on les déclare tôt)
# On les redéfinira dans la colonne gauche — Streamlit les rend une seule fois,
# donc on utilise st.session_state pour transmettre les valeurs.

st.divider()

# =============================================================================
# SOLLICITATIONS + RÉSULTATS
# =============================================================================
col_left, col_right = st.columns([1, 1.2], gap="large")

with col_left:
    st.markdown('<div class="section-title">Sollicitations ELU</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    v_ed = st.number_input("Effort tranchant VEd (kN)", 0.0, 5000.0, 120.0, 10.0)
    n_ed = st.number_input("Effort normal NEd (kN)  [+ = compression]",
                            -2000.0, 2000.0, 0.0, 10.0)
    m_ed = st.number_input("Moment fléchissant MEd (kN·m)", 0.0, 50000.0, 80.0, 5.0)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:1rem;">Sollicitations ELS</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    m_ed_ser = st.number_input("Moment de service MEd,ser (kN·m) [quasi-perm.]",
                                0.0, 30000.0, 50.0, 5.0)
    st.markdown('</div>', unsafe_allow_html=True)

    Asl_cm2 = longrine.Asl / 100
    Asw_cm2 = longrine.Asw / 100
    st.markdown(f"""
    <div class="card">
        <div class="card-title">Propriétés section calculées</div>
        <div class="kpi-grid">
            <div class="kpi-item">
                <div class="kpi-label">Hauteur utile d</div>
                <div class="kpi-value">{longrine.d:.0f}<span class="kpi-unit">mm</span></div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">Bras de levier z</div>
                <div class="kpi-value">{0.9*longrine.d:.0f}<span class="kpi-unit">mm</span></div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">Asl (long.)</div>
                <div class="kpi-value">{Asl_cm2:.1f}<span class="kpi-unit">cm²</span></div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">Asw (étrier)</div>
                <div class="kpi-value">{Asw_cm2:.2f}<span class="kpi-unit">cm²</span></div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">ρl (long.)</div>
                <div class="kpi-value">{longrine.rho_l*100:.3f}<span class="kpi-unit">%</span></div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">Asw/s</div>
                <div class="kpi-value">{longrine.Asw_sur_s:.3f}<span class="kpi-unit">mm²/mm</span></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.button("Lancer la vérification structurelle")

with col_right:
    st.markdown('<div class="section-title">Résultats de vérification</div>',
                unsafe_allow_html=True)

    if not procedures_ok:
        st.markdown("""
        <div class="info-box">
            ℹ️ Veuillez valider les trois procédures préalables avant de lancer l'analyse.
        </div>
        """, unsafe_allow_html=True)
    else:
        res = longrine.check_shear(v_ed, n_ed, verbose=False)

        # ── Statut global ─────────────────────────────────────────────────────
        if res["ok_global"]:
            st.markdown("""
            <div class="status-ok">
                <span style="font-size:1.4rem;">✅</span>
                <div>
                    <div class="status-text">ÉLÉMENT CONFORME</div>
                    <div style="font-size:0.75rem;color:#065F46;margin-top:0.15rem;">
                        Toutes les vérifications EC2 §6.2.3 sont satisfaites
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-fail">
                <span style="font-size:1.4rem;">❌</span>
                <div>
                    <div class="status-text">ÉCHEC DE VÉRIFICATION</div>
                    <div style="font-size:0.75rem;color:#991B1B;margin-top:0.15rem;">
                        Une ou plusieurs vérifications ne sont pas satisfaites
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Bouton PDF (dans la colonne résultats, aligné avec le statut) ─────
        st.markdown('<div class="pdf-btn-wrap">', unsafe_allow_html=True)
        _res_flex_pdf = longrine.check_bending(m_ed, verbose=False)
        _res_fl_pdf   = longrine.check_deflection(m_ed_ser, L_portee, psi2, support_type)
        pdf_bytes = generate_pdf(
            longrine, beton, acier, v_ed, n_ed, res,
            b_mm, h_mm, c_nom, n_long, phi_long,
            phi_etr, s_etr, n_bras, theta, beton_grade,
            m_ed, _res_flex_pdf, m_ed_ser, _res_fl_pdf, L_portee, support_type, psi2
        )
        fname = (f"note_calcul_EC2_"
                 f"{beton_grade.replace('/','_')}_"
                 f"b{b_mm}h{h_mm}_"
                 f"VEd{int(v_ed)}kN_MEd{int(m_ed)}kNm.pdf")
        st.download_button(
            label="📄  Exporter la note PDF",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            help="Télécharger la note de calcul récapitulative (PDF A4)",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Taux d'utilisation — components.html ─────────────────────────────
        def ratio_bar_style(v):
            if v <= 0.75: return "#065F46", "linear-gradient(90deg,#10B981,#34D399)"
            if v <= 1.00: return "#92400E", "linear-gradient(90deg,#F59E0B,#FCD34D)"
            return "#991B1B", "linear-gradient(90deg,#EF4444,#F87171)"

        tau1 = res["tau_VRd_max"]
        tau2 = res["tau_VRd_s"]
        c1_txt, c1_grad = ratio_bar_style(tau1)
        c2_txt, c2_grad = ratio_bar_style(tau2)
        w1 = min(tau1 * 100, 100)
        w2 = min(tau2 * 100, 100)

        components.html(f"""<!DOCTYPE html><html><head>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
        <style>
          *{{margin:0;padding:0;box-sizing:border-box;}}
          body{{background:transparent;font-family:'DM Sans',sans-serif;}}
          .card{{background:#FFF;border-radius:12px;padding:1.3rem 1.5rem;border:1px solid #E5E7EB;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 16px rgba(0,0,0,.03);}}
          .card-title{{font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;margin-bottom:1rem;}}
          .ratio-block{{margin-bottom:1rem;}}
          .ratio-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:.35rem;}}
          .ratio-name{{font-family:'DM Sans',sans-serif;font-size:.82rem;font-weight:600;color:#111827;}}
          .ratio-val{{font-family:'DM Mono',monospace;font-size:.82rem;font-weight:700;}}
          .ratio-track{{background:#E5E7EB;border-radius:999px;height:7px;overflow:hidden;}}
          .ratio-fill{{height:100%;border-radius:999px;transition:width .4s ease;}}
          .ratio-meta{{font-family:'DM Mono',monospace;font-size:.68rem;color:#6B7280;margin-top:.28rem;}}
          .spacer{{height:1rem;}}
        </style></head><body>
          <div class="card">
            <div class="card-title">Taux d'utilisation</div>
            <div class="ratio-block">
              <div class="ratio-header">
                <span class="ratio-name">Bielle comprimée — VRd,max</span>
                <span class="ratio-val" style="color:{c1_txt};">{tau1:.3f}</span>
              </div>
              <div class="ratio-track"><div class="ratio-fill" style="width:{w1:.1f}%;background:{c1_grad};"></div></div>
              <div class="ratio-meta">VEd = {v_ed:.1f} kN &nbsp;/&nbsp; VRd,max = {res['VRd_max_kN']:.1f} kN</div>
            </div>
            <div class="spacer"></div>
            <div class="ratio-block" style="margin-bottom:0;">
              <div class="ratio-header">
                <span class="ratio-name">Traction acier — VRd,s</span>
                <span class="ratio-val" style="color:{c2_txt};">{tau2:.3f}</span>
              </div>
              <div class="ratio-track"><div class="ratio-fill" style="width:{w2:.1f}%;background:{c2_grad};"></div></div>
              <div class="ratio-meta">VEd = {v_ed:.1f} kN &nbsp;/&nbsp; VRd,s = {res['VRd_s_kN']:.1f} kN</div>
            </div>
          </div>
        </body></html>""", height=210)

        # ── Vérifications constructives ───────────────────────────────────────
        ok_rho = res["ok_rho_w_min"]
        ok_s   = res["ok_s_max"]
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Vérifications constructives</div>
            <div class="checks-row">
                <div class="check-chip {'ok' if ok_rho else 'fail'}">
                    {'✓' if ok_rho else '✗'}&nbsp; ρw ≥ ρw,min &nbsp;
                    <span style="opacity:0.7">({res['rho_w']:.5f} ≥ {res['rho_w_min']:.5f})</span>
                </div>
                <div class="check-chip {'ok' if ok_s else 'fail'}">
                    {'✓' if ok_s else '✗'}&nbsp; s ≤ sl,max &nbsp;
                    <span style="opacity:0.7">({s_etr} ≤ {res['s_max_mm']:.0f} mm)</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Paramètres intermédiaires ─────────────────────────────────────────
        with st.expander("Paramètres intermédiaires du calcul"):
            c1, c2 = st.columns(2)
            params = [
                ("ν₁ (béton fissuré)", f"{res['nu1']:.4f}", "—"),
                ("αcw (effort normal)", f"{res['alpha_cw']:.4f}", "—"),
                ("σcp", f"{res['sigma_cp_MPa']:.3f}", "MPa"),
                ("cot θ", f"{res['cot_theta']:.4f}", "—"),
                ("fcd", f"{res['fcd_MPa']:.2f}", "MPa"),
                ("fywd", f"{res['fywd_MPa']:.2f}", "MPa"),
                ("d", f"{res['d_mm']:.1f}", "mm"),
                ("z", f"{res['z_mm']:.1f}", "mm"),
                ("Asw", f"{res['Asw_mm2']:.2f}", "mm²"),
            ]
            for i, (label, val, unit) in enumerate(params):
                col = c1 if i % 2 == 0 else c2
                with col:
                    st.markdown(
                        f"<div style='font-family:DM Mono,monospace;font-size:0.72rem;"
                        f"padding:0.3rem 0;border-bottom:1px solid #F3F4F6;color:#374151'>"
                        f"<span style='color:#9CA3AF'>{label}</span><br>"
                        f"<strong style='color:#111827'>{val}</strong>"
                        f"<span style='color:#9CA3AF;margin-left:4px'>{unit}</span></div>",
                        unsafe_allow_html=True
                    )

# =============================================================================
# GRAPHIQUE SENSIBILITÉ — Influence de l'angle θ
# =============================================================================
if procedures_ok:
    st.divider()
    st.markdown(
        "<div class='section-title'>Analyse de sensibilité — Influence de l'angle θ</div>",
        unsafe_allow_html=True
    )

    scan = longrine.scan_theta(v_ed, n_ed)
    thetas  = [r["theta"]       for r in scan]
    tau_max = [r["tau_VRd_max"] for r in scan]
    tau_s   = [r["tau_VRd_s"]   for r in scan]
    y_top   = max(max(tau_max), max(tau_s), 1.05) * 1.12

    fig = go.Figure()
    fig.add_hrect(y0=0,    y1=0.75,  fillcolor="rgba(16,185,129,0.05)",  line_width=0)
    fig.add_hrect(y0=0.75, y1=1.0,   fillcolor="rgba(245,158,11,0.07)",  line_width=0)
    fig.add_hrect(y0=1.0,  y1=y_top, fillcolor="rgba(239,68,68,0.06)",   line_width=0)
    fig.add_trace(go.Scatter(
        x=thetas, y=tau_max, name="Bielle comprimée (VRd,max)",
        line=dict(color="#2563EB", width=2.5), fill="tozeroy",
        fillcolor="rgba(37,99,235,0.07)",
        hovertemplate="θ = %{x:.1f}°<br>τ = %{y:.3f}<extra>Bielle</extra>"
    ))
    fig.add_trace(go.Scatter(
        x=thetas, y=tau_s, name="Traction acier (VRd,s)",
        line=dict(color="#EF4444", width=2.5), fill="tozeroy",
        fillcolor="rgba(239,68,68,0.07)",
        hovertemplate="θ = %{x:.1f}°<br>τ = %{y:.3f}<extra>Acier</extra>"
    ))
    fig.add_hline(y=1.0, line=dict(color="#111827", width=1.5, dash="dot"),
        annotation_text="Limite EC2 = 1.0", annotation_position="top right",
        annotation_font=dict(size=11, color="#374151", family="DM Sans, sans-serif"))
    fig.add_vline(x=theta, line=dict(color="#6B7280", width=1.5, dash="dash"),
        annotation_text=f"θ = {theta:.1f}°", annotation_position="top left",
        annotation_font=dict(size=11, color="#374151", family="DM Sans, sans-serif"))
    fig.update_layout(
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        font=dict(family="DM Sans, sans-serif", size=12, color="#111827"),
        margin=dict(l=10, r=10, t=30, b=10), height=340,
        xaxis=dict(
            title=dict(text="Angle θ (°)", font=dict(color="#374151", size=12)),
            range=[21, 46], showgrid=True, gridcolor="#E5E7EB", gridwidth=1,
            zeroline=False, linecolor="#D1D5DB", linewidth=1, showline=True,
            tickfont=dict(family="DM Mono, monospace", size=11, color="#374151"),
            ticks="outside", tickcolor="#D1D5DB",
        ),
        yaxis=dict(
            title=dict(text="Taux VEd / VRd", font=dict(color="#374151", size=12)),
            showgrid=True, gridcolor="#E5E7EB", gridwidth=1,
            zeroline=False, linecolor="#D1D5DB", linewidth=1, showline=True,
            tickfont=dict(family="DM Mono, monospace", size=11, color="#374151"),
            ticks="outside", tickcolor="#D1D5DB", range=[0, y_top],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=12, color="#374151"), bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="#E5E7EB", borderwidth=1),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#E5E7EB",
                        font=dict(color="#111827", family="DM Mono, monospace", size=11)),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# =============================================================================
# FLEXION & FLÈCHE
# =============================================================================
if procedures_ok:
    st.divider()
    col_flex, col_fleche = st.columns(2, gap="large")

    with col_flex:
        st.markdown(
            "<div class='section-title'>Vérification Flexion — EC2 §6.1</div>",
            unsafe_allow_html=True
        )
        res_flex = longrine.check_bending(m_ed, verbose=False)
        tau_M = res_flex["tau_MRd"]

        # Statut
        if res_flex["ok_global"]:
            st.markdown("""
            <div class="status-ok">
                <span style="font-size:1.4rem;">✅</span>
                <div>
                    <div class="status-text">FLEXION CONFORME</div>
                    <div style="font-size:0.75rem;color:#065F46;margin-top:0.15rem;">
                        MEd ≤ MRd — EC2 §6.1 satisfait
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-fail">
                <span style="font-size:1.4rem;">❌</span>
                <div>
                    <div class="status-text">FLEXION NON CONFORME</div>
                    <div style="font-size:0.75rem;color:#991B1B;margin-top:0.15rem;">
                        Une ou plusieurs vérifications EC2 §6.1 non satisfaites
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        def tau_color_css(v):
            if v <= 0.75: return "#065F46", "linear-gradient(90deg,#10B981,#34D399)"
            if v <= 1.00: return "#92400E", "linear-gradient(90deg,#F59E0B,#FCD34D)"
            return "#991B1B", "linear-gradient(90deg,#EF4444,#F87171)"

        c_txt, c_grad = tau_color_css(tau_M)
        w_pct = min(tau_M * 100, 100)
        components.html(f"""<!DOCTYPE html><html><head>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
        <style>
          *{{margin:0;padding:0;box-sizing:border-box;}}
          body{{background:transparent;font-family:'DM Sans',sans-serif;}}
          .card{{background:#FFF;border-radius:12px;padding:1.3rem 1.5rem;border:1px solid #E5E7EB;box-shadow:0 1px 3px rgba(0,0,0,.04);}}
          .card-title{{font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;margin-bottom:1rem;}}
          .ratio-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:.35rem;}}
          .ratio-name{{font-family:'DM Sans',sans-serif;font-size:.82rem;font-weight:600;color:#111827;}}
          .ratio-val{{font-family:'DM Mono',monospace;font-size:.82rem;font-weight:700;}}
          .ratio-track{{background:#E5E7EB;border-radius:999px;height:7px;overflow:hidden;}}
          .ratio-fill{{height:100%;border-radius:999px;}}
          .ratio-meta{{font-family:'DM Mono',monospace;font-size:.68rem;color:#6B7280;margin-top:.28rem;}}
          .chip{{display:inline-flex;align-items:center;gap:.3rem;border-radius:6px;padding:.3rem .65rem;font-family:'DM Mono',monospace;font-size:.68rem;margin-top:.8rem;margin-right:.3rem;}}
          .ok{{background:#ECFDF5;border:1px solid #6EE7B7;color:#065F46;}}
          .fail{{background:#FEF2F2;border:1px solid #FCA5A5;color:#991B1B;}}
        </style></head><body>
          <div class="card">
            <div class="card-title">Taux d'utilisation — Flexion</div>
            <div class="ratio-header">
              <span class="ratio-name">MEd / MRd</span>
              <span class="ratio-val" style="color:{c_txt};">{tau_M:.3f}</span>
            </div>
            <div class="ratio-track"><div class="ratio-fill" style="width:{w_pct:.1f}%;background:{c_grad};"></div></div>
            <div class="ratio-meta">MEd = {m_ed:.1f} kN·m &nbsp;/&nbsp; MRd = {res_flex['MRd_kNm']:.1f} kN·m</div>
            <div>
              <span class="chip {'ok' if res_flex['sous_arme'] else 'fail'}">
                {'✓' if res_flex['sous_arme'] else '✗'} Section sous-armée (pivot A/B)
              </span>
              <span class="chip {'ok' if res_flex['ok_asl_max'] else 'fail'}">
                {'✓' if res_flex['ok_asl_max'] else '✗'} Asl ≤ 4%·Ac
              </span>
            </div>
          </div>
        </body></html>""", height=190)

        with st.expander("Paramètres intermédiaires — Flexion"):
            c1, c2 = st.columns(2)
            params_flex = [
                ("x (axe neutre)", f"{res_flex['x_mm']:.1f}", "mm"),
                ("d (haut. utile)", f"{res_flex['d_mm']:.1f}", "mm"),
                ("MRd", f"{res_flex['MRd_kNm']:.2f}", "kN·m"),
                ("μEd", f"{res_flex['mu_Ed']:.4f}", "—"),
                ("εs", f"{res_flex['eps_s_permil']:.3f}", "‰"),
                ("εyd", f"{res_flex['eps_yd_permil']:.3f}", "‰"),
                ("λ (bloc rect.)", f"{res_flex['lam']:.3f}", "—"),
                ("η (bloc rect.)", f"{res_flex['eta']:.3f}", "—"),
                ("fyd", f"{res_flex['fyd_MPa']:.2f}", "MPa"),
            ]
            for i, (label, val, unit) in enumerate(params_flex):
                col = c1 if i % 2 == 0 else c2
                with col:
                    st.markdown(
                        f"<div style='font-family:DM Mono,monospace;font-size:0.72rem;"
                        f"padding:0.3rem 0;border-bottom:1px solid #F3F4F6;color:#374151'>"
                        f"<span style='color:#9CA3AF'>{label}</span><br>"
                        f"<strong style='color:#111827'>{val}</strong>"
                        f"<span style='color:#9CA3AF;margin-left:4px'>{unit}</span></div>",
                        unsafe_allow_html=True
                    )

    with col_fleche:
        st.markdown(
            "<div class='section-title'>Vérification Flèche — EC2 §7.4</div>",
            unsafe_allow_html=True
        )
        res_fl = longrine.check_deflection(m_ed_ser, L_portee, psi2, support_type)
        tau_fl = res_fl["tau_f_long"]

        if res_fl["ok_global"]:
            st.markdown("""
            <div class="status-ok">
                <span style="font-size:1.4rem;">✅</span>
                <div>
                    <div class="status-text">FLÈCHE CONFORME</div>
                    <div style="font-size:0.75rem;color:#065F46;margin-top:0.15rem;">
                        f ≤ L/250 — EC2 §7.4.1 satisfait
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-fail">
                <span style="font-size:1.4rem;">❌</span>
                <div>
                    <div class="status-text">FLÈCHE NON CONFORME</div>
                    <div style="font-size:0.75rem;color:#991B1B;margin-top:0.15rem;">
                        Flèche différée f > L/250 — EC2 §7.4.1 non satisfait
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        c_txt_f, c_grad_f = tau_color_css(tau_fl)
        c_txt_i, c_grad_i = tau_color_css(res_fl["tau_f_inst"])
        w_long = min(tau_fl * 100, 100)
        w_inst = min(res_fl["tau_f_inst"] * 100, 100)
        fiss_label = "Section fissurée (ζ > 0)" if res_fl["fissure"] else "Section non fissurée"
        fiss_cls   = "fail" if res_fl["fissure"] else "ok"
        fiss_icon  = "⚠" if res_fl["fissure"] else "✓"
        components.html(f"""<!DOCTYPE html><html><head>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
        <style>
          *{{margin:0;padding:0;box-sizing:border-box;}}
          body{{background:transparent;font-family:'DM Sans',sans-serif;}}
          .card{{background:#FFF;border-radius:12px;padding:1.3rem 1.5rem;border:1px solid #E5E7EB;box-shadow:0 1px 3px rgba(0,0,0,.04);}}
          .card-title{{font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6B7280;margin-bottom:1rem;}}
          .ratio-block{{margin-bottom:.9rem;}}
          .ratio-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:.35rem;}}
          .ratio-name{{font-family:'DM Sans',sans-serif;font-size:.82rem;font-weight:600;color:#111827;}}
          .ratio-val{{font-family:'DM Mono',monospace;font-size:.82rem;font-weight:700;}}
          .ratio-track{{background:#E5E7EB;border-radius:999px;height:7px;overflow:hidden;}}
          .ratio-fill{{height:100%;border-radius:999px;}}
          .ratio-meta{{font-family:'DM Mono',monospace;font-size:.68rem;color:#6B7280;margin-top:.28rem;}}
          .chip{{display:inline-flex;align-items:center;gap:.3rem;border-radius:6px;padding:.3rem .65rem;font-family:'DM Mono',monospace;font-size:.68rem;margin-top:.8rem;margin-right:.3rem;}}
          .ok{{background:#ECFDF5;border:1px solid #6EE7B7;color:#065F46;}}
          .warn{{background:#FFFBEB;border:1px solid #FCD34D;color:#92400E;}}
          .fail{{background:#FEF2F2;border:1px solid #FCA5A5;color:#991B1B;}}
        </style></head><body>
          <div class="card">
            <div class="card-title">Taux d'utilisation — Flèche (L = {L_portee:.1f} m)</div>
            <div class="ratio-block">
              <div class="ratio-header">
                <span class="ratio-name">Flèche instantanée</span>
                <span class="ratio-val" style="color:{c_txt_i};">{res_fl['tau_f_inst']:.3f}</span>
              </div>
              <div class="ratio-track"><div class="ratio-fill" style="width:{w_inst:.1f}%;background:{c_grad_i};"></div></div>
              <div class="ratio-meta">f_inst = {res_fl['f_inst_mm']:.1f} mm &nbsp;/&nbsp; f_adm = L/250 = {res_fl['f_adm_mm']:.1f} mm</div>
            </div>
            <div class="ratio-block" style="margin-bottom:0;">
              <div class="ratio-header">
                <span class="ratio-name">Flèche différée (fluage)</span>
                <span class="ratio-val" style="color:{c_txt_f};">{tau_fl:.3f}</span>
              </div>
              <div class="ratio-track"><div class="ratio-fill" style="width:{w_long:.1f}%;background:{c_grad_f};"></div></div>
              <div class="ratio-meta">f_long = {res_fl['f_long_mm']:.1f} mm &nbsp;/&nbsp; f_adm = L/250 = {res_fl['f_adm_mm']:.1f} mm</div>
            </div>
            <div>
              <span class="chip {fiss_cls}">{fiss_icon} {fiss_label}</span>
            </div>
          </div>
        </body></html>""", height=240)

        with st.expander("Paramètres intermédiaires — Flèche"):
            c1, c2 = st.columns(2)
            params_fl = [
                ("Mcr (fissuration)", f"{res_fl['Mcr_kNm']:.2f}", "kN·m"),
                ("ζ (coeff. fiss.)", f"{res_fl['zeta']:.4f}", "—"),
                ("xI (axe neut. I)", f"{res_fl['x_I_mm']:.1f}", "mm"),
                ("xII (axe neut. II)", f"{res_fl['x_II_mm']:.2f}", "mm"),
                ("αe (ratio mod.)", f"{res_fl['alphae']:.3f}", "—"),
                ("Ecm", f"{res_fl['Ecm_MPa']:.0f}", "MPa"),
                ("fctm", f"{res_fl['fctm_MPa']:.3f}", "MPa"),
                ("φ∞ (fluage)", f"{res_fl['phi_inf']:.1f}", "—"),
                ("κ (schéma stat.)", f"{res_fl['kappa']:.4f}", "—"),
            ]
            for i, (label, val, unit) in enumerate(params_fl):
                col = c1 if i % 2 == 0 else c2
                with col:
                    st.markdown(
                        f"<div style='font-family:DM Mono,monospace;font-size:0.72rem;"
                        f"padding:0.3rem 0;border-bottom:1px solid #F3F4F6;color:#374151'>"
                        f"<span style='color:#9CA3AF'>{label}</span><br>"
                        f"<strong style='color:#111827'>{val}</strong>"
                        f"<span style='color:#9CA3AF;margin-left:4px'>{unit}</span></div>",
                        unsafe_allow_html=True
                    )