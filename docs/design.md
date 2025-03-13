# **要件・設計書**

## **1. 要件定義**

### **1.1 基本情報**
- **プロジェクト名称**: Cline を活用した GitHub ベースの PM 業務支援システム  
- **リポジトリ名**: `pm-bot`  

### **1.2 プロジェクト概要**
本プロジェクトは、Cline（Roo Code）を活用し、GitHub 上でプロジェクトマネジメント（PM）業務を効率化するための仕組みを構築することを目的としています。  
Cline の AI コーディング支援機能を活用し、タスク管理、資料の QA、リスク抽出、Slack / Discord への通知を自動化・半自動化することで、PM の負担を軽減し、プロジェクトの進行をスムーズにします。  

### **1.3 機能要件**

#### **1.3.1 タスク管理**
- GitHub Issues を活用したタスク管理  
- GitHub Projects を用いたカンバン方式の進捗管理  
- Cline による Issue 作成・更新の支援  
- `.clinerules` による Issue 作成フォーマットの統一  

#### **1.3.2 資料の QA**
- Cline による資料の QA（ユーザーの質問に対して回答）  
- ユーザーが Cline に「@/docs/design.md について質問」と指示すると、Cline が回答  
- `.clinerules` に QA のフォーマットを定義  

#### **1.3.3 リスク抽出**
- Cline による設計書・要件定義書のリスク抽出  
- 抽出したリスクを GitHub Issues に登録  
- `.clinerules` にリスク Issue のフォーマットを定義  

#### **1.3.4 Slack / Discord 通知**
- Cline に指示して Slack / Discord Webhook を用いた通知を実施  
- タスクの進捗やリスク情報を Slack / Discord に投稿  
- `.clinerules` に Slack / Discord 通知のフォーマットを定義  

### **1.4 非機能要件**
- Cline の AI 処理を活用し、迅速なタスク管理・QA・リスク抽出を実現  
- GitHub API を活用し、リアルタイムな Issue・PR の管理を可能にする  
- Slack / Discord Webhook の URL を環境変数で管理し、外部に漏れないようにする  
- `.clinerules` の定期的な見直しと更新  

### **1.5 制約条件**
- Cline（Roo Code）を VS Code 上で使用することを前提  
- GitHub Issues / Projects を活用したタスク管理を行う  
- Slack / Discord Webhook を用いた通知を行う  

### **1.6 開発環境**
- **言語**: Python（Cline のカスタマイズ用）  
- **ツール**: Cline（Roo Code）、GitHub、Slack、Discord  
- **開発ツール**: VS Code、GitHub CLI（gh コマンド）  

### **1.7 成果物**
- `.clinerules` 設定ファイル  
- GitHub Issues / Projects の運用ガイド  
- `docs/risk.md`（リスク管理記録）  
- Slack / Discord 通知のフォーマット定義  

---

## **2. システム設計**

### **2.1 システム概要設計**

#### **2.1.1 システムアーキテクチャ**
```
[Cline] <-> [GitHub Issues / Projects] <-> [Slack / Discord Webhook]
```

#### **2.1.2 主要コンポーネント**
1. **Cline（Roo Code）**
   - AI によるタスク管理・QA・リスク抽出の支援  
   - `.clinerules` によるカスタマイズ  
2. **GitHub**
   - Issues / Projects によるタスク管理  
   - PR による資料の管理  
3. **Slack / Discord**
   - Webhook を用いたタスク進捗・リスク情報の通知  

### **2.2 詳細設計**

#### **2.2.1 `.clinerules` の設計**
```plaintext
# Cline Rules

## タスク管理
- Issue 作成時のフォーマット:
  - タイトル: `[カテゴリ] タスク名`
  - 説明: `詳細な作業内容、期限、担当者`
  - ラベル: `To Do, In Progress, Done`

## GitHub Project管理
- 環境変数設定:
  - `.env`ファイルに`REPO_OWNER`、`REPO_NAME`、`GITHUB_PROJECT_NUMBER`を設定
- 認証設定:
  - `gh auth login`でGitHubにログイン
  - `gh auth refresh -s project`でプロジェクト管理に必要なスコープを追加
- プロジェクト情報取得:
  - `gh project list`でプロジェクト一覧を取得
  - `gh project item-list $GITHUB_PROJECT_NUMBER --owner $REPO_OWNER`でタスク一覧を取得

## プロジェクトのタスク管理
- タスク一覧のテキスト化:
  - `docs/tasks.md`ファイルにタスク一覧を整理して保存
  - タスク情報には以下を含める:
    - 基本情報（Issue番号、リポジトリ、URL、状態、ラベル）
    - 担当者情報（GitHubアサイン、Issue本文内の記載）
    - 詳細内容（作業内容、期限など）
    - プロジェクト情報（開始日、終了日、期限切れ状況）

## 資料の QA
- ユーザーが「@/docs/design.md について質問」と指示すると、Cline が回答

## リスク抽出
- リスク Issue のフォーマット:
  - タイトル: `[リスク] 課題名`
  - 説明: `影響範囲、対策案`
  - ラベル: `High Risk, Medium Risk, Low Risk`

## Slack / Discord 通知
- 通知フォーマット:
  - `タスクの進捗: {Issue タイトル} が {ステータス} に変更されました`
  - `リスク情報: {リスク Issue タイトル} が登録されました`
  - `期限切れ警告: {Issue タイトル} (#番号) の期限（YYYY-MM-DD）が過ぎています`

## 期限切れタスクの通知
- 期限切れタスクの検出と通知:
  - `docs/tasks.md`ファイルからClineが期限切れタスクを検出
  - 検出したタスクをDiscordに通知
  - 通知内容に担当者情報を含める
```

#### **2.2.2 データフロー**
1. **タスク管理**
   - Cline に「新しいタスクを作成して」と指示  
   - `.clinerules` に基づき Issue を作成  
   - GitHub Projects で進捗を管理  

2. **資料の QA**
   - ユーザーが「@/docs/design.md について質問」と指示  
   - Cline が内容を解析し、適切な回答を提供  

3. **リスク抽出**
   - Cline に「@/docs/design.md からリスクを抽出して」と指示  
   - 抽出したリスクを Issue に登録  

4. **Slack / Discord 通知**
   - Cline に「この Issue の進捗を Slack / Discord に通知して」と指示  
   - Webhook を用いて Slack / Discord に投稿  

### **2.3 インターフェース設計**
- **GitHub API** を使用して Issue / Projects を管理  
- **Slack / Discord Webhook** を使用して通知を送信  

### **2.4 セキュリティ設計**
- GitHub のアクセス権限を適切に管理  
- Slack / Discord Webhook の URL を環境変数で管理  

### **2.5 実装詳細**

#### **2.5.1 タスク一覧のテキスト化**
- **概要**
  - GitHubプロジェクトのタスク情報を取得し、`docs/tasks.md`ファイルにマークダウン形式で書き込む
  - GraphQL APIを使用して詳細情報（開始日・終了日など）を取得
- **実装ファイル**
  - `src/update_tasks.py`: タスク一覧のテキスト化を行うPythonスクリプト
- **GraphQL APIクエリ例**
  ```graphql
  query {
    user(login: "REPO_OWNER") {
      projectV2(number: PROJECT_NUMBER) {
        items(first: 100) {
          nodes {
            content {
              ... on Issue {
                title
                number
                state
                body
                url
                labels(first: 10) {
                  nodes {
                    name
                  }
                }
                assignees(first: 5) {
                  nodes {
                    login
                    name
                  }
                }
                repository {
                  name
                  owner {
                    login
                  }
                }
              }
            }
            fieldValues(first: 20) {
              nodes {
                ... on ProjectV2ItemFieldDateValue {
                  field {
                    ... on ProjectV2FieldCommon {
                      name
                    }
                  }
                  date
                }
              }
            }
          }
        }
      }
    }
  }
  ```
- **出力フォーマット**
  ```markdown
  # GitHub Project タスク一覧

  ## 1. [カテゴリ] タスク名

  ### 基本情報
  - **Issue番号**: #番号
  - **リポジトリ**: オーナー/リポジトリ
  - **URL**: https://github.com/オーナー/リポジトリ/issues/番号
  - **状態**: OPEN/CLOSED
  - **ラベル**: ラベル名

  ### 担当者情報
  - **GitHubアサイン**: ユーザー名 (表示名)
  - **Issue本文内の記載**: 担当者名

  ### 詳細内容
  - **詳細な作業内容**: 作業内容の説明
  - **Issue本文内の期限**: YYYY-MM-DD

  ### プロジェクト情報
  - **開始日**: YYYY-MM-DD
  - **終了日**: YYYY-MM-DD
  - **期限切れ**: はい/いいえ（理由）
  ```

#### **2.5.2 期限切れタスクの通知**
- **概要**
  - `docs/tasks.md`ファイルから期限切れタスクを検出し、SlackやDiscordに通知
  - 期限切れの判定は、終了日または本文内の期限が過去の日付かどうかで行う
  - 環境変数の設定に応じて、通知先を制御可能
- **実装ファイル**
  - `src/notify_overdue_tasks.py`: 期限切れタスクの通知を行うPythonスクリプト
- **環境変数設定**
  - 通知設定（明示的に有効/無効を制御）:
    - `ENABLE_DISCORD_NOTIFICATION`: Discordへの通知を有効にするか（true/false）
    - `ENABLE_SLACK_NOTIFICATION`: Slackへの通知を有効にするか（true/false）
  - Webhook URL設定（有効にした通知先に必要）:
    - `DISCORD_WEBHOOK_URL`: DiscordのWebhook URL
    - `SLACK_WEBHOOK_URL`: SlackのWebhook URL
- **通知フォーマット**
  ```
  **期限切れ警告**: [タスクタイトル] (#番号) の期限（YYYY-MM-DD）が過ぎています
  **ステータス**: [ステータス]
  **担当者**: [GitHubアサイン] ([Issue本文内の担当者])
  **URL**: [Issue URL]
  ```
- **通知方法**
  - Discord/Slack Webhookを使用して通知
  - 通知コマンド例:
    ```bash
    # Discordに通知
    curl -H "Content-Type: application/json" \
         -d '{
           "content": "**期限切れ警告**: [タスクタイトル] (#番号) の期限（YYYY-MM-DD）が過ぎています\n**ステータス**: [ステータス]\n**担当者**: [GitHubアサイン] ([Issue本文内の担当者])\n**URL**: [Issue URL]"
         }' \
         $DISCORD_WEBHOOK_URL
    
    # Slackに通知
    curl -H "Content-Type: application/json" \
         -d '{
           "text": "**期限切れ警告**: [タスクタイトル] (#番号) の期限（YYYY-MM-DD）が過ぎています\n**ステータス**: [ステータス]\n**担当者**: [GitHubアサイン] ([Issue本文内の担当者])\n**URL**: [Issue URL]"
         }' \
         $SLACK_WEBHOOK_URL
    ```

### **2.6 テスト設計**
- **ユニットテスト**
  - `.clinerules` の適用テスト
  - Cline の Issue 作成・QA・リスク抽出の動作確認
- **統合テスト**
  - GitHub Issues / Projects との連携テスト
  - Slack / Discord 通知の動作確認
