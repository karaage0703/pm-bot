# PM-Bot - PM 業務支援システム

このリポジトリは、Cline（Roo Code）を活用し、プロジェクトマネジメント（PM）業務を効率化するためのシステムです。

## 機能

- **タスク管理**: GitHub Issues/Projects を活用したタスク管理
- **資料の QA**: Cline による資料の質問応答
- **Slack/Discord 通知**: Webhook を用いたタスク進捗・リスク情報の通知
- **プロジェクト資料管理**: materialsフォルダ内の資料をMarkdownに変換して一元管理

## インストール

```bash
# リポジトリのクローン
git clone https://github.com/karaage0703/pm-bot.git
cd pm-bot

# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env ファイルを編集して、必要な環境変数を設定してください
```

## 環境変数の設定

`.env` ファイルに以下の環境変数を設定してください：

- `REPO_OWNER`: リポジトリのオーナー名
- `REPO_NAME`: リポジトリ名
- `GITHUB_PROJECT_NUMBER`: GitHub Projectの番号
- `SLACK_WEBHOOK_URL`: Slack Webhook URL（オプション）
- `DISCORD_WEBHOOK_URL`: Discord Webhook URL（オプション）
- `ENABLE_SLACK_NOTIFICATION`: Slackへの通知を有効にするか（true/false）
- `ENABLE_DISCORD_NOTIFICATION`: Discordへの通知を有効にするか（true/false）

## 使い方

### タスク管理と通知

タスク一覧の更新:

```bash
python src/update_tasks.py
```

期限切れタスクの通知:

```bash
python src/notify_overdue_tasks.py
```

### プロジェクト資料管理

materialsフォルダ内の資料（PDF、PPTX、DOCX、MDなど）をMarkdownに変換して一元管理:

```bash
python src/generate_project_info.py
```

オプション:
- `--input-dir`: 入力ディレクトリのパス（デフォルト: materials）
- `--output-file`: 出力ファイルのパス（デフォルト: docs/project_info.md）
- `--no-recursive`: サブディレクトリを再帰的に処理しない（デフォルトは再帰的に処理する）

### コマンド例

PM-Bot は以下のようなコマンドを処理できます：

- **資料の QA**:
  ```
  @/docs/project_info.md について質問：プロジェクトの目的は何ですか？
  ```

- **Slack/Discord 通知**:
  ```
  Issue #1 の進捗を通知して
  ```

- **期限切れタスクの通知**:
  ```
  期限切れのタスクをDiscordに通知して
  ```

### Dockerを使用する場合

開発環境をDockerで構築することもできます。

1. 開発環境の起動:

```bash
docker compose up -d
```

2. コンテナ内でコマンドを実行:

```bash
# コンテナのシェルにアクセス
docker compose exec app /bin/bash
```

3. 開発環境の停止:

```bash
docker compose down
```

## テスト

テストの実行:

    pytest

### Dockerでのテスト実行

コンテナ内でテストを実行:

```bash
docker compose exec app pytest
