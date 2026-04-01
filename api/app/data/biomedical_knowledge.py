"""Curated biomedical knowledge for Neo4j knowledge graph seeding.

Contains disease-pathway-intervention mappings for all conditions found in
Tesla Med Bed frequency scan reports. Every ICD-10 code in the normalizer's
MOCK_ICD10_MAP has a corresponding entry here.

Data is organized to ensure diseases that share biological pathways are
explicitly linked, enabling the graph_client's find_shared_pathways() and
find_systemic_patterns() queries to return meaningful results.

Sources consulted for curation:
- KEGG Disease/Pathway databases (https://rest.kegg.jp)
- Human Phenotype Ontology (https://hpo.jax.org)
- PubMed clinical literature
- ICD-10-CM classification guidelines
"""

from typing import TypedDict


class DiseaseRecord(TypedDict):
    name: str
    pathways: list[str]
    nutritional_factors: list[str]
    lifestyle_interventions: list[str]
    anatomical_structures: list[str]
    genes: list[str]
    phenotypes: list[str]
    comorbid_with: list[str]  # other ICD-10 codes


# ---------------------------------------------------------------------------
# Biological Pathways (~40)
# ---------------------------------------------------------------------------
PATHWAYS: dict[str, dict] = {
    # Immune / Inflammatory
    "Inflammatory response": {"kegg_id": "hsa04668", "category": "immune"},
    "NF-kB signaling": {"kegg_id": "hsa04064", "category": "immune"},
    "TNF signaling": {"kegg_id": "hsa04668", "category": "immune"},
    "IL-17 signaling": {"kegg_id": "hsa04657", "category": "immune"},
    "Th1/Th2 differentiation": {"kegg_id": "hsa04658", "category": "immune"},
    "Complement and coagulation": {"kegg_id": "hsa04610", "category": "immune"},
    "Autoimmune regulation": {"kegg_id": "hsa04940", "category": "immune"},
    # Metabolic
    "Lipid metabolism": {"kegg_id": "hsa00071", "category": "metabolic"},
    "Bile acid biosynthesis": {"kegg_id": "hsa00120", "category": "metabolic"},
    "Cholesterol metabolism": {"kegg_id": "hsa04979", "category": "metabolic"},
    "Iron metabolism": {"kegg_id": "hsa04978", "category": "metabolic"},
    "Porphyrin metabolism": {"kegg_id": "hsa00860", "category": "metabolic"},
    "Copper metabolism": {"kegg_id": "hsa04978", "category": "metabolic"},
    "Glucose metabolism": {"kegg_id": "hsa04930", "category": "metabolic"},
    "Insulin signaling": {"kegg_id": "hsa04910", "category": "metabolic"},
    "Thyroid hormone signaling": {"kegg_id": "hsa04919", "category": "metabolic"},
    "Calcium signaling": {"kegg_id": "hsa04020", "category": "metabolic"},
    "Bone metabolism": {"kegg_id": "hsa04928", "category": "metabolic"},
    # Digestive
    "Gastric acid secretion": {"kegg_id": "hsa04971", "category": "digestive"},
    "Gut microbiome regulation": {"kegg_id": "hsa05321", "category": "digestive"},
    "Mucosal barrier integrity": {"kegg_id": "hsa04530", "category": "digestive"},
    "Hepatic fibrosis": {"kegg_id": "hsa04932", "category": "digestive"},
    "Pancreatic secretion": {"kegg_id": "hsa04972", "category": "digestive"},
    # Cardiovascular
    "Atherosclerosis signaling": {"kegg_id": "hsa05417", "category": "cardiovascular"},
    "Renin-angiotensin system": {"kegg_id": "hsa04614", "category": "cardiovascular"},
    "Cardiac conduction": {"kegg_id": "hsa04261", "category": "cardiovascular"},
    "Vascular smooth muscle contraction": {"kegg_id": "hsa04270", "category": "cardiovascular"},
    "Coagulation cascade": {"kegg_id": "hsa04610", "category": "cardiovascular"},
    # Respiratory
    "Airway inflammation": {"kegg_id": "hsa05310", "category": "respiratory"},
    "Mucus hypersecretion": {"kegg_id": "hsa04750", "category": "respiratory"},
    # Cellular / Oncology
    "Oxidative stress response": {"kegg_id": "hsa04066", "category": "cellular"},
    "Apoptosis": {"kegg_id": "hsa04210", "category": "cellular"},
    "Cell cycle regulation": {"kegg_id": "hsa04110", "category": "cellular"},
    "p53 signaling": {"kegg_id": "hsa04115", "category": "cellular"},
    "HIF-1 signaling": {"kegg_id": "hsa04066", "category": "cellular"},
    "MAPK signaling": {"kegg_id": "hsa04010", "category": "cellular"},
    "PI3K-Akt signaling": {"kegg_id": "hsa04151", "category": "cellular"},
    "Wnt signaling": {"kegg_id": "hsa04310", "category": "cellular"},
    # Neurological
    "Autonomic nervous system regulation": {"kegg_id": "hsa04725", "category": "neurological"},
    "Serotonin signaling": {"kegg_id": "hsa04726", "category": "neurological"},
    "Erythropoiesis": {"kegg_id": "hsa04640", "category": "hematopoietic"},
    # Musculoskeletal
    "Extracellular matrix remodeling": {"kegg_id": "hsa04512", "category": "musculoskeletal"},
    "Cartilage degradation": {"kegg_id": "hsa04512", "category": "musculoskeletal"},
}


# ---------------------------------------------------------------------------
# Nutritional Factors (~30)
# ---------------------------------------------------------------------------
NUTRITIONAL_FACTORS: dict[str, dict] = {
    "Vitamin D": {"type": "vitamin", "evidence_level": "strong"},
    "Vitamin B12": {"type": "vitamin", "evidence_level": "strong"},
    "Folate (B9)": {"type": "vitamin", "evidence_level": "strong"},
    "Vitamin C": {"type": "vitamin", "evidence_level": "strong"},
    "Vitamin A": {"type": "vitamin", "evidence_level": "moderate"},
    "Vitamin E": {"type": "vitamin", "evidence_level": "moderate"},
    "Vitamin K2": {"type": "vitamin", "evidence_level": "moderate"},
    "Iron": {"type": "mineral", "evidence_level": "strong"},
    "Zinc": {"type": "mineral", "evidence_level": "strong"},
    "Magnesium": {"type": "mineral", "evidence_level": "strong"},
    "Calcium": {"type": "mineral", "evidence_level": "strong"},
    "Selenium": {"type": "mineral", "evidence_level": "moderate"},
    "Omega-3 fatty acids": {"type": "fatty_acid", "evidence_level": "strong"},
    "Probiotics": {"type": "supplement", "evidence_level": "moderate"},
    "Prebiotics (fiber)": {"type": "supplement", "evidence_level": "moderate"},
    "Curcumin": {"type": "phytonutrient", "evidence_level": "emerging"},
    "Quercetin": {"type": "phytonutrient", "evidence_level": "emerging"},
    "Coenzyme Q10": {"type": "supplement", "evidence_level": "moderate"},
    "L-Glutamine": {"type": "amino_acid", "evidence_level": "moderate"},
    "N-Acetyl Cysteine": {"type": "amino_acid", "evidence_level": "moderate"},
    "Alpha-lipoic acid": {"type": "supplement", "evidence_level": "moderate"},
    "Milk thistle (silymarin)": {"type": "herbal", "evidence_level": "moderate"},
    "Berberine": {"type": "phytonutrient", "evidence_level": "emerging"},
    "Glucosamine": {"type": "supplement", "evidence_level": "moderate"},
    "Chondroitin": {"type": "supplement", "evidence_level": "moderate"},
    "Bromelain": {"type": "enzyme", "evidence_level": "emerging"},
    "Boswellia": {"type": "herbal", "evidence_level": "emerging"},
    "Saw palmetto": {"type": "herbal", "evidence_level": "moderate"},
    "Iodine": {"type": "mineral", "evidence_level": "strong"},
    "Chromium": {"type": "mineral", "evidence_level": "moderate"},
}


# ---------------------------------------------------------------------------
# Lifestyle Interventions (~25)
# ---------------------------------------------------------------------------
LIFESTYLE_INTERVENTIONS: dict[str, dict] = {
    "Aerobic exercise (30 min/day)": {"category": "exercise", "evidence_level": "strong"},
    "Resistance training": {"category": "exercise", "evidence_level": "strong"},
    "Yoga and stretching": {"category": "exercise", "evidence_level": "moderate"},
    "Walking (10,000 steps/day)": {"category": "exercise", "evidence_level": "strong"},
    "Mediterranean diet": {"category": "diet", "evidence_level": "strong"},
    "Anti-inflammatory diet": {"category": "diet", "evidence_level": "moderate"},
    "Low-FODMAP diet": {"category": "diet", "evidence_level": "moderate"},
    "Gluten-free diet": {"category": "diet", "evidence_level": "strong"},
    "DASH diet": {"category": "diet", "evidence_level": "strong"},
    "Low-sodium diet": {"category": "diet", "evidence_level": "strong"},
    "Iron-rich diet": {"category": "diet", "evidence_level": "strong"},
    "Stress reduction (mindfulness)": {"category": "stress_management", "evidence_level": "strong"},
    "Cognitive behavioral therapy": {"category": "stress_management", "evidence_level": "strong"},
    "Sleep hygiene (7-9 hours)": {"category": "sleep", "evidence_level": "strong"},
    "Smoking cessation": {"category": "behavior", "evidence_level": "strong"},
    "Alcohol reduction": {"category": "behavior", "evidence_level": "strong"},
    "Weight management": {"category": "behavior", "evidence_level": "strong"},
    "Posture correction": {"category": "physical_therapy", "evidence_level": "moderate"},
    "Breathing exercises": {"category": "respiratory_therapy", "evidence_level": "moderate"},
    "Pelvic floor exercises": {"category": "physical_therapy", "evidence_level": "moderate"},
    "Elevation therapy (legs)": {"category": "physical_therapy", "evidence_level": "moderate"},
    "Compression therapy": {"category": "physical_therapy", "evidence_level": "strong"},
    "Hydrotherapy": {"category": "physical_therapy", "evidence_level": "emerging"},
    "Allergen avoidance": {"category": "environmental", "evidence_level": "strong"},
    "Humidified air therapy": {"category": "environmental", "evidence_level": "moderate"},
}


# ---------------------------------------------------------------------------
# Diseases — keyed by ICD-10 code
# Every code from normalizer.py MOCK_ICD10_MAP is included.
# ---------------------------------------------------------------------------
DISEASES: dict[str, DiseaseRecord] = {
    # ========================
    # GASTROINTESTINAL CLUSTER
    # ========================
    "K29.40": {
        "name": "Atrophic Gastritis",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Autoimmune regulation",
            "Mucosal barrier integrity",
        ],
        "nutritional_factors": [
            "Vitamin B12",
            "Iron",
            "Folate (B9)",
            "Zinc",
            "Probiotics",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Stomach mucosa", "Gastric glands"],
        "genes": ["HFE", "PTPN22", "IL1B"],
        "phenotypes": ["Epigastric pain", "B12 deficiency", "Iron deficiency anemia"],
        "comorbid_with": ["D64.9", "K21.0", "E03.9"],
    },
    "K29.00": {
        "name": "Catarrhal Gastritis",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Mucosal barrier integrity",
        ],
        "nutritional_factors": ["L-Glutamine", "Probiotics", "Zinc", "Vitamin A"],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Stomach mucosa"],
        "genes": ["IL1B", "TNF"],
        "phenotypes": ["Epigastric pain", "Nausea", "Dyspepsia"],
        "comorbid_with": ["K29.40", "K21.0"],
    },
    "K29.60": {
        "name": "Hypertrophic Gastritis",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Mucosal barrier integrity",
            "MAPK signaling",
        ],
        "nutritional_factors": ["Zinc", "Probiotics", "L-Glutamine", "Vitamin A"],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Stomach mucosa", "Gastric glands"],
        "genes": ["MEN1", "IL1B"],
        "phenotypes": ["Epigastric pain", "Protein-losing gastropathy", "Nausea"],
        "comorbid_with": ["K29.40", "K29.70"],
    },
    "K29.70": {
        "name": "Gastritis (unspecified)",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Mucosal barrier integrity",
        ],
        "nutritional_factors": [
            "Probiotics",
            "L-Glutamine",
            "Zinc",
            "Vitamin C",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Stomach mucosa"],
        "genes": ["IL1B", "TNF", "COX2"],
        "phenotypes": ["Epigastric pain", "Dyspepsia", "Bloating"],
        "comorbid_with": ["K21.0", "K29.80"],
    },
    "K29.80": {
        "name": "Duodenitis",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Mucosal barrier integrity",
            "Gut microbiome regulation",
        ],
        "nutritional_factors": ["L-Glutamine", "Probiotics", "Zinc", "Vitamin A"],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Duodenum", "Duodenal mucosa"],
        "genes": ["IL1B", "TNF"],
        "phenotypes": ["Upper abdominal pain", "Nausea", "Bloating"],
        "comorbid_with": ["K29.70", "K26.9"],
    },
    "K21.0": {
        "name": "Chronic Reflux-Gastritis (GERD)",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Mucosal barrier integrity",
        ],
        "nutritional_factors": [
            "Probiotics",
            "L-Glutamine",
            "Magnesium",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Weight management",
            "Anti-inflammatory diet",
            "Sleep hygiene (7-9 hours)",
            "Alcohol reduction",
        ],
        "anatomical_structures": [
            "Esophageal-gastric junction",
            "Esophagus",
            "Stomach",
        ],
        "genes": ["ASIC1", "IL1B"],
        "phenotypes": ["Heartburn", "Regurgitation", "Dysphagia"],
        "comorbid_with": ["K29.40", "K29.70", "J45.9"],
    },
    "K31.89": {
        "name": "Gastroptosis",
        "pathways": [
            "Gastric acid secretion",
            "Autonomic nervous system regulation",
        ],
        "nutritional_factors": ["Zinc", "Probiotics", "Vitamin C"],
        "lifestyle_interventions": [
            "Resistance training",
            "Walking (10,000 steps/day)",
            "Anti-inflammatory diet",
        ],
        "anatomical_structures": ["Stomach"],
        "genes": ["COL3A1"],
        "phenotypes": ["Epigastric heaviness", "Early satiety", "Bloating"],
        "comorbid_with": ["K29.70"],
    },
    "K52.9": {
        "name": "Colitis / Enteritis",
        "pathways": [
            "Inflammatory response",
            "Gut microbiome regulation",
            "Mucosal barrier integrity",
            "NF-kB signaling",
            "Autoimmune regulation",
        ],
        "nutritional_factors": [
            "Probiotics",
            "Prebiotics (fiber)",
            "L-Glutamine",
            "Omega-3 fatty acids",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Low-FODMAP diet",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Colon", "Small intestine"],
        "genes": ["NOD2", "IL23R", "ATG16L1"],
        "phenotypes": ["Diarrhea", "Abdominal pain", "Rectal bleeding"],
        "comorbid_with": ["K64.9", "K63.8", "K90.0"],
    },
    "K26.9": {
        "name": "Duodenal Ulcer",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Mucosal barrier integrity",
        ],
        "nutritional_factors": [
            "Zinc",
            "L-Glutamine",
            "Vitamin A",
            "Probiotics",
            "Vitamin C",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
            "Smoking cessation",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Duodenum"],
        "genes": ["IL1B", "TNF", "COX2"],
        "phenotypes": ["Epigastric pain", "Nocturnal pain", "GI bleeding"],
        "comorbid_with": ["K29.80", "K29.70"],
    },
    "K25.7": {
        "name": "Chronic Gastric Ulcer",
        "pathways": [
            "Gastric acid secretion",
            "Inflammatory response",
            "Mucosal barrier integrity",
        ],
        "nutritional_factors": [
            "Zinc",
            "L-Glutamine",
            "Vitamin A",
            "Probiotics",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Smoking cessation",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Stomach mucosa"],
        "genes": ["IL1B", "TNF"],
        "phenotypes": ["Epigastric pain", "Weight loss", "GI bleeding"],
        "comorbid_with": ["K29.70", "K26.9"],
    },
    "K90.0": {
        "name": "Gluten Enteropathy (Celiac Disease)",
        "pathways": [
            "Autoimmune regulation",
            "Inflammatory response",
            "Mucosal barrier integrity",
            "Gut microbiome regulation",
        ],
        "nutritional_factors": [
            "Iron",
            "Vitamin D",
            "Calcium",
            "Folate (B9)",
            "Zinc",
            "Vitamin B12",
        ],
        "lifestyle_interventions": [
            "Gluten-free diet",
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Small intestine", "Duodenal mucosa"],
        "genes": ["HLA-DQ2", "HLA-DQ8", "TG2"],
        "phenotypes": [
            "Malabsorption",
            "Diarrhea",
            "Iron deficiency anemia",
            "Osteoporosis",
        ],
        "comorbid_with": ["D64.9", "M81.0", "E03.9", "K52.9"],
    },
    "K63.8": {
        "name": "Intestinal Dysbiosis",
        "pathways": [
            "Gut microbiome regulation",
            "Inflammatory response",
            "Mucosal barrier integrity",
        ],
        "nutritional_factors": [
            "Probiotics",
            "Prebiotics (fiber)",
            "L-Glutamine",
            "Zinc",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Low-FODMAP diet",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Large intestine", "Small intestine"],
        "genes": ["NOD2", "FUT2"],
        "phenotypes": ["Bloating", "Irregular bowel movements", "Flatulence"],
        "comorbid_with": ["K52.9", "K29.70"],
    },
    "K64.9": {
        "name": "Haemorrhoids",
        "pathways": [
            "Vascular smooth muscle contraction",
            "Inflammatory response",
            "Coagulation cascade",
        ],
        "nutritional_factors": [
            "Prebiotics (fiber)",
            "Vitamin C",
            "Quercetin",
            "Bromelain",
        ],
        "lifestyle_interventions": [
            "Walking (10,000 steps/day)",
            "Anti-inflammatory diet",
            "Weight management",
        ],
        "anatomical_structures": ["Rectum", "Anal canal"],
        "genes": ["MMP2", "COX2"],
        "phenotypes": ["Rectal bleeding", "Perianal pain", "Pruritus ani"],
        "comorbid_with": ["K52.9"],
    },
    "K66.0": {
        "name": "Commissural Disease (Peritoneal Adhesions)",
        "pathways": [
            "Inflammatory response",
            "Extracellular matrix remodeling",
            "NF-kB signaling",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Vitamin E",
            "N-Acetyl Cysteine",
            "Bromelain",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Yoga and stretching",
        ],
        "anatomical_structures": ["Peritoneum"],
        "genes": ["TGF-B1", "MMP9"],
        "phenotypes": ["Abdominal pain", "Bowel obstruction", "Bloating"],
        "comorbid_with": ["K52.9"],
    },
    # ========================
    # HEPATOBILIARY CLUSTER
    # ========================
    "K80.10": {
        "name": "Calculous Cholecystitis",
        "pathways": [
            "Bile acid biosynthesis",
            "Cholesterol metabolism",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Omega-3 fatty acids",
            "Milk thistle (silymarin)",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Weight management",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Gallbladder"],
        "genes": ["ABCG8", "ABCG5", "UGT1A1"],
        "phenotypes": [
            "Right upper quadrant pain",
            "Nausea",
            "Murphy sign positive",
        ],
        "comorbid_with": ["K80.20", "K82.8"],
    },
    "K80.20": {
        "name": "Cholelithiasis",
        "pathways": [
            "Bile acid biosynthesis",
            "Cholesterol metabolism",
            "Lipid metabolism",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Omega-3 fatty acids",
            "Prebiotics (fiber)",
            "Milk thistle (silymarin)",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Weight management",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Gallbladder", "Bile duct"],
        "genes": ["ABCG8", "ABCG5", "LITH1"],
        "phenotypes": ["Biliary colic", "Right upper quadrant pain", "Jaundice"],
        "comorbid_with": ["K80.10", "K82.8"],
    },
    "K82.8": {
        "name": "Dyskinesia of Gallbladder",
        "pathways": [
            "Bile acid biosynthesis",
            "Autonomic nervous system regulation",
            "Cholesterol metabolism",
        ],
        "nutritional_factors": [
            "Milk thistle (silymarin)",
            "Omega-3 fatty acids",
            "Magnesium",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Gallbladder"],
        "genes": ["CCK", "ABCG8"],
        "phenotypes": ["Right upper quadrant pain", "Dyspepsia", "Nausea"],
        "comorbid_with": ["K80.20", "K80.10"],
    },
    "K73.9": {
        "name": "Chronic Relapsing Hepatitis",
        "pathways": [
            "Hepatic fibrosis",
            "Inflammatory response",
            "NF-kB signaling",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Milk thistle (silymarin)",
            "N-Acetyl Cysteine",
            "Vitamin E",
            "Omega-3 fatty acids",
            "Selenium",
        ],
        "lifestyle_interventions": [
            "Alcohol reduction",
            "Mediterranean diet",
            "Weight management",
        ],
        "anatomical_structures": ["Liver", "Hepatocyte"],
        "genes": ["HFE", "PNPLA3", "TM6SF2"],
        "phenotypes": ["Elevated transaminases", "Fatigue", "Hepatomegaly"],
        "comorbid_with": ["K76.0", "K74.0"],
    },
    "K71.0": {
        "name": "Cholestatic Hepatosis",
        "pathways": [
            "Bile acid biosynthesis",
            "Hepatic fibrosis",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Milk thistle (silymarin)",
            "N-Acetyl Cysteine",
            "Vitamin E",
            "Selenium",
        ],
        "lifestyle_interventions": [
            "Alcohol reduction",
            "Mediterranean diet",
        ],
        "anatomical_structures": ["Liver", "Intrahepatic bile duct"],
        "genes": ["ABCB4", "ABCB11"],
        "phenotypes": ["Jaundice", "Pruritus", "Elevated alkaline phosphatase"],
        "comorbid_with": ["K74.3", "K73.9"],
    },
    "K76.0": {
        "name": "Fatty Hepatosis (NAFLD)",
        "pathways": [
            "Lipid metabolism",
            "Insulin signaling",
            "Hepatic fibrosis",
            "Oxidative stress response",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Vitamin E",
            "Milk thistle (silymarin)",
            "Berberine",
            "N-Acetyl Cysteine",
            "Alpha-lipoic acid",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Aerobic exercise (30 min/day)",
            "Weight management",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Liver", "Hepatocyte"],
        "genes": ["PNPLA3", "TM6SF2", "MBOAT7"],
        "phenotypes": ["Hepatomegaly", "Elevated transaminases", "Fatigue"],
        "comorbid_with": ["K73.9", "K74.0", "E10.9", "I70.9"],
    },
    "K74.0": {
        "name": "Periportal Hepatic Fibrosis",
        "pathways": [
            "Hepatic fibrosis",
            "Inflammatory response",
            "Extracellular matrix remodeling",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Milk thistle (silymarin)",
            "Vitamin E",
            "N-Acetyl Cysteine",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Alcohol reduction",
            "Mediterranean diet",
            "Weight management",
        ],
        "anatomical_structures": ["Liver", "Portal tract"],
        "genes": ["PNPLA3", "TGF-B1"],
        "phenotypes": ["Portal hypertension", "Splenomegaly", "Fatigue"],
        "comorbid_with": ["K73.9", "K76.0", "K74.3"],
    },
    "K74.3": {
        "name": "Primary Biliary Cirrhosis",
        "pathways": [
            "Autoimmune regulation",
            "Bile acid biosynthesis",
            "Hepatic fibrosis",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Calcium",
            "Vitamin K2",
            "Milk thistle (silymarin)",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Alcohol reduction",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Liver", "Intrahepatic bile duct"],
        "genes": ["HLA-DRB1", "IL12A", "IL12RB2"],
        "phenotypes": ["Pruritus", "Fatigue", "Jaundice", "Osteoporosis"],
        "comorbid_with": ["K71.0", "K74.0", "M81.0"],
    },
    "K86.1": {
        "name": "Chronic Relapsing Pancreatitis",
        "pathways": [
            "Pancreatic secretion",
            "Inflammatory response",
            "Oxidative stress response",
            "NF-kB signaling",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Vitamin D",
            "Selenium",
            "Vitamin C",
            "Alpha-lipoic acid",
        ],
        "lifestyle_interventions": [
            "Alcohol reduction",
            "Anti-inflammatory diet",
            "Smoking cessation",
        ],
        "anatomical_structures": ["Pancreas", "Pancreatic duct"],
        "genes": ["PRSS1", "SPINK1", "CFTR"],
        "phenotypes": [
            "Epigastric pain radiating to back",
            "Steatorrhea",
            "Weight loss",
        ],
        "comorbid_with": ["E10.9", "K76.0"],
    },
    # ========================
    # CARDIOVASCULAR CLUSTER
    # ========================
    "I70.9": {
        "name": "Atherosclerosis",
        "pathways": [
            "Atherosclerosis signaling",
            "Lipid metabolism",
            "Inflammatory response",
            "Oxidative stress response",
            "Cholesterol metabolism",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Coenzyme Q10",
            "Vitamin E",
            "Magnesium",
            "Alpha-lipoic acid",
            "Berberine",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Aerobic exercise (30 min/day)",
            "Smoking cessation",
            "Stress reduction (mindfulness)",
            "Weight management",
        ],
        "anatomical_structures": ["Arterial wall", "Coronary artery", "Aorta"],
        "genes": ["APOE", "LDLR", "PCSK9", "APOB"],
        "phenotypes": ["Arterial plaque", "Claudication", "Angina"],
        "comorbid_with": ["I10", "I49.9", "I42.9", "K76.0"],
    },
    "I49.9": {
        "name": "Cardiac Arrhythmia",
        "pathways": [
            "Cardiac conduction",
            "Calcium signaling",
            "Autonomic nervous system regulation",
        ],
        "nutritional_factors": [
            "Magnesium",
            "Coenzyme Q10",
            "Omega-3 fatty acids",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Aerobic exercise (30 min/day)",
            "Stress reduction (mindfulness)",
            "Sleep hygiene (7-9 hours)",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Heart", "Cardiac conduction system"],
        "genes": ["SCN5A", "KCNQ1", "KCNH2"],
        "phenotypes": ["Palpitations", "Dizziness", "Syncope"],
        "comorbid_with": ["I70.9", "I10", "I42.9"],
    },
    "I10": {
        "name": "Idiopathic Hypertension",
        "pathways": [
            "Renin-angiotensin system",
            "Vascular smooth muscle contraction",
            "Atherosclerosis signaling",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Magnesium",
            "Coenzyme Q10",
            "Omega-3 fatty acids",
            "Vitamin D",
            "Calcium",
        ],
        "lifestyle_interventions": [
            "DASH diet",
            "Low-sodium diet",
            "Aerobic exercise (30 min/day)",
            "Weight management",
            "Stress reduction (mindfulness)",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Arterial wall", "Heart", "Kidney"],
        "genes": ["ACE", "AGT", "ADD1", "CYP11B2"],
        "phenotypes": ["Elevated blood pressure", "Headache", "Target organ damage"],
        "comorbid_with": ["I70.9", "I49.9", "I42.9"],
    },
    "I42.9": {
        "name": "Myocardiodystrophy (Cardiomyopathy)",
        "pathways": [
            "Cardiac conduction",
            "Oxidative stress response",
            "Calcium signaling",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Coenzyme Q10",
            "Magnesium",
            "Vitamin D",
            "Omega-3 fatty acids",
            "Selenium",
        ],
        "lifestyle_interventions": [
            "Aerobic exercise (30 min/day)",
            "Mediterranean diet",
            "Stress reduction (mindfulness)",
            "Alcohol reduction",
        ],
        "anatomical_structures": ["Heart", "Myocardium"],
        "genes": ["MYH7", "MYBPC3", "TTN"],
        "phenotypes": ["Dyspnea", "Fatigue", "Heart failure"],
        "comorbid_with": ["I49.9", "I70.9", "I10"],
    },
    "I80.9": {
        "name": "Thrombophlebitis",
        "pathways": [
            "Coagulation cascade",
            "Inflammatory response",
            "Complement and coagulation",
            "Vascular smooth muscle contraction",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Vitamin E",
            "Bromelain",
            "Quercetin",
        ],
        "lifestyle_interventions": [
            "Walking (10,000 steps/day)",
            "Elevation therapy (legs)",
            "Compression therapy",
            "Smoking cessation",
        ],
        "anatomical_structures": ["Venous wall", "Deep veins of lower limb"],
        "genes": ["F5", "F2", "SERPINC1"],
        "phenotypes": ["Limb swelling", "Warmth and redness", "Pain"],
        "comorbid_with": ["I83.90", "I70.9"],
    },
    "I83.90": {
        "name": "Varicose Veins",
        "pathways": [
            "Vascular smooth muscle contraction",
            "Extracellular matrix remodeling",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Quercetin",
            "Bromelain",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Walking (10,000 steps/day)",
            "Elevation therapy (legs)",
            "Compression therapy",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Saphenous vein", "Lower limb veins"],
        "genes": ["MMP2", "MMP9", "COL3A1"],
        "phenotypes": ["Visible tortuous veins", "Leg heaviness", "Edema"],
        "comorbid_with": ["I80.9", "L97.909"],
    },
    "I95.9": {
        "name": "Hypotension",
        "pathways": [
            "Autonomic nervous system regulation",
            "Renin-angiotensin system",
        ],
        "nutritional_factors": [
            "Iron",
            "Vitamin B12",
            "Folate (B9)",
            "Magnesium",
        ],
        "lifestyle_interventions": [
            "Walking (10,000 steps/day)",
            "Sleep hygiene (7-9 hours)",
            "Low-sodium diet",
        ],
        "anatomical_structures": ["Heart", "Arterial wall"],
        "genes": ["NOS3", "ACE"],
        "phenotypes": ["Dizziness", "Syncope", "Fatigue"],
        "comorbid_with": ["G90.9", "D64.9"],
    },
    "I09.9": {
        "name": "Rheumatic Carditis",
        "pathways": [
            "Autoimmune regulation",
            "Inflammatory response",
            "Cardiac conduction",
            "Complement and coagulation",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Vitamin D",
            "Vitamin C",
            "Coenzyme Q10",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Aerobic exercise (30 min/day)",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Heart", "Heart valves", "Pericardium"],
        "genes": ["HLA-DRB1", "TNF", "IL1B"],
        "phenotypes": ["Heart murmur", "Joint pain", "Fever"],
        "comorbid_with": ["I49.9", "M13.0"],
    },
    # ========================
    # RESPIRATORY CLUSTER
    # ========================
    "J45.9": {
        "name": "Bronchial Asthma",
        "pathways": [
            "Airway inflammation",
            "Th1/Th2 differentiation",
            "IL-17 signaling",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Magnesium",
            "Omega-3 fatty acids",
            "Vitamin C",
            "Quercetin",
        ],
        "lifestyle_interventions": [
            "Breathing exercises",
            "Aerobic exercise (30 min/day)",
            "Allergen avoidance",
            "Anti-inflammatory diet",
        ],
        "anatomical_structures": ["Bronchus", "Bronchial smooth muscle"],
        "genes": ["ADAM33", "IL4", "IL13", "ORMDL3"],
        "phenotypes": ["Wheezing", "Dyspnea", "Cough"],
        "comorbid_with": ["J42", "J30.1", "K21.0"],
    },
    "J42": {
        "name": "Chronic Bronchitis",
        "pathways": [
            "Airway inflammation",
            "Mucus hypersecretion",
            "Inflammatory response",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Vitamin D",
            "N-Acetyl Cysteine",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Smoking cessation",
            "Breathing exercises",
            "Aerobic exercise (30 min/day)",
            "Humidified air therapy",
        ],
        "anatomical_structures": ["Bronchus", "Bronchial mucosa"],
        "genes": ["MUC5AC", "SERPINA1", "HHIP"],
        "phenotypes": ["Chronic productive cough", "Dyspnea", "Wheezing"],
        "comorbid_with": ["J45.9", "J47.9"],
    },
    "J47.9": {
        "name": "Bronchiectasis",
        "pathways": [
            "Airway inflammation",
            "Mucus hypersecretion",
            "NF-kB signaling",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "N-Acetyl Cysteine",
            "Vitamin C",
            "Zinc",
        ],
        "lifestyle_interventions": [
            "Breathing exercises",
            "Aerobic exercise (30 min/day)",
            "Humidified air therapy",
        ],
        "anatomical_structures": ["Bronchus"],
        "genes": ["CFTR", "DNAH5"],
        "phenotypes": ["Chronic productive cough", "Recurrent infections", "Hemoptysis"],
        "comorbid_with": ["J42", "J45.9"],
    },
    "J04.0": {
        "name": "Laryngitis",
        "pathways": [
            "Airway inflammation",
            "Inflammatory response",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Zinc",
            "Vitamin A",
            "Probiotics",
        ],
        "lifestyle_interventions": [
            "Humidified air therapy",
            "Smoking cessation",
            "Allergen avoidance",
        ],
        "anatomical_structures": ["Larynx", "Vocal cords"],
        "genes": ["IL6", "TNF"],
        "phenotypes": ["Hoarseness", "Sore throat", "Cough"],
        "comorbid_with": ["J02.9", "J35.0"],
    },
    "J02.9": {
        "name": "Pharyngitis",
        "pathways": [
            "Airway inflammation",
            "Inflammatory response",
            "NF-kB signaling",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Zinc",
            "Probiotics",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Humidified air therapy",
            "Smoking cessation",
            "Allergen avoidance",
        ],
        "anatomical_structures": ["Pharynx"],
        "genes": ["TLR2", "IL6"],
        "phenotypes": ["Sore throat", "Dysphagia", "Fever"],
        "comorbid_with": ["J04.0", "J35.0"],
    },
    "J35.0": {
        "name": "Chronic Tonsillitis",
        "pathways": [
            "Inflammatory response",
            "Airway inflammation",
            "Autoimmune regulation",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Zinc",
            "Probiotics",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Allergen avoidance",
            "Anti-inflammatory diet",
            "Sleep hygiene (7-9 hours)",
        ],
        "anatomical_structures": ["Palatine tonsil"],
        "genes": ["TLR2", "IL6", "TNF"],
        "phenotypes": [
            "Recurrent sore throat",
            "Tonsillar hypertrophy",
            "Halitosis",
        ],
        "comorbid_with": ["J02.9", "J04.0", "I09.9"],
    },
    "J34.2": {
        "name": "Deviated Nasal Septum",
        "pathways": ["Airway inflammation"],
        "nutritional_factors": ["Vitamin C", "Quercetin"],
        "lifestyle_interventions": [
            "Breathing exercises",
            "Humidified air therapy",
            "Allergen avoidance",
        ],
        "anatomical_structures": ["Nasal septum"],
        "genes": ["COL2A1"],
        "phenotypes": ["Nasal obstruction", "Epistaxis", "Snoring"],
        "comorbid_with": ["J30.1"],
    },
    "J30.1": {
        "name": "Allergic Rhinitis (Pollinosis)",
        "pathways": [
            "Th1/Th2 differentiation",
            "Inflammatory response",
            "Airway inflammation",
        ],
        "nutritional_factors": [
            "Vitamin C",
            "Quercetin",
            "Probiotics",
            "Vitamin D",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Allergen avoidance",
            "Anti-inflammatory diet",
            "Breathing exercises",
        ],
        "anatomical_structures": ["Nasal mucosa"],
        "genes": ["IL4", "IL13", "STAT6"],
        "phenotypes": ["Sneezing", "Rhinorrhea", "Nasal congestion"],
        "comorbid_with": ["J45.9", "J34.2"],
    },
    # ========================
    # MUSCULOSKELETAL CLUSTER
    # ========================
    "M19.90": {
        "name": "Osteoarthritis",
        "pathways": [
            "Inflammatory response",
            "Cartilage degradation",
            "Extracellular matrix remodeling",
            "Bone metabolism",
        ],
        "nutritional_factors": [
            "Glucosamine",
            "Chondroitin",
            "Omega-3 fatty acids",
            "Vitamin D",
            "Curcumin",
            "Boswellia",
        ],
        "lifestyle_interventions": [
            "Walking (10,000 steps/day)",
            "Resistance training",
            "Weight management",
            "Yoga and stretching",
        ],
        "anatomical_structures": ["Joint cartilage", "Synovial membrane"],
        "genes": ["GDF5", "COL2A1", "MMP13"],
        "phenotypes": ["Joint pain", "Stiffness", "Reduced range of motion"],
        "comorbid_with": ["M81.0", "M13.0"],
    },
    "M81.0": {
        "name": "Osteoporosis",
        "pathways": [
            "Bone metabolism",
            "Calcium signaling",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Calcium",
            "Vitamin D",
            "Vitamin K2",
            "Magnesium",
            "Zinc",
        ],
        "lifestyle_interventions": [
            "Resistance training",
            "Walking (10,000 steps/day)",
            "Yoga and stretching",
            "Smoking cessation",
        ],
        "anatomical_structures": ["Bone", "Vertebral body"],
        "genes": ["ESR1", "LRP5", "COL1A1", "VDR"],
        "phenotypes": ["Fracture risk", "Loss of height", "Kyphosis"],
        "comorbid_with": ["M19.90", "E03.9", "K90.0", "K74.3"],
    },
    "M13.0": {
        "name": "Polyarthritis",
        "pathways": [
            "Inflammatory response",
            "Autoimmune regulation",
            "TNF signaling",
            "NF-kB signaling",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Curcumin",
            "Vitamin D",
            "Boswellia",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Yoga and stretching",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Synovial joint", "Synovial membrane"],
        "genes": ["HLA-DRB1", "PTPN22", "TNF"],
        "phenotypes": ["Joint swelling", "Morning stiffness", "Symmetric joint pain"],
        "comorbid_with": ["M19.90", "I09.9"],
    },
    "M54.10": {
        "name": "Radiculopathy",
        "pathways": [
            "Inflammatory response",
            "Extracellular matrix remodeling",
            "NF-kB signaling",
        ],
        "nutritional_factors": [
            "Vitamin B12",
            "Omega-3 fatty acids",
            "Magnesium",
            "Curcumin",
        ],
        "lifestyle_interventions": [
            "Posture correction",
            "Yoga and stretching",
            "Resistance training",
            "Walking (10,000 steps/day)",
        ],
        "anatomical_structures": ["Spinal nerve root", "Intervertebral disc"],
        "genes": ["COL9A2", "MMP3"],
        "phenotypes": [
            "Radiating limb pain",
            "Numbness",
            "Muscle weakness",
        ],
        "comorbid_with": ["M47.819", "M48.27"],
    },
    "M75.00": {
        "name": "Scapulohumeral Periarthritis",
        "pathways": [
            "Inflammatory response",
            "Extracellular matrix remodeling",
        ],
        "nutritional_factors": [
            "Omega-3 fatty acids",
            "Curcumin",
            "Vitamin D",
            "Magnesium",
        ],
        "lifestyle_interventions": [
            "Yoga and stretching",
            "Posture correction",
            "Resistance training",
        ],
        "anatomical_structures": ["Shoulder joint", "Rotator cuff"],
        "genes": ["MMP3", "COL1A1"],
        "phenotypes": ["Shoulder pain", "Restricted mobility", "Night pain"],
        "comorbid_with": ["M19.90"],
    },
    "M47.819": {
        "name": "Spondylarthrosis Deformans",
        "pathways": [
            "Bone metabolism",
            "Cartilage degradation",
            "Inflammatory response",
            "Extracellular matrix remodeling",
        ],
        "nutritional_factors": [
            "Glucosamine",
            "Chondroitin",
            "Omega-3 fatty acids",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Posture correction",
            "Yoga and stretching",
            "Walking (10,000 steps/day)",
            "Resistance training",
        ],
        "anatomical_structures": ["Vertebral body", "Facet joint"],
        "genes": ["GDF5", "COL2A1"],
        "phenotypes": ["Back pain", "Stiffness", "Reduced spinal mobility"],
        "comorbid_with": ["M54.10", "M48.27", "M19.90"],
    },
    "M48.27": {
        "name": "Baastrup's Disease (Kissing Spine)",
        "pathways": [
            "Bone metabolism",
            "Inflammatory response",
            "Extracellular matrix remodeling",
        ],
        "nutritional_factors": [
            "Calcium",
            "Vitamin D",
            "Omega-3 fatty acids",
            "Curcumin",
        ],
        "lifestyle_interventions": [
            "Posture correction",
            "Yoga and stretching",
            "Resistance training",
        ],
        "anatomical_structures": ["Spinous process", "Interspinous ligament"],
        "genes": ["COL1A1"],
        "phenotypes": ["Lumbar pain on extension", "Midline tenderness"],
        "comorbid_with": ["M47.819", "M54.10"],
    },
    "M79.2": {
        "name": "Neuralgia",
        "pathways": [
            "Inflammatory response",
            "Serotonin signaling",
            "Autonomic nervous system regulation",
        ],
        "nutritional_factors": [
            "Vitamin B12",
            "Magnesium",
            "Alpha-lipoic acid",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Stress reduction (mindfulness)",
            "Yoga and stretching",
            "Sleep hygiene (7-9 hours)",
        ],
        "anatomical_structures": ["Peripheral nerve"],
        "genes": ["SCN9A", "TRPV1"],
        "phenotypes": ["Shooting pain", "Burning sensation", "Hyperesthesia"],
        "comorbid_with": ["M54.10", "G90.9"],
    },
    # ========================
    # ENDOCRINE / METABOLIC CLUSTER
    # ========================
    "E03.9": {
        "name": "Hypothyroidism",
        "pathways": [
            "Thyroid hormone signaling",
            "Autoimmune regulation",
            "Lipid metabolism",
        ],
        "nutritional_factors": [
            "Iodine",
            "Selenium",
            "Zinc",
            "Vitamin D",
            "Iron",
        ],
        "lifestyle_interventions": [
            "Aerobic exercise (30 min/day)",
            "Stress reduction (mindfulness)",
            "Gluten-free diet",
            "Sleep hygiene (7-9 hours)",
        ],
        "anatomical_structures": ["Thyroid gland"],
        "genes": ["TPO", "TG", "TSHR", "FOXE1"],
        "phenotypes": ["Fatigue", "Weight gain", "Cold intolerance", "Constipation"],
        "comorbid_with": ["K29.40", "M81.0", "D64.9"],
    },
    "E04.0": {
        "name": "Diffuse Goiter",
        "pathways": [
            "Thyroid hormone signaling",
            "Calcium signaling",
        ],
        "nutritional_factors": [
            "Iodine",
            "Selenium",
            "Zinc",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Aerobic exercise (30 min/day)",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Thyroid gland"],
        "genes": ["TG", "TSHR", "NKX2-1"],
        "phenotypes": ["Thyroid enlargement", "Neck swelling", "Dysphagia"],
        "comorbid_with": ["E03.9"],
    },
    "E10.9": {
        "name": "Insulin-dependent Diabetes Mellitus (Type 1)",
        "pathways": [
            "Insulin signaling",
            "Glucose metabolism",
            "Autoimmune regulation",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Chromium",
            "Magnesium",
            "Alpha-lipoic acid",
            "Vitamin D",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Aerobic exercise (30 min/day)",
            "Stress reduction (mindfulness)",
            "Sleep hygiene (7-9 hours)",
        ],
        "anatomical_structures": ["Pancreatic islets", "Beta cells"],
        "genes": ["HLA-DQB1", "INS", "PTPN22", "IL2RA"],
        "phenotypes": ["Hyperglycemia", "Polyuria", "Weight loss"],
        "comorbid_with": ["I70.9", "K76.0", "K86.1"],
    },
    "E83.01": {
        "name": "Hepatocerebral Dystrophy (Wilson's Disease)",
        "pathways": [
            "Copper metabolism",
            "Hepatic fibrosis",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Zinc",
            "Vitamin E",
            "N-Acetyl Cysteine",
            "Selenium",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Liver", "Basal ganglia", "Cornea"],
        "genes": ["ATP7B"],
        "phenotypes": [
            "Kayser-Fleischer rings",
            "Hepatic dysfunction",
            "Tremor",
        ],
        "comorbid_with": ["K73.9", "K74.0"],
    },
    "E80.20": {
        "name": "Porphyria",
        "pathways": [
            "Porphyrin metabolism",
            "Hepatic fibrosis",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Magnesium",
            "Iron",
            "Zinc",
        ],
        "lifestyle_interventions": [
            "Alcohol reduction",
            "Stress reduction (mindfulness)",
            "Sleep hygiene (7-9 hours)",
        ],
        "anatomical_structures": ["Liver", "Bone marrow"],
        "genes": ["HMBS", "PPOX", "UROD"],
        "phenotypes": [
            "Abdominal pain",
            "Photosensitivity",
            "Neuropsychiatric symptoms",
        ],
        "comorbid_with": ["K73.9"],
    },
    # ========================
    # ONCOLOGY CLUSTER
    # ========================
    "C34.9": {
        "name": "Bronchogenic Carcinoma",
        "pathways": [
            "Cell cycle regulation",
            "p53 signaling",
            "Apoptosis",
            "PI3K-Akt signaling",
            "MAPK signaling",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Selenium",
            "Omega-3 fatty acids",
            "Curcumin",
            "Vitamin C",
        ],
        "lifestyle_interventions": [
            "Smoking cessation",
            "Anti-inflammatory diet",
            "Aerobic exercise (30 min/day)",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Lung", "Bronchus"],
        "genes": ["EGFR", "KRAS", "TP53", "ALK"],
        "phenotypes": ["Cough", "Hemoptysis", "Weight loss"],
        "comorbid_with": ["J42", "J47.9"],
    },
    "C32.0": {
        "name": "Papillary Cancer of the Larynx",
        "pathways": [
            "Cell cycle regulation",
            "p53 signaling",
            "Apoptosis",
            "Wnt signaling",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Selenium",
            "Vitamin C",
            "Curcumin",
        ],
        "lifestyle_interventions": [
            "Smoking cessation",
            "Alcohol reduction",
            "Anti-inflammatory diet",
        ],
        "anatomical_structures": ["Larynx", "Vocal cords"],
        "genes": ["TP53", "CDKN2A", "PIK3CA"],
        "phenotypes": ["Hoarseness", "Dysphagia", "Stridor"],
        "comorbid_with": ["J04.0"],
    },
    "C25.9": {
        "name": "Pancreatic Carcinoma",
        "pathways": [
            "Cell cycle regulation",
            "p53 signaling",
            "Apoptosis",
            "MAPK signaling",
            "PI3K-Akt signaling",
            "Wnt signaling",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Selenium",
            "Omega-3 fatty acids",
            "Curcumin",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Smoking cessation",
            "Weight management",
        ],
        "anatomical_structures": ["Pancreas", "Pancreatic duct"],
        "genes": ["KRAS", "TP53", "SMAD4", "CDKN2A"],
        "phenotypes": ["Jaundice", "Weight loss", "Epigastric pain radiating to back"],
        "comorbid_with": ["K86.1", "E10.9"],
    },
    "D13.1": {
        "name": "Fibroma of the Stomach",
        "pathways": [
            "Cell cycle regulation",
            "Extracellular matrix remodeling",
            "MAPK signaling",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Selenium",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Mediterranean diet",
            "Anti-inflammatory diet",
        ],
        "anatomical_structures": ["Stomach", "Stomach wall"],
        "genes": ["PDGFRA", "KIT"],
        "phenotypes": ["Gastric mass", "GI bleeding", "Abdominal discomfort"],
        "comorbid_with": ["K29.70"],
    },
    # ========================
    # HEMATOLOGICAL
    # ========================
    "D64.9": {
        "name": "Anaemia",
        "pathways": [
            "Iron metabolism",
            "Erythropoiesis",
            "Oxidative stress response",
        ],
        "nutritional_factors": [
            "Iron",
            "Vitamin B12",
            "Folate (B9)",
            "Vitamin C",
            "Zinc",
        ],
        "lifestyle_interventions": [
            "Iron-rich diet",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Bone marrow", "Spleen"],
        "genes": ["HFE", "EPO", "TMPRSS6"],
        "phenotypes": [
            "Fatigue",
            "Pallor",
            "Dyspnea on exertion",
            "Tachycardia",
        ],
        "comorbid_with": ["K29.40", "K90.0", "E03.9"],
    },
    # ========================
    # INFECTIOUS / PARASITIC
    # ========================
    "B83.9": {
        "name": "Helminthiasis",
        "pathways": [
            "Th1/Th2 differentiation",
            "Inflammatory response",
            "Gut microbiome regulation",
        ],
        "nutritional_factors": [
            "Probiotics",
            "Zinc",
            "Vitamin A",
            "Iron",
        ],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Sleep hygiene (7-9 hours)",
        ],
        "anatomical_structures": ["Small intestine", "Large intestine"],
        "genes": ["IL4", "IL13", "STAT6"],
        "phenotypes": [
            "Abdominal pain",
            "Eosinophilia",
            "Iron deficiency anemia",
        ],
        "comorbid_with": ["D64.9", "K52.9"],
    },
    # ========================
    # NEUROLOGICAL / AUTONOMIC
    # ========================
    "G90.9": {
        "name": "Vegetative-Vascular Dystonia (Dysautonomia)",
        "pathways": [
            "Autonomic nervous system regulation",
            "Serotonin signaling",
            "Calcium signaling",
        ],
        "nutritional_factors": [
            "Magnesium",
            "Vitamin B12",
            "Omega-3 fatty acids",
            "Coenzyme Q10",
        ],
        "lifestyle_interventions": [
            "Aerobic exercise (30 min/day)",
            "Stress reduction (mindfulness)",
            "Sleep hygiene (7-9 hours)",
            "Yoga and stretching",
        ],
        "anatomical_structures": ["Autonomic ganglia", "Sympathetic chain"],
        "genes": ["NET", "DBH", "ADRB1"],
        "phenotypes": ["Tachycardia", "Dizziness", "Anxiety", "Temperature dysregulation"],
        "comorbid_with": ["I95.9", "F48.0", "I49.9"],
    },
    "F48.0": {
        "name": "Neurasthenia",
        "pathways": [
            "Serotonin signaling",
            "Autonomic nervous system regulation",
            "HIF-1 signaling",
        ],
        "nutritional_factors": [
            "Magnesium",
            "Vitamin B12",
            "Omega-3 fatty acids",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Cognitive behavioral therapy",
            "Aerobic exercise (30 min/day)",
            "Sleep hygiene (7-9 hours)",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Central nervous system"],
        "genes": ["SLC6A4", "BDNF", "COMT"],
        "phenotypes": ["Chronic fatigue", "Irritability", "Insomnia", "Headache"],
        "comorbid_with": ["G90.9"],
    },
    # ========================
    # UROGENITAL
    # ========================
    "N41.9": {
        "name": "Prostatitis",
        "pathways": [
            "Inflammatory response",
            "NF-kB signaling",
            "Autoimmune regulation",
        ],
        "nutritional_factors": [
            "Zinc",
            "Saw palmetto",
            "Quercetin",
            "Omega-3 fatty acids",
            "Vitamin D",
        ],
        "lifestyle_interventions": [
            "Pelvic floor exercises",
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
            "Aerobic exercise (30 min/day)",
        ],
        "anatomical_structures": ["Prostate gland"],
        "genes": ["SRD5A2", "CYP17A1"],
        "phenotypes": ["Pelvic pain", "Urinary frequency", "Dysuria"],
        "comorbid_with": ["N45.9"],
    },
    "N45.9": {
        "name": "Orchitis",
        "pathways": [
            "Inflammatory response",
            "Autoimmune regulation",
        ],
        "nutritional_factors": ["Zinc", "Vitamin C", "Omega-3 fatty acids", "Selenium"],
        "lifestyle_interventions": [
            "Anti-inflammatory diet",
            "Stress reduction (mindfulness)",
        ],
        "anatomical_structures": ["Testis"],
        "genes": ["TNF", "IL6"],
        "phenotypes": ["Scrotal pain", "Testicular swelling", "Fever"],
        "comorbid_with": ["N41.9"],
    },
    "N28.89": {
        "name": "Nephroptosis",
        "pathways": [
            "Renin-angiotensin system",
            "Autonomic nervous system regulation",
        ],
        "nutritional_factors": ["Vitamin D", "Magnesium"],
        "lifestyle_interventions": [
            "Resistance training",
            "Weight management",
        ],
        "anatomical_structures": ["Kidney"],
        "genes": ["COL3A1"],
        "phenotypes": ["Flank pain on standing", "Hematuria"],
        "comorbid_with": ["N13.30"],
    },
    "N13.30": {
        "name": "Renal Hydronephrosis",
        "pathways": [
            "Renin-angiotensin system",
            "Inflammatory response",
            "Extracellular matrix remodeling",
        ],
        "nutritional_factors": [
            "Vitamin D",
            "Omega-3 fatty acids",
            "Magnesium",
        ],
        "lifestyle_interventions": [
            "Walking (10,000 steps/day)",
            "Anti-inflammatory diet",
        ],
        "anatomical_structures": ["Kidney", "Renal pelvis", "Ureter"],
        "genes": ["RET", "GDNF"],
        "phenotypes": ["Flank pain", "Hydronephrosis on imaging", "UTI"],
        "comorbid_with": ["N28.89"],
    },
    # ========================
    # DERMATOLOGICAL / VASCULAR
    # ========================
    "L97.909": {
        "name": "Trophic Leg Ulcers",
        "pathways": [
            "Vascular smooth muscle contraction",
            "Inflammatory response",
            "Extracellular matrix remodeling",
            "Coagulation cascade",
        ],
        "nutritional_factors": [
            "Zinc",
            "Vitamin C",
            "Vitamin A",
            "Omega-3 fatty acids",
        ],
        "lifestyle_interventions": [
            "Compression therapy",
            "Elevation therapy (legs)",
            "Walking (10,000 steps/day)",
            "Smoking cessation",
        ],
        "anatomical_structures": ["Skin of lower leg", "Venous vasculature"],
        "genes": ["MMP9", "VEGF", "FGF2"],
        "phenotypes": ["Non-healing ulcer", "Leg edema", "Skin discoloration"],
        "comorbid_with": ["I83.90", "I80.9"],
    },
    # ========================
    # OPHTHALMOLOGICAL
    # ========================
    "H52.0": {
        "name": "Farsightedness (Hypermetropia)",
        "pathways": ["Calcium signaling"],
        "nutritional_factors": ["Vitamin A", "Zinc", "Omega-3 fatty acids"],
        "lifestyle_interventions": [
            "Aerobic exercise (30 min/day)",
            "Sleep hygiene (7-9 hours)",
        ],
        "anatomical_structures": ["Eye", "Lens"],
        "genes": ["PAX6"],
        "phenotypes": ["Blurred near vision", "Eye strain", "Headache"],
        "comorbid_with": [],
    },
    # ========================
    # MUSCLE / MISCELLANEOUS
    # ========================
    "R25.2": {
        "name": "Calf Muscle Spasm",
        "pathways": [
            "Calcium signaling",
            "Autonomic nervous system regulation",
        ],
        "nutritional_factors": [
            "Magnesium",
            "Calcium",
            "Vitamin D",
            "Vitamin E",
        ],
        "lifestyle_interventions": [
            "Yoga and stretching",
            "Walking (10,000 steps/day)",
            "Hydrotherapy",
        ],
        "anatomical_structures": ["Gastrocnemius muscle", "Soleus muscle"],
        "genes": ["CACNA1S", "RYR1"],
        "phenotypes": ["Nocturnal leg cramps", "Muscle pain", "Muscle tightness"],
        "comorbid_with": ["I83.90", "M79.2"],
    },
}
