#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitHub Projectのタスク一覧をテキスト化するスクリプト

このスクリプトは、GraphQL APIを使用してGitHubプロジェクトのタスク情報を取得し、
docs/tasks.mdファイルにマークダウン形式で書き込みます。
"""

import os
import json
import re
import datetime
import subprocess
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

    return env_vars


def run_command(command):
    """コマンドを実行する関数

    Args:
        command (str): 実行するコマンド

    Returns:
        str: コマンドの出力
    """
    print(f"コマンドを実行します: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"コマンド実行エラー: {e}")
        print(f"エラー出力: {e.stderr}")
        raise


def fetch_project_tasks(env_vars):
    """GitHubプロジェクトのタスク情報を取得する関数

    Args:
        env_vars (dict): 環境変数の辞書

    Returns:
        list: タスク情報のリスト
    """
    # GraphQLクエリを作成
    query = f"""
    query {{
      user(login: "{env_vars["REPO_OWNER"]}") {{
        projectV2(number: {env_vars["GITHUB_PROJECT_NUMBER"]}) {{
          items(first: 100) {{
            nodes {{
              content {{
                ... on Issue {{
                  title
                  number
                  state
                  body
                  url
                  labels(first: 10) {{
                    nodes {{
                      name
                    }}
                  }}
                  assignees(first: 5) {{
                    nodes {{
                      login
                      name
                    }}
                  }}
                  repository {{
                    name
                    owner {{
                      login
                    }}
                  }}
                }}
              }}
              fieldValues(first: 20) {{
                nodes {{
                  ... on ProjectV2ItemFieldDateValue {{
                    field {{
                      ... on ProjectV2FieldCommon {{
                        name
                      }}
                    }}
                    date
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """

    # GraphQLクエリを実行
    command = f"gh api graphql -f query='{query}'"
    output = run_command(command)

    # JSONをパース
    data = json.loads(output)

    # タスク情報を取得
    try:
        project_items = data["data"]["user"]["projectV2"]["items"]["nodes"]
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

    if task_item.get("fieldValues") and task_item["fieldValues"].get("nodes"):
        for field_value in task_item["fieldValues"]["nodes"]:
            if not field_value.get("field"):
                continue

            field_name = field_value["field"]["name"]

            if field_name in ["開始日", "Start date"] and "date" in field_value:
                task_info["start_date"] = field_value["date"]
            elif field_name in ["終了日", "End date"] and "date" in field_value:
                task_info["end_date"] = field_value["date"]

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
                return "はい（終了日が過去の日付）"
            else:
                return "いいえ（終了日は未来の日付）"
        except ValueError:
            pass

    # 本文内の期限がある場合
    if task_info["deadline_in_body"]:
        try:
            deadline = datetime.date.fromisoformat(task_info["deadline_in_body"])
            if deadline < today:
                return "はい（本文内の期限が過去の日付）"
            else:
                return "いいえ（本文内の期限は未来の日付）"
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
    category_match = re.match(r"\[(.+?)\]", task_info["title"])
    category = category_match.group(1) if category_match else "その他"

    # タイトルからカテゴリ部分を削除
    title = re.sub(r"^\[.+?\]\s*", "", task_info["title"])

    # マークダウン形式に整形
    markdown = f"## {index}. [{category}] {title}\n\n"

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
            if assignee.get("name"):
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

    # 詳細な作業内容を抽出
    if "## 詳細な作業内容" in task_info["body"]:
        # 詳細な作業内容セクションを抽出
        detail_match = re.search(r"## 詳細な作業内容\s*\n(.*?)(?:\n##|\Z)", task_info["body"], re.DOTALL)
        if detail_match:
            detail = detail_match.group(1).strip()
            markdown += f"- **詳細な作業内容**: {detail}\n"
        else:
            markdown += "- **詳細**: 詳細情報なし\n"
    else:
        # 本文から意味のある最初の行を抽出
        lines = [line.strip() for line in task_info["body"].split("\n") if line.strip() and not line.strip().startswith("#")]
        if lines:
            markdown += f"- **詳細**: {lines[0]}\n"
        else:
            markdown += "- **詳細**: 詳細情報なし\n"

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

    print(f"ファイルに書き込みます: {file_path}")
    print(f"ファイルパスの絶対パス: {os.path.abspath(file_path)}")
    print(f"ディレクトリが存在するか: {os.path.exists(os.path.dirname(file_path))}")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"ファイルの書き込みが完了しました: {file_path}")
        print(f"ファイルが存在するか: {os.path.exists(file_path)}")
    except Exception as e:
        print(f"ファイルの書き込み中にエラーが発生しました: {e}")
        raise


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
