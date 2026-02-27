# Brief for Code Generating Agent: National Multidimensional Poverty Index (MPI) 2023 Analysis

## 1. Overview of the Report
The **National Multidimensional Poverty Index (MPI): A Progress Review 2023** is a report by NITI Aayog, Government of India. It evaluates the progress in reducing multidimensional poverty in India between **NFHS-4 (2015-16)** and **NFHS-5 (2019-21)**.

### Purpose for Coder Agent:
This document defines the methodology for calculating poverty indices (Headcount Ratio, Intensity, and MPI Value) and provides the mapping of 12 key indicators across 3 dimensions.

## 2. Methodology & Content Page Format

### Dimensions and Indicators (Weights):
The MPI is calculated based on three equally weighted dimensions (1/3 each), further subdivided into 12 indicators:

1. **Health (1/3)**
   - Nutrition (1/6)
   - Child & Adolescent Mortality (1/12)
   - Maternal Health (1/12)

2. **Education (1/3)**
   - Years of Schooling (1/6)
   - School Attendance (1/6)

3. **Standard of Living (1/3)**
   - Cooking Fuel (1/21)
   - Sanitation (1/21)
   - Drinking Water (1/21)
   - Housing (1/21)
   - Electricity (1/21)
   - Assets (1/21)
   - Bank Account (1/21)

### Key Indices to Generate/Analyze:
- **Headcount Ratio (H):** Proportion of multidimensionally poor in the population (How many are poor?).
- **Intensity of Poverty (A):** Average proportion of deprivations experienced by the poor (How poor are they?).
- **MPI Value:** Calculated as $H 	imes A$.

## 3. Data Context for Coding
- **Source Data:** National Family Health Survey (NFHS-5 microdata).
- **Resolution:** Provides data at the **National**, **State**, and **District** levels.
- **Target:** Aiming to achieve SDG Target 1.2 (reducing poverty in all forms by at least half) by 2030.

## 4. Suggested Data Schema / Logic
When processing the associated datasets (like the NFHS-5 ssrn datasheet), the agent should look for columns corresponding to these 12 indicators to replicate or verify the MPI scores provided in the report.
- **Join Key:** `District Name` or `State Name` (ensure alignment with Census 2011 codes).
- **Transformation:** Indicators are often binary (deprived/not deprived) based on specific thresholds defined in the report's methodology section.
