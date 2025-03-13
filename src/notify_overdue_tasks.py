#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
期限切れタスクをSlack/Discordに通知するスクリプト（修正版3）

このスクリプトは、docs/tasks.mdファイルから期限切れタスクを検出し、
SlackやDiscordに通知します。環境変数の設定に応じて、どちらか一方、
または両方に通知することができます。
"""

import os
import re
import json
import requests
from dotenv import load_dotenv


def load_env_vars():
    """環境変数を読み込む関数

    Returns:
        dict: 環境変数の辞書
    """
    # 環境変数をクリア
    if "SLACK_WEBHOOK_URL" in os.environ:
        del os.environ["SLACK_WEBHOOK_URL"]
    if "DISCORD_WEBHOOK_URL" in os.environ:
        del os.environ["DISCORD_WEBHOOK_URL"]
    if "ENABLE_SLACK_NOTIFICATION" in os.environ:
        del os.environ["ENABLE_SLACK_NOTIFICATION"]
    if "ENABLE_DISCORD_NOTIFICATION" in os.environ:
        del os.environ["ENABLE_DISCORD_NOTIFICATION"]

    # 環境変数を読み込む
    load_dotenv(override=True)

    env_vars = {}

    # 通知設定
    enable_discord = os.getenv("ENABLE_DISCORD_NOTIFICATION", "false").lower() in ["true", "1", "yes", "y"]
    enable_slack = os.getenv("ENABLE_SLACK_NOTIFICATION", "false").lower() in ["true", "1", "yes", "y"]

    env_vars["ENABLE_DISCORD_NOTIFICATION"] = enable_discord
    env_vars["ENABLE_SLACK_NOTIFICATION"] = enable_slack

    # Discord Webhook URL
    if enable_discord:
        discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if discord_webhook_url:
            env_vars["DISCORD_WEBHOOK_URL"] = discord_webhook_url
        else:
            print("警告: ENABLE_DISCORD_NOTIFICATION=trueですが、DISCORD_WEBHOOK_URLが設定されていません。")

    # Slack Webhook URL
    if enable_slack:
        slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if slack_webhook_url:
            # 環境変数から読み込んだWebhook URLを表示
            print(f"環境変数から読み込んだSlack Webhook URL: {slack_webhook_url[:30]}...")
            env_vars["SLACK_WEBHOOK_URL"] = slack_webhook_url
        else:
            print("警告: ENABLE_SLACK_NOTIFICATION=trueですが、SLACK_WEBHOOK_URLが設定されていません。")

    # 少なくとも1つの通知先が有効かつWebhook URLが設定されている必要がある
    if (not enable_discord or "DISCORD_WEBHOOK_URL" not in env_vars) and (
        not enable_slack or "SLACK_WEBHOOK_URL" not in env_vars
    ):
        raise ValueError(
            "有効な通知先がありません。ENABLE_DISCORD_NOTIFICATION、ENABLE_SLACK_NOTIFICATION、DISCORD_WEBHOOK_URL、SLACK_WEBHOOK_URLの設定を確認してください。"
        )

    return env_vars


def extract_tasks_from_markdown(file_path):
    """マークダウンファイルからタスク情報を抽出する関数

    Args:
        file_path (str): マークダウンファイルのパス

    Returns:
        list: タスク情報のリスト
    """
    # ファイルが存在するか確認
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    # ファイルを読み込む
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # タスクブロックを抽出
    task_blocks = re.split(r"\n## \d+\.", content)

    # 最初のブロックはヘッダーなのでスキップ
    task_blocks = task_blocks[1:]

    tasks = []
    for i, block in enumerate(task_blocks, 1):
        # タスク情報を抽出
        task = {}

        # タイトルを抽出
        title_match = re.search(r"\[(.+?)\] (.+?)(?:\n|$)", block)
        if title_match:
            task["category"] = title_match.group(1)
            task["title"] = title_match.group(2)
        else:
            continue

        # Issue番号を抽出
        issue_number_match = re.search(r"\*\*Issue番号\*\*: #(\d+)", block)
        if issue_number_match:
            task["number"] = issue_number_match.group(1)
        else:
            continue

        # URLを抽出
        url_match = re.search(r"\*\*URL\*\*: (.+?)(?:\n|$)", block)
        if url_match:
            task["url"] = url_match.group(1)
        else:
            continue

        # 状態を抽出
        state_match = re.search(r"\*\*状態\*\*: (.+?)(?:\n|$)", block)
        if state_match:
            task["state"] = state_match.group(1)
        else:
            continue

        # GitHubアサインを抽出
        assignee_match = re.search(r"\*\*GitHubアサイン\*\*: (.+?)(?:\n|$)", block)
        if assignee_match and assignee_match.group(1) != "なし":
            task["assignee"] = assignee_match.group(1)
        else:
            task["assignee"] = "なし"

        # Issue本文内の担当者を抽出
        assignee_in_body_match = re.search(r"\*\*Issue本文内の記載\*\*: (.+?)(?:\n|$)", block)
        if assignee_in_body_match:
            task["assignee_in_body"] = assignee_in_body_match.group(1)
        else:
            task["assignee_in_body"] = ""

        # 終了日を抽出
        end_date_match = re.search(r"\*\*終了日\*\*: (\d{4}-\d{2}-\d{2})", block)
        if end_date_match:
            task["end_date"] = end_date_match.group(1)
        else:
            task["end_date"] = ""

        # Issue本文内の期限を抽出
        deadline_match = re.search(r"\*\*Issue本文内の期限\*\*: (\d{4}-\d{2}-\d{2})", block)
        if deadline_match:
            task["deadline"] = deadline_match.group(1)
        else:
            task["deadline"] = ""

        # 期限切れ状態を抽出
        overdue_match = re.search(r"\*\*期限切れ\*\*: (.+?)(?:\n|$)", block)
        if overdue_match:
            task["is_overdue"] = overdue_match.group(1)
        else:
            task["is_overdue"] = ""

        tasks.append(task)

    return tasks


def filter_overdue_tasks(tasks):
    """期限切れタスクをフィルタリングする関数

    Args:
        tasks (list): タスク情報のリスト

    Returns:
        list: 期限切れタスクのリスト
    """
    overdue_tasks = []
    for task in tasks:
        if task["is_overdue"].startswith("はい"):
            overdue_tasks.append(task)

    return overdue_tasks


def create_notification_message(task):
    """通知メッセージを作成する関数

    Args:
        task (dict): タスク情報

    Returns:
        str: 通知メッセージ
    """
    # 期限を取得
    deadline = task.get("deadline", "") or task.get("end_date", "")

    # 通知内容を作成
    content = (
        f"**期限切れ警告**: [{task['category']}] {task['title']} (#{task['number']}) の期限（{deadline}）が過ぎています\n"
    )
    content += f"**ステータス**: {task['state']}\n"

    # 担当者情報を追加
    if task["assignee_in_body"]:
        content += f"**担当者**: {task['assignee']} ({task['assignee_in_body']})\n"
    else:
        content += f"**担当者**: {task['assignee']}\n"

    content += f"**URL**: {task['url']}"

    return content


def send_discord_notification(webhook_url, task):
    """Discordに通知を送信する関数

    Args:
        webhook_url (str): Discord WebhookのURL
        task (dict): タスク情報

    Returns:
        bool: 送信成功の場合はTrue、失敗の場合はFalse
    """
    # 通知内容を作成
    content = create_notification_message(task)

    # Discordに通知
    payload = {"content": content}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Discordへの通知送信エラー: {e}")
        return False


def send_slack_notification(webhook_url, task):
    """Slackに通知を送信する関数（requestsライブラリを使用）

    Args:
        webhook_url (str): Slack WebhookのURL
        task (dict): タスク情報

    Returns:
        bool: 送信成功の場合はTrue、失敗の場合はFalse
    """
    # 期限を取得
    deadline = task.get("deadline", "") or task.get("end_date", "")

    # 通知内容を作成
    message = f"期限切れタスク: [{task['category']}] {task['title']} (#{task['number']}) の期限（{deadline}）が過ぎています"

    print(f"Slackへの通知内容: {message}")
    print(f"Slack Webhook URL: {webhook_url[:30]}...")

    # requestsライブラリを使用してメッセージを送信
    payload = {"text": message}
    headers = {"Content-type": "application/json"}

    try:
        print("Slackへメッセージを送信します...")
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)

        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.text}")

        if response.status_code == 200 and response.text == "ok":
            print("Slackへの通知送信成功")
            return True
        else:
            print(f"Slackへの通知送信エラー: ステータスコード={response.status_code}")
            return False
    except Exception as e:
        print(f"Slackへの通知送信エラー: {e}")
        return False


def main():
    """メイン関数"""
    try:
        print("期限切れタスクの通知を開始します...")

        # 環境変数を読み込む
        env_vars = load_env_vars()

        # マークダウンファイルからタスク情報を抽出
        file_path = "docs/tasks.md"
        tasks = extract_tasks_from_markdown(file_path)
        print(f"{len(tasks)}件のタスクを抽出しました。")

        # 期限切れタスクをフィルタリング
        overdue_tasks = filter_overdue_tasks(tasks)
        print(f"{len(overdue_tasks)}件の期限切れタスクを検出しました。")

        # 期限切れタスクがない場合は終了
        if not overdue_tasks:
            print("期限切れタスクはありません。")
            return 0

        # 期限切れタスクを通知
        discord_success = 0
        slack_success = 0

        for task in overdue_tasks:
            print(f"期限切れタスク: [{task['category']}] {task['title']} (#{task['number']})")

            # Discordに通知
            if env_vars["ENABLE_DISCORD_NOTIFICATION"] and "DISCORD_WEBHOOK_URL" in env_vars:
                if send_discord_notification(env_vars["DISCORD_WEBHOOK_URL"], task):
                    discord_success += 1

            # Slackに通知
            if env_vars["ENABLE_SLACK_NOTIFICATION"] and "SLACK_WEBHOOK_URL" in env_vars:
                if send_slack_notification(env_vars["SLACK_WEBHOOK_URL"], task):
                    slack_success += 1

        # 通知結果を表示
        if env_vars["ENABLE_DISCORD_NOTIFICATION"] and "DISCORD_WEBHOOK_URL" in env_vars:
            print(f"Discord: {discord_success}/{len(overdue_tasks)}件の通知を送信しました。")
        else:
            print("Discord通知は無効です。")

        if env_vars["ENABLE_SLACK_NOTIFICATION"] and "SLACK_WEBHOOK_URL" in env_vars:
            print(f"Slack: {slack_success}/{len(overdue_tasks)}件の通知を送信しました。")
        else:
            print("Slack通知は無効です。")

        return 0

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
