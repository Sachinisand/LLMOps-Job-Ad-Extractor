"""
Writes eval/holdout_ads.jsonl: 12 extra labelled job ads that were written AFTER
the baseline rules were finished, using different wording on purpose.

Why: the baseline rules were developed while looking at eval/job_ads.jsonl, so
their score there is optimistic. This held-out set shows how each approach copes
with phrasing it has never seen, which is the real test for a production model.
Never tune prompts or rules on this file.

Run:  python scripts/make_holdout_set.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "eval" / "holdout_ads.jsonl"


def label(title, seniority, skills, german, english, mode, smin, smax, location):
    return {"job_title": title, "seniority": seniority, "skills": sorted(skills), "german_level": german,
            "english_required": english, "work_mode": mode, "salary_min": smin, "salary_max": smax,
            "location": location}


ADS = [
    ("""Wir suchen dich als Data Analyst (all genders) für unser Team in Essen!
Was du mitbringst: Einstiegsposition – auch für Absolvent:innen. Microsoft Excel, MS SQL Server und Power-BI.
Deutschkenntnisse auf C1-Niveau, Englisch reicht auf Basisniveau.
Bis zu 3 Tage Home-Office pro Woche. Jahresgehalt ab 45.000 Euro.""",
     label("Data Analyst", "junior", ["excel", "power bi", "sql"], "C1", True, "hybrid", 45000, 45000, "Essen")),

    ("""Lead Data Engineer @ Wavelength Media (Cologne)
We need someone to own our lakehouse: PySpark, Delta Lake on Databricks, Terraform, CI/CD with GitHub Actions.
You'll manage 4 engineers. Our working language is English – German skills are welcome but optional.
Work from anywhere in Germany. Package: up to EUR 105,000.""",
     label("Lead Data Engineer", "lead", ["databricks", "delta lake", "github actions", "spark", "terraform"], "unspecified", True, "remote", None, 105000, "Köln")),

    ("""Datenanalyst:in Einkauf – Kühne & Partner Lebensmittel
Arbeitsort Osnabrück, Präsenzpflicht im Büro
Du wertest Lieferantendaten aus (Excel, Power Query) und pflegst Kennzahlen im ERP-System SAP.
Mehrjährige Erfahrung im Einkaufscontrolling. Deutsch auf muttersprachlichem Niveau.
Monatsgehalt: 4.200 € (12 Gehälter).""",
     label("Datenanalyst:in Einkauf", "mid", ["excel", "power query", "sap"], "native", None, "onsite", 50400, 50400, "Osnabrück")),

    ("""Junior Analytics Engineer – Fernweh Reisen
City: Mannheim | Mode: hybrid, Tuesdays and Thursdays in the office
SQL every day, dbt for models, Python for small scripts, Tableau for dashboards.
German B2+ needed for stakeholder meetings, solid English.
Pay: 4,000 EUR gross per month.""",
     label("Junior Analytics Engineer", "junior", ["dbt", "python", "sql", "tableau"], "B2", True, "hybrid", 48000, 48000, "Mannheim")),

    ("""Studentische Aushilfe Data & Reporting (m/w/d)
Wo? Göttingen, direkt bei uns am Campus.
Unterstütze uns bei Excel-Auswertungen und einfachen SQL-Abfragen. 10 Std./Woche, 14 €/Std.
Gute Deutschkenntnisse (mind. B2).""",
     label("Studentische Aushilfe Data & Reporting", "working_student", ["excel", "sql"], "B2", None, "onsite", None, None, "Göttingen")),

    ("""Senior Product Data Scientist – Quanta Insurance Tech
Based in Munich (hybrid, 2 office days)
Causal inference, experimentation (A/B testing), Python, SQL, Bayesian statistics. 6+ yrs experience.
English is a must; German is not required.
Salary band: €95k–€115k + bonus.""",
     label("Senior Product Data Scientist", "senior", ["a/b testing", "python", "sql", "statistics"], "none", True, "hybrid", 95000, 115000, "München")),

    ("""BI-Analyst (w/m/d) Gesundheitswesen
Region Rostock – ausschließlich mobiles Arbeiten
Aufbau von Dashboards in Qlik Sense, Datenaufbereitung mit SQL, erste Erfahrung mit Python wünschenswert.
Deutsch C2, Englischkenntnisse sind nicht erforderlich.
Vergütung: 55-60k €.""",
     label("BI-Analyst", "unspecified", ["python", "qlik", "sql"], "C2", False, "remote", 55000, 60000, "Rostock")),

    ("""Data Operations Specialist – Northbound Freight
Hamburg port office (on-site role)
Keep our shipment data clean: SQL queries, Excel macros (VBA), ticket handling in Jira.
2 years in a data role. English required, German A2 helpful but not required.
Salary: 47k to 52k per year (EUR).""",
     label("Data Operations Specialist", "mid", ["excel", "jira", "sql", "vba"], "none", True, "onsite", 47000, 52000, "Hamburg")),

    ("""Trainee Data & Analytics (m/w/d) – 18-monatiges Programm
Standorte: Bielefeld
Du lernst SQL, Python und Power BI in drei Fachabteilungen kennen.
Für Hochschulabsolvent:innen. Deutsch fließend, Englisch gut.
Hybrid. Traineegehalt 44.000 € p.a.""",
     label("Trainee Data & Analytics", "junior", ["power bi", "python", "sql"], "C1", True, "hybrid", 44000, 44000, "Bielefeld")),

    ("""Marketing Data Analyst (m/f/d) – Stadtrad Mobility
Office: Leipzig, flexible hybrid setup
GA4 / Google Analytics, Looker Studio, BigQuery SQL. Bonus if you know R.
Mid-level (3+ years). German C1 and English C1.
Salary: 58.000 – 63.000 EUR.""",
     label("Marketing Data Analyst", "mid", ["bigquery", "google analytics", "looker", "r", "sql"], "C1", True, "hybrid", 58000, 63000, "Leipzig")),

    ("""Internship: Data Science (6 months) – Fjord Analytics
Location: Berlin office
Python (pandas, scikit-learn), basic machine learning, Git.
English only – no German needed. Compensation: €1,700/month.""",
     label("Internship: Data Science", "intern", ["git", "machine learning", "pandas", "python", "scikit-learn"], "none", True, "onsite", 20400, 20400, "Berlin")),

    ("""Teamlead Data Platform (m/w/d) – Energieversorger Süd
Standort Karlsruhe, Hybrid-Modell
Führung von 6 Data Engineers, Azure Data Factory, Snowflake, dbt, Kubernetes.
Deutsch verhandlungssicher und Englisch fließend.
Zielgehalt 100.000 – 120.000 €.""",
     label("Teamlead Data Platform", "lead", ["azure", "azure data factory", "dbt", "kubernetes", "snowflake"], "C1", True, "hybrid", 100000, 120000, "Karlsruhe")),
]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, lab) in enumerate(ADS, 1):
            f.write(json.dumps({"id": f"holdout{i:02d}", "text": text, "label": lab}, ensure_ascii=False) + "\n")
    print(f"Wrote {len(ADS)} labelled ads to {OUT}")


if __name__ == "__main__":
    main()
