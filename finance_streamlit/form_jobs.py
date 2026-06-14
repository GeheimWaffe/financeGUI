import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta
from sqlalchemy import select, func
from engines import makesession  # Repris de tes imports précédents
from datamodel import Job, Mouvement  # Adapte le nom du module si nécessaire


def rollback_job(job_id: int):
    """Fonction qui gère la suppression/désactivation en cascade des mouvements d'un job."""
    try:
        with makesession() as session:
            # Récupération du Job
            job = session.scalar(select(Job).where(Job.job_id == job_id))

            if job:
                # Si ta relation contient cascade="all, delete-orphan",
                # supprimer le job supprimera automatiquement les mouvements liés en BDD.
                session.delete(job)

                # S'il ne faut PAS supprimer le job mais juste "désactiver" les mouvements :
                # (Décommente si tu as un attribut 'actif' ou similaire sur Mouvement)
                # session.execute(
                #     update(Mouvement).where(Mouvement.job_id == job_id).values(actif=False)
                # )

                session.flush()
                if not st.session_state.get('test_mode', False):
                    session.commit()
                return True
            return False
    except Exception as e:
        st.error(f"Erreur technique lors du rollback : {e}")
        return False


def view_log():
    st.title("📊 Historique et Logs des Jobs")

    # ==========================================
    # SECTION 1 : GRAPHIQUE DES 30 DERNIERS JOURS
    # ==========================================
    st.subheader("Activité des 30 derniers jours (Volume de mouvements)")

    date_30_days_ago = datetime.now() - timedelta(days=30)

    with makesession() as session:
        # Requête pour grouper les mouvements par jour de job
        graph_stmt = (
            select(
                func.date(Job.job_timestamp).label("jour"),
                func.count(Mouvement.index).label("nb_mouvements")  # Adapte Mouvement.id selon ton modèle
            )
            .join(Mouvement, Job.mouvements)
            .where(Job.job_timestamp >= date_30_days_ago)
            .group_by(func.date(Job.job_timestamp))
        )
        graph_data = session.execute(graph_stmt).all()

    if graph_data:
        df_graph = pd.DataFrame(graph_data, columns=["Jour", "Nombre de mouvements"])
        df_graph["Jour"] = pd.to_datetime(df_graph["Jour"])

        # Graphique Altair pour un rendu propre et interactif
        chart = alt.Chart(df_graph).mark_bar(color="#4682B4").encode(
            x=alt.X("Jour:T", title="Date de l'exécution", axis=alt.Axis(format="%d %b")),
            y=alt.Y("Nombre de mouvements:Q", title="Mouvements créés"),
            tooltip=["Jour", "Nombre de mouvements"]
        ).properties(height=250)

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Aucun mouvement généré par des jobs au cours des 30 derniers jours.")

    st.divider()

    # ==========================================
    # SECTION 2 : FILTRES & TABLE DES JOBS
    # ==========================================
    st.subheader("🔍 Exploration et Rollback des Jobs")

    # Initialisation des filtres temporels demandés
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Date de début", value=date.today() - timedelta(days=14))
    with col_d2:
        end_date = st.date_input("Date de fin", value=date.today())

    if start_date > end_date:
        st.error("Erreur : La date de début doit être antérieure à la date de fin.")
        return

    # Récupération des jobs dans la plage de dates choisie
    with makesession() as session:
        # Jointure externe pour avoir le compte des mouvements, même s'il y en a 0 (ex: shutdown)
        jobs_stmt = (
            select(
                Job.job_id,
                Job.job_key,
                Job.job_timestamp,
                func.count(Mouvement.index).label("total_mouvements")
            ).join(Mouvement, Job.mouvements)
            .where(
                func.date(Job.job_timestamp).between(start_date, end_date)
            )
            .group_by(Job.job_id)
            .order_by(Job.job_timestamp.desc())
        )
        jobs_results = session.execute(jobs_stmt).all()

    if not jobs_results:
        st.warning("Aucun job trouvé pour la période sélectionnée.")
        return

    # Construction du DataFrame pour l'affichage
    df_jobs = pd.DataFrame([
        {
            "ID Job": r.job_id,
            "Type de Job": r.job_key,
            "Date d'Exécution": r.job_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Mouvements impactés": r.total_mouvements
        } for r in jobs_results
    ])

    # Affichage du DataFrame avec sélection de ligne (Single-choice)
    st.write("Sélectionnez un job pour accéder aux options de gestion :")

    selection = st.dataframe(
        df_jobs,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",  # Permet de capter la sélection instantanément
        selection_mode="single-row"
    )

    # ==========================================
    # SECTION 3 : LOGIQUE DE SELECTION & ROLLBACK
    # ==========================================
    selected_rows = selection.get("selection", {}).get("rows", [])

    if selected_rows:
        # Récupération de l'index sélectionné
        selected_index = selected_rows[0]
        selected_job_id = int(df_jobs.iloc[selected_index]["ID Job"])
        selected_job_type = df_jobs.iloc[selected_index]["Type de Job"]
        selected_mvt_count = df_jobs.iloc[selected_index]["Mouvements impactés"]

        st.write("")  # Espacement

        # Zone d'action contextuelle
        with st.container(border=True):
            st.markdown(f"⚠️ **Job Sélectionné : ID {selected_job_id} ({selected_job_type})**")
            st.caption(f"Ce job contient **{selected_mvt_count}** mouvement(s) associé(s).")

            # Bouton de Rollback destructeur / restrictif
            if st.button("⏪ Retour Arrière (Désactiver/Supprimer)", type="primary"):
                with st.spinner("Annulation du job en cours..."):
                    success = rollback_job(selected_job_id)

                    if success:
                        st.success(f"Le Job {selected_job_id} et ses {selected_mvt_count} mouvements ont été annulés.")
                        # On force le rafraîchissement pour mettre la table à jour
                        st.rerun()
                    else:
                        st.error("Échec de l'opération de Retour Arrière.")
    else:
        st.caption("💡 Cliquez sur une ligne du tableau pour activer l'option de Retour Arrière.")