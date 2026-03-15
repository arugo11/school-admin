# Azure CLI 調査証跡

更新日時: 2026-03-15 16:56 JST

## 実行した主要コマンド

```bash
az version
az account show
az account list -o table
az group list -o table
az resource list -o table
az cognitiveservices account list -o table
az cognitiveservices account show -g sit-copilot -n sitcopilotaoai23088
az cognitiveservices account deployment list -g sit-copilot -n sitcopilotaoai23088 -o table
az cognitiveservices account deployment show -g sit-copilot -n sitcopilotaoai23088 --deployment-name sit-copilot-demo-chat
az extension add -n ml
az ml workspace list -o json
az provider show -n Microsoft.CognitiveServices --query "registrationState" -o tsv
az provider show -n Microsoft.MachineLearningServices --query "registrationState" -o tsv
az provider show -n Microsoft.SaaS --query "registrationState" -o tsv
az cognitiveservices account list-kinds -o table
az cognitiveservices account list-skus --kind ComputerVision -l japaneast -o table
az cognitiveservices account list-skus --kind AIServices -l japaneast -o table
az cognitiveservices account list-skus --kind OpenAI -l japaneast -o table
az group create -n school-admin-precheck-rg -l japaneast -o json
az cognitiveservices account create -g school-admin-precheck-rg -n schooladminocr23088 -l japaneast --kind ComputerVision --sku F0 -o json
az resource list -g school-admin-precheck-rg -o table
az cognitiveservices account keys list -g school-admin-precheck-rg -n schooladminocr23088
curl -X POST "https://japaneast.api.cognitive.microsoft.com/vision/v3.2/read/analyze" ...
az cognitiveservices account keys list -g sit-copilot -n sitcopilotaoai23088
curl "https://japaneast.api.cognitive.microsoft.com/openai/deployments/sit-copilot-demo-chat/chat/completions?api-version=2024-10-21" ...
```

## 要点だけの出力抜粋

### 1. サブスクリプション確認

```json
{
  "name": "Azure for Students",
  "state": "Enabled",
  "tenantDisplayName": "SIT",
  "tenantDefaultDomain": "shibaura3.onmicrosoft.com",
  "user": {
    "name": "al23088@sic.shibaura-it.ac.jp",
    "type": "user"
  }
}
```

```text
Name                CloudName    SubscriptionId                        TenantId                              State    IsDefault
------------------  -----------  ------------------------------------  ------------------------------------  -------  -----------
Azure for Students  AzureCloud   4c170a0d-3e6d-42a0-b941-533e4f44e729  bfc5048d-9704-40ed-8a4c-a35ccf36a936  Enabled  True
```

### 2. 既存 resource group

```text
Name                                                                Location    Status
------------------------------------------------------------------  ----------  ---------
sit-copilot                                                         japaneast   Succeeded
ai_appi-sitc-02210594_d4843bb6-e2ea-4f80-af57-e7fa2f5c9a1b_managed  japaneast   Succeeded
```

### 3. 既存 AI 系リソース

```text
Kind    Location    Name                 ResourceGroup
------  ----------  -------------------  ---------------
OpenAI  japaneast   sitcopilotaoai23088  sit-copilot
```

```text
Name                   ResourceGroup    Location    Type                                       Status
---------------------  ---------------  ----------  -----------------------------------------  ---------
sitcopilotstudentsacr  sit-copilot      japaneast   Microsoft.ContainerRegistry/registries     Succeeded
sit-copilot-logs       sit-copilot      japaneast   Microsoft.OperationalInsights/workspaces   Succeeded
sit-copilot-students   sit-copilot      eastasia    Microsoft.Web/staticSites                  Succeeded
sit-copilot-env        sit-copilot      japaneast   Microsoft.App/managedEnvironments          Succeeded
sit-copilot-api        sit-copilot      japaneast   Microsoft.App/containerApps                Succeeded
sitcopilotsearch23088  sit-copilot      japaneast   Microsoft.Search/searchServices            Succeeded
sitcopilotaoai23088    sit-copilot      japaneast   Microsoft.CognitiveServices/accounts       Succeeded
sitcopilotpg23088      sit-copilot      japaneast   Microsoft.DBforPostgreSQL/flexibleServers  Succeeded
```

### 4. 既存 Azure OpenAI deployment

```text
Name                   ResourceGroup
---------------------  ---------------
sit-copilot-demo-chat  sit-copilot
```

```json
{
  "name": "sit-copilot-demo-chat",
  "properties": {
    "model": {
      "name": "gpt-4o-mini",
      "version": "2024-07-18"
    },
    "provisioningState": "Succeeded"
  },
  "sku": {
    "name": "GlobalStandard",
    "capacity": 1
  }
}
```

### 5. OpenAI 実呼び出し

```json
{
  "id": "chatcmpl-DJac73D4F54oVY78mZHveh2cnqil6",
  "model": "gpt-4o-mini-2024-07-18",
  "content": "OK",
  "error": null
}
```

事実:
- 既存 AOAI deployment は API 応答した。
- エンドポイントは `https://japaneast.api.cognitive.microsoft.com/` で成功した。

### 6. Vision SKU 確認

```text
Kind            Name    ResourceType    Tier
--------------  ------  --------------  --------
ComputerVision  F0      accounts        Free
ComputerVision  S1      accounts        Standard
```

```text
Kind        Name    ResourceType    Tier
----------  ------  --------------  --------
AIServices  S0      accounts        Standard
```

```text
Kind    Name    ResourceType    Tier
------  ------  --------------  --------
OpenAI  S0      accounts        Standard
```

### 7. 調査用 resource group 作成

```json
{
  "name": "school-admin-precheck-rg",
  "location": "japaneast",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

### 8. Vision resource 作成

```json
{
  "name": "schooladminocr23088",
  "kind": "ComputerVision",
  "location": "japaneast",
  "sku": {
    "name": "F0"
  },
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

```text
Name                 ResourceGroup             Location    Type                                  Status
-------------------  ------------------------  ----------  ------------------------------------  ---------
schooladminocr23088  school-admin-precheck-rg  japaneast   Microsoft.CognitiveServices/accounts  Succeeded
```

### 9. Read OCR 疎通

```text
operation-location:
https://japaneast.api.cognitive.microsoft.com/vision/v3.2/read/analyzeResults/992fc9f4-491c-45eb-952a-8b1dcba38b5b
```

```json
{
  "status": "succeeded",
  "pages": 2,
  "firstPageLines": [
    "Sample Form: Page 1",
    "Name",
    "John Smith",
    "Age",
    "23"
  ]
}
```

事実:
- Read API の最小疎通は成功。
- 今回の疎通サンプルは英語の手書きフォーム PDF であり、日本語数学答案の精度検証ではない。

### 10. Foundry / Marketplace 関連プロバイダー状態

```text
Namespace                          RegistrationState
---------------------------------  -------------------
Microsoft.CognitiveServices        Registered
Microsoft.MachineLearningServices  NotRegistered
Microsoft.SaaS                     NotRegistered
```

```json
[]
```

事実:
- `az ml workspace list -o json` は空配列。
- 既存の ML workspace / Foundry hub / project は少なくとも CLI 上では見つからなかった。

## 失敗したコマンドとその理由

### 1. RG 作成前に Vision resource を作成

```text
ERROR: (ResourceGroupNotFound) Resource group 'school-admin-precheck-rg' could not be found.
```

理由:
- 並列実行したため、RG の作成完了前に resource 作成が走った。

### 2. `az ml workspace list --scope resource_group -g sit-copilot -o json`

```text
ERROR: unrecognized arguments: --scope resource_group
```

理由:
- 使用した `az ml` 拡張版ではこの引数を受け付けなかった。

### 3. `az cognitiveservices account check-name ...`

```text
ERROR: 'check-name' is misspelled or not recognized by the system.
```

理由:
- 当該サブコマンドは現 CLI に存在しなかった。

### 4. `az cognitiveservices account list-usage -l japaneast -o table`

```text
ERROR: the following arguments are required: --resource-group/-g, --name/-n
```

理由:
- 想定と異なり account 単位の usage コマンドだった。

### 5. OpenAI を resource 固有 FQDN で呼び出し

```text
curl: (6) Could not resolve host: sitcopilotaoai23088.openai.azure.com
```

理由:
- この resource は account 固有 FQDN ではなく、`japaneast.api.cognitive.microsoft.com` エンドポイントで利用する構成だった。

## リソース作成可否の証拠

### 作成できた
- resource group: `school-admin-precheck-rg`
- Vision resource: `schooladminocr23088` (`ComputerVision F0`)

### 既存のため新規作成せずに利用可能
- Azure OpenAI resource: `sitcopilotaoai23088`
- Azure OpenAI deployment: `sit-copilot-demo-chat`

### 未確認
- AI Foundry hub / project / serverless endpoint の新規作成
- 新規 Azure OpenAI resource の追加作成
- Key Vault / Storage の新規作成

未確認理由:
- 調査段階であり、不要な課金・Marketplace 契約・依存リソース増殖を避けたため。

## 再現に必要な最小手順

1. `az login` 済みであることを確認する。
2. `az account show` で既定 subscription を確認する。
3. `az group create -n school-admin-precheck-rg -l japaneast`
4. `az cognitiveservices account create -g school-admin-precheck-rg -n <unique-name> -l japaneast --kind ComputerVision --sku F0`
5. `az cognitiveservices account keys list -g school-admin-precheck-rg -n <unique-name> --query key1 -o tsv`
6. Read API に 1 回だけ `POST /vision/v3.2/read/analyze` を投げる。
7. 既存 AOAI の再利用確認は `sitcopilotaoai23088` の key を取得し、`/openai/deployments/sit-copilot-demo-chat/chat/completions` を最小トークンで呼ぶ。

## 注意

- この証跡ファイルには secret 値そのものは転記していない。
- OCR 疎通用に作成した `school-admin-precheck-rg` と `schooladminocr23088` は現時点で残してある。
