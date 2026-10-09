# Azure-Based Data Engineering Platform

A simple, end-to-end reference project using the **medallion architecture** on Azure.

```
 CSV file ──► ADLS Gen2 (landing) ──► Databricks ──► bronze ──► silver ──► gold ──► BI / Synapse / Power BI
                                          ▲
                        Azure Data Factory orchestrates the notebooks
```

| Layer   | What happens                                                     |
|---------|------------------------------------------------------------------|
| landing | Raw files as uploaded (`ingest_to_adls.py`)                      |
| bronze  | Delta table, data as-is + audit columns                          |
| silver  | Typed, validated, de-duplicated                                  |
| gold    | Business aggregates (daily sales, category/country, customers)   |

## Project structure

```
infra/main.bicep               ADLS Gen2 (+4 containers), Data Factory, Databricks, Key Vault
src/ingest_to_adls.py          Upload files to the landing container (DefaultAzureCredential)
src/local_pipeline.py          Same bronze/silver/gold logic in pandas - runs with no Azure account
databricks/01_bronze.py        PySpark notebooks (Delta Lake)
databricks/02_silver.py
databricks/03_gold.py
adf/pl_orders_medallion.json   ADF pipeline: Bronze -> Silver -> Gold
data/sample_orders.csv         Sample data (includes a duplicate row and a missing quantity)
```

## 1. Try it locally (no Azure needed)

```bash
pip install -r requirements.txt
python src/local_pipeline.py
```
Results are written to `output/bronze|silver|gold/`. Silver drops the duplicate order 1009 and the row with missing quantity (order 1010).

## 2. Deploy to Azure

```bash
az login
az group create -n rg-dataplatform-dev -l centralindia
az deployment group create -g rg-dataplatform-dev -f infra/main.bicep -p prefix=dplat
```
Note the `storageAccountName` output.

## 3. Ingest data

```bash
export AZURE_STORAGE_ACCOUNT=<storageAccountName>
python src/ingest_to_adls.py --file data/sample_orders.csv
```
Your user needs the **Storage Blob Data Contributor** role on the storage account.

## 4. Run the transformations

1. In the Databricks workspace, import the three files from `databricks/` into `/Shared/dataplatform/`.
2. Give the cluster access to the lake (e.g. Unity Catalog external location, or a service principal with Spark config for `abfss`).
3. Run the notebooks in order, passing the widget `storage_account`.

## 5. Orchestrate with Data Factory

1. In ADF Studio, create a linked service named `ls_databricks` pointing to your workspace.
2. Import `adf/pl_orders_medallion.json` as a pipeline.
3. Trigger it with `storage_account=<storageAccountName>`. Add a schedule or storage-event trigger when ready.

## Ideas to extend

- Auto Loader / structured streaming for incremental ingestion
- Great Expectations or Delta constraints for data quality
- Synapse serverless SQL or Power BI on the gold layer
- CI/CD with GitHub Actions (`az deployment` + Databricks CLI)
