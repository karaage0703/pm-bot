# PM-Bot - GitHub ベースの PM 業務支援システム

このリポジトリは、Cline（Roo Code）を活用し、GitHub 上でプロジェクトマネジメント（PM）業務を効率化するためのシステムです。

## 機能

- **タスク管理**: GitHub Issues/Projects を活用したタスク管理
- **資料の QA**: Cline による資料の質問応答
- **リスク抽出**: 設計書からのリスク抽出と Issue 登録
- **Slack/Discord 通知**: Webhook を用いたタスク進捗・リスク情報の通知

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

## 使い方

メインプログラムの実行:

```bash
python -m src.main
```

### コマンド例

PM-Bot は以下のようなコマンドを処理できます：

- **タスク作成**:
  ```
  タスクを作成して：開発、ログイン機能実装、ユーザー認証機能を実装する、2023-12-31、開発者A
  ```

- **タスクステータス更新**:
  ```
  タスク #1 のステータスを In Progress に変更して
  ```

- **資料の QA**:
  ```
  @/docs/design.md について質問：プロジェクトの目的は何ですか？
  ```

- **リスク抽出**:
  ```
  @/docs/design.md からリスクを抽出して
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
```
