#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitHub Projectのタスク一覧をテキスト化するスクリプト

このスクリプトは、GitHubのGraphQL APIを使用してプロジェクトのタスク情報を取得し、
docs/tasks.mdファイルにマークダウン形式で書き込みます。
"""

import os
import json
import datetime
import requests
from dotenv import load_dotenv


def load_env_vars():
    """環境変数を読み込む関数

    Returns:
        dict: 環境変数の辞書
    """
    load_dotenv()

    required_vars = ["REPO_OWNER", "REPO_NAME", "GITHUB_PROJECT_NUMBER"]
    env_vars = {}

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"環境変数 {var} が設定されていません。.envファイルを確認してください。")
        env_vars[var] = value

    # GitHub Personal Access Token
    env_vars["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN")
    if not env_vars["GITHUB_TOKEN"]:
        print("警告: GITHUB_TOKENが設定されていません。gh auth statusで認証情報を確認します。")
        # ghコマンドから認証情報を取得する処理を追加する場合はここに記述

    return env_vars


def get_github_token():
    """GitHubのトークンを取得する関数

    環境変数GITHUB_TOKENが設定されていない場合は、ghコマンドから認証情報を取得します。

    Returns:
        str: GitHubのトークン
    """
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # ghコマンドから認証情報を取得
    import subprocess

    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if line.strip().startswith("Token:"):
                return line.split("Token:")[1].strip()
    except Exception as e:
        print(f"ghコマンドからトークンを取得できませんでした: {e}")
        print("gh auth loginでGitHubにログインしてください。")

    return None


def fetch_project_tasks(env_vars):
    """GitHubプロジェクトのタスク情報を取得する関数

    Args:
        env_vars (dict): 環境変数の辞書

    Returns:
        list: タスク情報のリスト
    """
    token = get_github_token()
    if not token:
        raise ValueError("GitHubトークンが取得できませんでした。")

    # GraphQLクエリ
    query = """
    query($owner: String!, $projectNumber: Int!) {
      user(login: $owner) {
        projectV2(number: $projectNumber) {
          title
          items(first: 100) {
            nodes {
              id
              content {
                ... on Issue {
                  title
                  number
                  state
                  body
                  createdAt
                  updatedAt
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
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                      }
                    }
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    # GraphQL APIのエンドポイント
    url = "https://api.github.com/graphql"

    # リクエストヘッダー
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # リクエストの変数
    variables = {"owner": env_vars["REPO_OWNER"], "projectNumber": int(env_vars["GITHUB_PROJECT_NUMBER"])}

    # リクエストデータ
    data = {"query": query, "variables": variables}

    # APIリクエスト
    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise Exception(f"API呼び出しエラー: {response.status_code} {response.text}")

    result = response.json()

    # エラーチェック
    if "errors" in result:
        raise Exception(f"GraphQLエラー: {result['errors']}")

    # タスク情報を取得
    try:
        project_items = result["data"]["user"]["projectV2"]["items"]["nodes"]
        return project_items
    except (KeyError, TypeError) as e:
        raise Exception(f"レスポンスの解析エラー: {e}")


def extract_task_info(task_item):
    """タスク情報を抽出する関数

    Args:
        task_item (dict): タスク情報の辞書

    Returns:
        dict: 整形されたタスク情報
    """
    task_info = {}

    # コンテンツ情報がない場合はスキップ
    if not task_item.get("content"):
        return None

    content = task_item["content"]

    # 基本情報
    task_info["title"] = content.get("title", "")
    task_info["number"] = content.get("number", "")
    task_info["state"] = content.get("state", "")
    task_info["body"] = content.get("body", "")
    task_info["url"] = content.get("url", "")
    task_info["created_at"] = content.get("createdAt", "")
    task_info["updated_at"] = content.get("updatedAt", "")

    # リポジトリ情報
    if content.get("repository"):
        repo = content["repository"]
        task_info["repository"] = f"{repo['owner']['login']}/{repo['name']}"
    else:
        task_info["repository"] = ""

    # ラベル情報
    if content.get("labels") and content["labels"].get("nodes"):
        task_info["labels"] = [label["name"] for label in content["labels"]["nodes"]]
    else:
        task_info["labels"] = []

    # アサイン情報
    if content.get("assignees") and content["assignees"].get("nodes"):
        task_info["assignees"] = [
            {"login": assignee["login"], "name": assignee.get("name", "")} for assignee in content["assignees"]["nodes"]
        ]
    else:
        task_info["assignees"] = []

    # フィールド値
    task_info["start_date"] = ""
    task_info["end_date"] = ""
    task_info["status"] = ""

    if task_item.get("fieldValues") and task_item["fieldValues"].get("nodes"):
        for field_value in task_item["fieldValues"]["nodes"]:
            if not field_value.get("field"):
                continue

            field_name = field_value["field"]["name"]

            if field_name == "開始日" and "date" in field_value:
                task_info["start_date"] = field_value["date"]
            elif field_name == "終了日" and "date" in field_value:
                task_info["end_date"] = field_value["date"]
            elif field_name == "Status" and "name" in field_value:
                task_info["status"] = field_value["name"]

    # 本文から担当者と期限を抽出
    task_info["assignee_in_body"] = extract_assignee_from_body(task_info["body"])
    task_info["deadline_in_body"] = extract_deadline_from_body(task_info["body"])

    # 期限切れ判定
    task_info["is_overdue"] = check_if_overdue(task_info)

    return task_info


def extract_assignee_from_body(body):
    """Issue本文から担当者を抽出する関数

    Args:
        body (str): Issue本文

    Returns:
        str: 担当者名
    """
    import re

    # 担当者を抽出するパターン
    patterns = [
        r"## 担当者\s*\n\s*(.+?)(?:\n|$)",  # ## 担当者 の後の行
        r"担当者[:：]\s*(.+?)(?:\n|$)",  # 担当者: の後
        r"担当[:：]\s*(.+?)(?:\n|$)",  # 担当: の後
    ]

    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(1).strip()

    return ""


def extract_deadline_from_body(body):
    """Issue本文から期限を抽出する関数

    Args:
        body (str): Issue本文

    Returns:
        str: 期限（YYYY-MM-DD形式）
    """
    import re

    # 期限を抽出するパターン
    patterns = [
        r"## 期限\s*\n\s*(.+?)(?:\n|$)",  # ## 期限 の後の行
        r"期限[:：]\s*(.+?)(?:\n|$)",  # 期限: の後
        r"締切[:：]\s*(.+?)(?:\n|$)",  # 締切: の後
        r"deadline[:：]\s*(.+?)(?:\n|$)",  # deadline: の後
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()

            # YYYY-MM-DD形式かチェック
            date_match = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", date_str)
            if date_match:
                year, month, day = date_match.groups()
                return f"{year}-{int(month):02d}-{int(day):02d}"

    return ""


def check_if_overdue(task_info):
    """タスクが期限切れかどうかを判定する関数

    Args:
        task_info (dict): タスク情報

    Returns:
        str: 期限切れの状態（"はい"または"いいえ"と理由）
    """
    today = datetime.date.today()

    # 終了日がある場合
    if task_info["end_date"]:
        try:
            end_date = datetime.date.fromisoformat(task_info["end_date"])
            if end_date < today:
                return f"はい（終了日が過去の日付）"
            else:
                return f"いいえ（終了日は未来の日付）"
        except ValueError:
            pass

    # 本文内の期限がある場合
    if task_info["deadline_in_body"]:
        try:
            deadline = datetime.date.fromisoformat(task_info["deadline_in_body"])
            if deadline < today:
                return f"はい（本文内の期限が過去の日付）"
            else:
                return f"いいえ（本文内の期限は未来の日付）"
        except ValueError:
            pass

    # どちらもない場合
    if task_info["state"] == "CLOSED":
        return "いいえ（タスクは完了済み）"

    return "不明（期限が設定されていません）"


def format_task_to_markdown(task_info, index):
    """タスク情報をマークダウン形式に整形する関数

    Args:
        task_info (dict): タスク情報
        index (int): タスクのインデックス

    Returns:
        str: マークダウン形式のタスク情報
    """
    # タイトルからカテゴリを抽出
    import re

    category_match = re.match(r"\[(.+?)\]", task_info["title"])
    category = category_match.group(1) if category_match else "その他"

    # マークダウン形式に整形
    markdown = f"## {index}. [{category}] {task_info['title']}\n\n"

    # 基本情報
    markdown += "### 基本情報\n"
    markdown += f"- **Issue番号**: #{task_info['number']}\n"
    markdown += f"- **リポジトリ**: {task_info['repository']}\n"
    markdown += f"- **URL**: {task_info['url']}\n"
    markdown += f"- **状態**: {task_info['state']}\n"

    # ラベル情報
    if task_info["labels"]:
        markdown += f"- **ラベル**: {', '.join(task_info['labels'])}\n"

    markdown += "\n"

    # 担当者情報
    markdown += "### 担当者情報\n"

    if task_info["assignees"]:
        assignee_info = []
        for assignee in task_info["assignees"]:
            if assignee["name"]:
                assignee_info.append(f"{assignee['login']} ({assignee['name']})")
            else:
                assignee_info.append(assignee["login"])

        markdown += f"- **GitHubアサイン**: {', '.join(assignee_info)}\n"
    else:
        markdown += "- **GitHubアサイン**: なし\n"

    if task_info["assignee_in_body"]:
        markdown += f"- **Issue本文内の記載**: {task_info['assignee_in_body']}\n"

    markdown += "\n"

    # 詳細内容
    markdown += "### 詳細内容\n"

    # 本文の最初の行を抽出
    first_line = task_info["body"].split("\n")[0] if task_info["body"] else ""
    if first_line.startswith("#"):
        first_line = task_info["body"].split("\n")[1] if len(task_info["body"].split("\n")) > 1 else ""

    if "## 詳細な作業内容" in task_info["body"]:
        # 詳細な作業内容セクションを抽出
        import re

        detail_match = re.search(r"## 詳細な作業内容\s*\n(.*?)(?:\n##|\Z)", task_info["body"], re.DOTALL)
        if detail_match:
            detail = detail_match.group(1).strip()
            markdown += f"- **詳細な作業内容**: {detail}\n"
        else:
            markdown += f"- **詳細**: {first_line}\n"
    else:
        markdown += f"- **詳細**: {first_line}\n"

    if task_info["deadline_in_body"]:
        markdown += f"- **Issue本文内の期限**: {task_info['deadline_in_body']}\n"

    markdown += "\n"

    # プロジェクト情報
    markdown += "### プロジェクト情報\n"

    if task_info["start_date"]:
        markdown += f"- **開始日**: {task_info['start_date']}\n"

    if task_info["end_date"]:
        markdown += f"- **終了日**: {task_info['end_date']}\n"

    markdown += f"- **期限切れ**: {task_info['is_overdue']}\n"

    return markdown


def generate_tasks_markdown(tasks):
    """タスク一覧のマークダウンを生成する関数

    Args:
        tasks (list): タスク情報のリスト

    Returns:
        str: マークダウン形式のタスク一覧
    """
    markdown = "# GitHub Project タスク一覧\n\n"

    for i, task in enumerate(tasks, 1):
        markdown += format_task_to_markdown(task, i)

        # 最後のタスク以外は区切り線を追加
        if i < len(tasks):
            markdown += "\n"

    return markdown


def write_to_file(content, file_path):
    """ファイルに書き込む関数

    Args:
        content (str): 書き込む内容
        file_path (str): ファイルパス
    """
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    """メイン関数"""
    try:
        print("タスク一覧のテキスト化を開始します...")

        # 環境変数を読み込む
        env_vars = load_env_vars()
        print(
            f"環境変数を読み込みました: REPO_OWNER={env_vars['REPO_OWNER']}, REPO_NAME={env_vars['REPO_NAME']}, PROJECT_NUMBER={env_vars['GITHUB_PROJECT_NUMBER']}"
        )

        # プロジェクトのタスク情報を取得
        print("GitHubプロジェクトからタスク情報を取得しています...")
        project_items = fetch_project_tasks(env_vars)
        print(f"{len(project_items)}件のタスクを取得しました。")

        # タスク情報を抽出
        tasks = []
        for item in project_items:
            task_info = extract_task_info(item)
            if task_info:
                tasks.append(task_info)

        print(f"{len(tasks)}件のタスク情報を抽出しました。")

        # マークダウンを生成
        markdown = generate_tasks_markdown(tasks)

        # ファイルに書き込む
        file_path = "docs/tasks.md"
        write_to_file(markdown, file_path)

        print(f"タスク一覧を {file_path} に書き込みました。")

        return 0

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
