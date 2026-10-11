"""
Writes eval/job_ads.jsonl: 30 labelled job ads used to evaluate every prompt and model.

The ads are SYNTHETIC: written for this project in the style of real German and
English data job ads. Company names are invented. Each ad has the correct answer
("label") that the extractor should produce. Some ads contain on purpose the
cases that trip models up: German levels written in words, monthly or hourly pay,
"German is a plus", skills spelled in different ways.

Run:  python scripts/make_eval_set.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "eval" / "job_ads.jsonl"


def label(title, seniority, skills, german, english, mode, smin, smax, location):
    return {"job_title": title, "seniority": seniority, "skills": sorted(skills), "german_level": german,
            "english_required": english, "work_mode": mode, "salary_min": smin, "salary_max": smax,
            "location": location}


ADS = [
    ("""Junior Data Analyst (m/w/d) – Nordwind Logistik GmbH
Standort: Hamburg
Deine Aufgaben: Aufbau von Reports und Dashboards in Power BI, Analyse von Lieferdaten mit SQL.
Dein Profil: Abgeschlossenes Studium, erste Erfahrung mit SQL und Excel, Python von Vorteil.
Sprachen: Deutsch B2, gute Englischkenntnisse.
Wir bieten: Hybrides Arbeiten (2 Tage pro Woche im Büro), 46.000 – 52.000 € brutto/Jahr.""",
     label("Junior Data Analyst", "junior", ["power bi", "sql", "excel", "python"], "B2", True, "hybrid", 46000, 52000, "Hamburg")),

    ("""Data Analyst – Marketing Analytics | Kiezkraft Media
Location: Berlin (fully remote within Germany possible)
You will analyse campaign performance, run A/B tests and build Looker dashboards.
Requirements: 2+ years experience, strong SQL, Python (pandas), Google Analytics.
Languages: English fluent. German is a plus, not a must.
Salary: 55k–65k EUR per year.""",
     label("Data Analyst", "mid", ["a/b testing", "google analytics", "looker", "pandas", "python", "sql"], "unspecified", True, "remote", 55000, 65000, "Berlin")),

    ("""Werkstudent (m/w/d) Business Intelligence
Ort: Hannover
Du unterstützt unser BI-Team bei der Pflege von Tableau-Dashboards und Datenabfragen mit SQL.
Gute Excel-Kenntnisse, idealerweise erste Erfahrung mit Python.
Sehr gute Deutschkenntnisse (C1) und gutes Englisch.
16–20 Stunden pro Woche, 15,50 € pro Stunde, Arbeit vor Ort.""",
     label("Werkstudent Business Intelligence", "working_student", ["excel", "python", "sql", "tableau"], "C1", True, "onsite", None, None, "Hannover")),

    ("""Senior Data Engineer – Fintech Hafenbank
Location: Frankfurt am Main, hybrid (3 days per week in the office)
Design and run data pipelines with Databricks, Spark and Airflow on AWS. dbt for transformations.
5+ years of experience. Docker and Git are daily tools.
English required, German not required.
Compensation: 85.000 – 100.000 € per year.""",
     label("Senior Data Engineer", "senior", ["airflow", "aws", "databricks", "dbt", "docker", "git", "spark"], "none", True, "hybrid", 85000, 100000, "Frankfurt am Main")),

    ("""Praktikum Datenanalyse (m/w/d) – Sonnenfeld Energie AG
Einsatzort: München
Aufgaben: Auswertung von Verbrauchsdaten, Erstellung von Berichten in Excel und Power BI.
Voraussetzungen: Studium der Wirtschaftsinformatik oder ähnlich, Grundkenntnisse in R oder Python, Statistikkenntnisse.
Deutsch verhandlungssicher, Englisch gut.
Vergütung: 1.800 € pro Monat. Vor Ort in unserem Büro in München.""",
     label("Praktikum Datenanalyse", "intern", ["excel", "power bi", "python", "r", "statistics"], "C1", True, "onsite", 21600, 21600, "München")),

    ("""BI Developer (m/w/d) - Alpenblick Versicherung
Standort: Köln
Entwicklung von ETL-Strecken und Datenmodellen im SAP BW Umfeld, Reporting mit Power BI.
Mehrjährige Berufserfahrung, sehr gute SQL-Kenntnisse.
Deutsch auf Muttersprachniveau, Englisch von Vorteil.
Hybrid: 50 % mobiles Arbeiten. Gehalt: 62.000 bis 72.000 € jährlich.""",
     label("BI Developer", "mid", ["etl", "power bi", "sap", "sql"], "native", None, "hybrid", 62000, 72000, "Köln")),

    ("""Graduate Data Analyst – Lindenhof Retail
Location: Düsseldorf
Entry-level role for recent graduates. You will clean sales data in Python and build reports in Tableau.
Requirements: degree in a quantitative field, SQL basics, Excel.
English required; German B1 or higher.
Office-based. Salary 44,000 EUR a year.""",
     label("Graduate Data Analyst", "junior", ["excel", "python", "sql", "tableau"], "B1", True, "onsite", 44000, 44000, "Düsseldorf")),

    ("""Head of Data & Analytics (m/w/d) – Mittelstand Maschinenbau
Ort: Stuttgart
Sie führen ein Team von 8 Analysten und Data Engineers und verantworten die Datenstrategie.
Erfahrung mit Azure, Snowflake und Power BI, Führungserfahrung.
Deutsch fließend, Englisch verhandlungssicher.
Remote-Anteil möglich, 2 Tage im Büro. Gehalt nach Vereinbarung.""",
     label("Head of Data & Analytics", "lead", ["azure", "power bi", "snowflake"], "C1", True, "hybrid", None, None, "Stuttgart")),

    ("""Data Scientist (Junior) – Okapi Health
Location: Leipzig, 100% remote possible
Build machine learning models in Python (scikit-learn, pandas), SQL for data extraction, Git.
Knowledge of statistics required. English fluent. No German required.
Salary range: 50,000 – 58,000 EUR.""",
     label("Data Scientist", "junior", ["git", "machine learning", "pandas", "python", "scikit-learn", "sql", "statistics"], "none", True, "remote", 50000, 58000, "Leipzig")),

    ("""Reporting Analyst (m/w/d) – Stadtwerke Talheim
Standort: Bielefeld
Erstellung monatlicher Berichte mit Excel (inkl. VBA) und Power Query, Pflege der Datenbanken.
Erste Berufserfahrung, sicherer Umgang mit MS Office.
Deutsch C1. Präsenz vor Ort.
Vergütung nach TV-V, ca. 3.900 € monatlich.""",
     label("Reporting Analyst", "unspecified", ["excel", "power query", "vba"], "C1", None, "onsite", 46800, 46800, "Bielefeld")),

    ("""Product Analyst – Pixelpost (app startup)
Berlin, hybrid, 2 days a week in the office
Own product metrics, run A/B tests, write SQL in BigQuery and visualise in Looker Studio.
Python is nice to have. Mid-level, 3+ years.
English is our company language; German not needed.
Salary: €60k – €70k.""",
     label("Product Analyst", "mid", ["a/b testing", "bigquery", "looker", "python", "sql"], "none", True, "hybrid", 60000, 70000, "Berlin")),

    ("""Junior Controller mit Schwerpunkt Datenanalyse (m/w/d)
Standort: Hildesheim
Unterstützung bei Planung und Forecast, Analysen in Excel und SAP, Aufbau erster Power BI Berichte.
Berufseinsteiger willkommen. Deutsch sehr gut (C1), Englisch Grundkenntnisse.
Arbeitsort vor Ort. 42.000 – 47.000 €.""",
     label("Junior Controller mit Schwerpunkt Datenanalyse", "junior", ["excel", "power bi", "sap"], "C1", True, "onsite", 42000, 47000, "Hildesheim")),

    ("""Analytics Engineer – Nordlicht Commerce
Location: Hamburg or remote (Germany)
Model data with dbt and SQL on Snowflake, orchestrate with Airflow, version control with Git.
2–4 years experience. Fluent English; German B2 is a plus.
Salary: 65.000–75.000 EUR p.a.""",
     label("Analytics Engineer", "mid", ["airflow", "dbt", "git", "snowflake", "sql"], "unspecified", True, "remote", 65000, 75000, "Hamburg")),

    ("""Werkstudent Data Science (m/w/d) – Mobilität der Zukunft
Ort: Darmstadt, hybrid
Du entwickelst Prognosemodelle mit Python und unterstützt bei Datenaufbereitung in SQL.
Studium der Informatik, Mathematik oder vergleichbar. Kenntnisse in Machine Learning.
Deutsch und Englisch fließend.
Stundenlohn: 17 €.""",
     label("Werkstudent Data Science", "working_student", ["machine learning", "python", "sql"], "C1", True, "hybrid", None, None, "Darmstadt")),

    ("""Data Quality Analyst – Medilab Diagnostics
Location: Munich, on-site
Monitor data quality in clinical data pipelines using SQL and Python. Jira for tickets, Scrum team.
2+ years of experience. English required. German A2 or higher.
Salary 52,000–56,000 EUR.""",
     label("Data Quality Analyst", "mid", ["jira", "python", "scrum", "sql"], "A2", True, "onsite", 52000, 56000, "Munich")),

    ("""Senior BI Consultant (m/w/d) – Beratungshaus Elbe
Standort: Dresden
Konzeption von Data-Warehouse-Lösungen, Umsetzung mit Qlik und SQL, Kundenprojekte.
Mindestens 6 Jahre Erfahrung, Reisebereitschaft 30 %.
Deutsch verhandlungssicher, Englisch sehr gut.
Hybrid. Gehalt: 75 – 90 Tsd. € pro Jahr.""",
     label("Senior BI Consultant", "senior", ["qlik", "sql"], "C1", True, "hybrid", 75000, 90000, "Dresden")),

    ("""Junior Data Engineer – GreenGrid Solar
Location: Freiburg, hybrid
Help build ETL pipelines in Python and SQL on Azure. Docker basics welcome.
English fluent, German B1 required for team meetings.
Salary 48k–53k €.""",
     label("Junior Data Engineer", "junior", ["azure", "docker", "etl", "python", "sql"], "B1", True, "hybrid", 48000, 53000, "Freiburg")),

    ("""Datenanalyst (m/w/d) im Vertrieb – Brauhaus Kessler
Standort: Bamberg
Vertriebsdaten mit Excel und Power BI auswerten, Absatzprognosen erstellen.
Abgeschlossene Ausbildung oder Studium. Deutsch Muttersprache.
Wir arbeiten vor Ort. Gehalt: 45.000 €.""",
     label("Datenanalyst", "unspecified", ["excel", "power bi"], "native", None, "onsite", 45000, 45000, "Bamberg")),

    ("""Machine Learning Engineer – Lumen Robotics
Location: Munich, hybrid (1 day per week in the office)
Deploy ML models with Docker and Kubernetes on GCP, Python, MLOps practices.
Senior level, 5+ years. English only team, German not required.
Salary: 90,000–110,000 EUR.""",
     label("Machine Learning Engineer", "senior", ["docker", "gcp", "kubernetes", "machine learning", "python"], "none", True, "hybrid", 90000, 110000, "Munich")),

    ("""Supply Chain Data Analyst (m/w/d) – Weserport Logistik
Standort: Bremen
Analyse von Transport- und Lagerdaten mit SQL und Python, Dashboards in Tableau.
2 Jahre Berufserfahrung. Deutsch B2, Englisch verhandlungssicher.
Hybrid möglich. 54.000–60.000 € p.a.""",
     label("Supply Chain Data Analyst", "mid", ["python", "sql", "tableau"], "B2", True, "hybrid", 54000, 60000, "Bremen")),

    ("""Customer Insights Analyst – Kaffeewerk Online Shop
Location: Hamburg, fully remote
Analyse customer behaviour, segmentation in Python, SQL queries, reports in Google Analytics and Excel.
Mid level. English fluent. German C1 because you present to German stakeholders.
Salary not stated.""",
     label("Customer Insights Analyst", "mid", ["excel", "google analytics", "python", "sql"], "C1", True, "remote", None, None, "Hamburg")),

    ("""IT-Systemanalyst Data Warehouse (m/w/d) – Landesbank Nord
Ort: Hannover
Betreuung des Data Warehouse, SQL-Entwicklung, SAS-Programme pflegen.
Erfahrung im Bankenumfeld. Deutsch C2, Englisch B2.
Vor Ort, 2 Tage mobiles Arbeiten pro Woche möglich. Gehalt 58.000 – 68.000 €.""",
     label("IT-Systemanalyst Data Warehouse", "unspecified", ["sas", "sql"], "C2", True, "hybrid", 58000, 68000, "Hannover")),

    ("""Data Analyst Intern – Spree Mobility
Location: Berlin, on-site
6-month internship. Support the analytics team with SQL queries and Python notebooks.
English required. German not required.
Paid internship: 1,600 EUR per month.""",
     label("Data Analyst Intern", "intern", ["python", "sql"], "none", True, "onsite", 19200, 19200, "Berlin")),

    ("""Teamleitung Reporting & Analytics (m/w/d) – Gesundheitskasse Mitte
Standort: Kassel
Fachliche und disziplinarische Führung von 5 Mitarbeitenden, Weiterentwicklung der Power BI Landschaft.
Erfahrung mit SQL und Datenmodellierung. Deutsch verhandlungssicher.
Hybrides Arbeiten. Vergütung nach Tarif (E13).""",
     label("Teamleitung Reporting & Analytics", "lead", ["power bi", "sql"], "C1", None, "hybrid", None, None, "Kassel")),

    ("""Pricing Analyst – Bergsee Travel
Location: Munich, hybrid
Build pricing models in Python and Excel, analyse booking data with SQL.
2+ years. English fluent, German B2.
Salary 58,000 – 64,000 EUR.""",
     label("Pricing Analyst", "mid", ["excel", "python", "sql"], "B2", True, "hybrid", 58000, 64000, "Munich")),

    ("""Junior Data Analyst (m/w/d) Energiewirtschaft – Netzwerk Ost
Standort: Leipzig
Analyse von Netz- und Marktdaten mit Python und SQL, Visualisierung in Power BI.
Studium abgeschlossen, Interesse an Energiemärkten. Deutsch B2, Englisch gut.
Hybrid (3 Tage Büro). 47.000 – 51.000 €.""",
     label("Junior Data Analyst", "junior", ["power bi", "python", "sql"], "B2", True, "hybrid", 47000, 51000, "Leipzig")),

    ("""Data Steward (m/w/d) – Chemiepark Rhein
Ort: Ludwigshafen
Pflege von Stammdaten in SAP, Datenqualitätsregeln, Abstimmung mit Fachbereichen.
Kenntnisse in Excel und SQL wünschenswert. Deutsch fließend, Englisch gut.
Vor Ort. 50.000 €–56.000 € jährlich.""",
     label("Data Steward", "unspecified", ["excel", "sap", "sql"], "C1", True, "onsite", 50000, 56000, "Ludwigshafen")),

    ("""Business Analyst Data & AI – Consulting North
Location: Hamburg, hybrid
Translate business needs into data requirements, work with Python, SQL and Power BI teams, Scrum.
Junior position for graduates. English fluent; German C1 required for client work.
Salary: 50k EUR.""",
     label("Business Analyst Data & AI", "junior", ["power bi", "python", "scrum", "sql"], "C1", True, "hybrid", 50000, 50000, "Hamburg")),

    ("""Statistiker / Data Analyst (m/w/d) – Marktforschung Delta
Standort: Nürnberg
Auswertung von Umfragedaten mit R und SPSS, Statistik, Erstellung von Präsentationen.
Deutsch Muttersprache, Englisch sehr gut.
Remote-first Unternehmen. 52.000 – 58.000 €.""",
     label("Statistiker / Data Analyst", "unspecified", ["r", "spss", "statistics"], "native", True, "remote", 52000, 58000, "Nürnberg")),

    ("""Cloud Data Engineer – Harbor Analytics
Location: Bremen, remote within EU
Build streaming and batch pipelines with Spark on AWS, Terraform, Python, SQL. Mid-level, 3+ years.
English required, German not required.
Salary: 70,000 EUR - 80,000 EUR.""",
     label("Cloud Data Engineer", "mid", ["aws", "python", "spark", "sql", "terraform"], "none", True, "remote", 70000, 80000, "Bremen")),
]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, lab) in enumerate(ADS, 1):
            f.write(json.dumps({"id": f"ad{i:02d}", "text": text, "label": lab}, ensure_ascii=False) + "\n")
    print(f"Wrote {len(ADS)} labelled ads to {OUT}")


if __name__ == "__main__":
    main()
