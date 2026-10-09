// Azure Data Engineering Platform - infrastructure
// Deploy:
//   az group create -n rg-dataplatform-dev -l centralindia
//   az deployment group create -g rg-dataplatform-dev -f infra/main.bicep -p prefix=dplat

@description('Short lowercase prefix used for resource names (3-10 chars).')
@minLength(3)
@maxLength(10)
param prefix string = 'dplat'

@description('Azure region.')
param location string = resourceGroup().location

var suffix = uniqueString(resourceGroup().id)
var storageName = toLower('${prefix}dl${suffix}')
var adfName = '${prefix}-adf-${suffix}'
var dbxName = '${prefix}-dbx-${suffix}'
var kvName = '${prefix}-kv-${suffix}'

// ---------- Data Lake (ADLS Gen2) with medallion containers ----------
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: take(storageName, 24)
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for name in [
  'landing'
  'bronze'
  'silver'
  'gold'
]: {
  parent: blobService
  name: name
}]

// ---------- Key Vault ----------
resource kv 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: take(kvName, 24)
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

// ---------- Azure Data Factory ----------
resource adf 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: adfName
  location: location
  identity: { type: 'SystemAssigned' }
}

// ---------- Azure Databricks ----------
resource dbx 'Microsoft.Databricks/workspaces@2023-02-01' = {
  name: dbxName
  location: location
  sku: { name: 'standard' }
  properties: {
    managedResourceGroupId: subscriptionResourceId('Microsoft.Resources/resourceGroups', '${dbxName}-managed')
  }
}

// ---------- Let ADF write to the lake (Storage Blob Data Contributor) ----------
var blobContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource adfLakeAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, adf.id, blobContributorRoleId)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobContributorRoleId)
    principalId: adf.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output storageAccountName string = storage.name
output dataFactoryName string = adf.name
output databricksWorkspaceUrl string = dbx.properties.workspaceUrl
output keyVaultName string = kv.name
