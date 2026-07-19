import streamlit as st
from sqlalchemy import select
from datetime import date

from engines import makesession  # Repris de tes imports précédents
from datamodel import Impot  # La classe ORM générée juste avant


def view_gestion_impots():
    st.title("📑 Gestion des Impôts")

    # 1. Sélection de l'année (Filtre principal)
    current_year = date.today().year
    years_options = list(range(current_year - 5, current_year + 2))

    selected_year = st.selectbox(
        "Sélectionner l'année fiscale :",
        options=years_options,
        index=years_options.index(current_year)
    )

    # 2. Récupération ou initialisation de l'objet Impot pour cette année
    with makesession() as session:
        # On cherche s'il y a déjà une ligne pour cette année
        db_impot = session.scalar(
            select(Impot).where(Impot.annee == selected_year)
        )

        # Si l'objet existe, on passe en mode édition, sinon on crée une instance vierge
        if db_impot:
            st.info(f"ℹ️ Données existantes trouvées pour l'année {selected_year}. Mode Édition activé.")
            impot_data = db_impot
        else:
            st.success(f"✨ Aucun enregistrement pour {selected_year}. Mode Saisie initialisé.")
            impot_data = Impot(annee=selected_year, revenu_imposable_1=0.0, revenu_imposable_2=0.0)

    # 3. Formulaire de saisie / édition
    # Note : On utilise un st.form pour bloquer l'écriture en BDD tant qu'on n'a pas cliqué sur Valider
    with st.form(key=f"form_impots_{selected_year}"):

        st.subheader("💰 Revenus Imposables")
        col1, col2 = st.columns(2)
        with col1:
            rev_1 = st.number_input("Revenu Imposable Foyer 1 (€) :", value=float(impot_data.revenu_imposable_1),
                                    min_value=0.0, format="%.2f")
        with col2:
            rev_2 = st.number_input("Revenu Imposable Foyer 2 (€) :", value=float(impot_data.revenu_imposable_2),
                                    min_value=0.0, format="%.2f")

        st.subheader("📉 Déductions & Crédits d'Impôt")
        col3, col4, col5 = st.columns(3)
        with col3:
            emploi = st.number_input("Emploi salarié (€) :", value=float(impot_data.emploi_salarie or 0.0),
                                     min_value=0.0, format="%.2f")
            tx_deduc = st.number_input("Taux déduction emploi (%) :",
                                       value=float(impot_data.tx_deduction_emploi or 0.0), min_value=0.0,
                                       max_value=100.0, format="%.2f")
        with col4:
            dons = st.number_input("Dons effectués (€) :", value=float(impot_data.dons or 0.0), min_value=0.0,
                                   format="%.2f")
            dons_deduc = st.number_input("Dons déductibles (%) :", value=float(impot_data.dons_deductible or 0.0),
                                         min_value=0.0, max_value=100.0, format="%.2f")
        with col5:
            syndicat = st.number_input("Cotisation Syndicale (€) :", value=float(impot_data.syndicat_deductible or 0.0),
                                       min_value=0.0, format="%.2f")

        st.subheader("🏦 Prélèvements & Retenues")
        col6, col7, col8 = st.columns(3)
        with col6:
            impot_av_red = st.number_input("Impôt avant réduction (€) :",
                                           value=float(impot_data.impot_avant_reduction or 0.0), min_value=0.0,
                                           format="%.2f")
            impot_prop = st.number_input("Impôt proportionnel (€) :",
                                         value=float(impot_data.impot_proportionnel or 0.0), min_value=0.0,
                                         format="%.2f")
        with col7:
            retenue = st.number_input("Retenue à la source (€) :", value=float(impot_data.retenue_source or 0.0),
                                      min_value=0.0, format="%.2f")
            acompte = st.number_input("Acomptes prélevés (€) :", value=float(impot_data.acompte or 0.0), min_value=0.0,
                                      format="%.2f")
        with col8:
            avance = st.number_input("Avance perçue (€) :", value=float(impot_data.avance or 0.0), min_value=0.0,
                                     format="%.2f")
            sociaux = st.number_input("Prélèvements Sociaux (€) :", value=float(impot_data.prelevements_sociaux or 0.0),
                                      min_value=0.0, format="%.2f")
            # Ajout du dernier champ restant de ton modèle
            prelev_forfaitaire = st.number_input("Prélèvement Forfaitaire (€) :",
                                                 value=float(impot_data.prelevement_forfaitaire or 0.0), min_value=0.0,
                                                 format="%.2f")

        st.divider()

        # 4. Boutons d'actions
        btn_valider, btn_annuler, _ = st.columns([1, 1, 2])

        with btn_valider:
            submit = st.form_submit_button("Sauvegarder ✅", type="primary", use_container_width=True)

        with btn_annuler:
            # st.form_submit_button est requis pour capturer un clic dans un formulaire, même pour annuler
            cancel = st.form_submit_button("Annuler ❌", use_container_width=True)

        # 5. Logique de traitement après clic
        if submit:
            with makesession() as session:
                # Si c'est une édition, on ré-attache ou fusionne l'objet dans la session en cours
                if impot_data.id_impot is not None:
                    obj_to_save = session.merge(impot_data)
                else:
                    obj_to_save = impot_data
                    session.add(obj_to_save)

                # Application des valeurs saisies dans l'interface vers l'objet ORM
                obj_to_save.revenu_imposable_1 = rev_1
                obj_to_save.revenu_imposable_2 = rev_2
                obj_to_save.emploi_salarie = emploi
                obj_to_save.tx_deduction_emploi = tx_deduc
                obj_to_save.dons = dons
                obj_to_save.dons_deductible = dons_deduc
                obj_to_save.syndicat_deductible = syndicat
                obj_to_save.impot_avant_reduction = impot_av_red
                obj_to_save.impot_proportionnel = impot_prop
                obj_to_save.retenue_source = retenue
                obj_to_save.acompte = acompte
                obj_to_save.avance = avance
                obj_to_save.prelevements_sociaux = sociaux
                obj_to_save.prelevement_forfaitaire = prelev_forfaitaire

                session.flush()
                if not st.session_state.get('test_mode', False):
                    session.commit()

                st.success(f"💾 Les données fiscales de l'année {selected_year} ont été enregistrées avec succès !")
                st.rerun()

        if cancel:
            st.warning("❌ Modifications annulées.")
            st.rerun()