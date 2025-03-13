#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
materialsフォルダ内の資料をdocs/project_info.mdに書き出すスクリプト

このスクリプトは、materialsフォルダ内の様々な形式のファイル（PDF、PPTX、DOCX、MDなど）を
Markdownに変換し、1つのdocs/project_info.mdファイルにまとめます。
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from markitdown import MarkItDown


def parse_arguments():
    """コマンドライン引数をパースする関数

    Returns:
        argparse.Namespace: パースされた引数
    """
    parser = argparse.ArgumentParser(description="materialsフォルダ内の資料をdocs/project_info.mdに書き出すスクリプト")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="materials",
        help="入力ディレクトリのパス（デフォルト: materials）",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="docs/project_info.md",
        help="出力ファイルのパス（デフォルト: docs/project_info.md）",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="サブディレクトリを再帰的に処理しない（デフォルトは再帰的に処理する）",
    )
    return parser.parse_args()


def get_files(directory, recursive=True):
    """指定されたディレクトリ内のファイルを取得する関数

    Args:
        directory (str): ディレクトリのパス
        recursive (bool, optional): サブディレクトリも再帰的に処理するかどうか. Defaults to True.

    Returns:
        list: ファイルパスのリスト
    """
    files = []
    directory_path = Path(directory)

    if recursive:
        for file_path in directory_path.glob("**/*"):
            if file_path.is_file():
                files.append(str(file_path))
    else:
        for file_path in directory_path.glob("*"):
            if file_path.is_file():
                files.append(str(file_path))

    return sorted(files)


def convert_to_markdown(file_path):
    """ファイルをMarkdownに変換する関数

    Args:
        file_path (str): ファイルのパス

    Returns:
        str: Markdown形式のテキスト
    """
    try:
        print(f"変換中: {file_path}")

        # MDファイルの場合は、直接内容を読み込む
        if file_path.lower().endswith(".md"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        # その他のファイルはMarkItDownを使用して変換
        converter = MarkItDown()
        result = converter.convert(file_path)
        return result.text_content
    except Exception as e:
        print(f"エラー: {file_path}の変換に失敗しました: {e}")
        return f"# {os.path.basename(file_path)}\n\n*このファイルの変換に失敗しました。*\n\n"


def generate_project_info(input_dir, output_file, recursive=True):
    """プロジェクト情報を生成する関数

    Args:
        input_dir (str): 入力ディレクトリのパス
        output_file (str): 出力ファイルのパス
        recursive (bool, optional): サブディレクトリも再帰的に処理するかどうか. Defaults to True.

    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 入力ディレクトリが存在するか確認
        if not os.path.exists(input_dir):
            print(f"エラー: 入力ディレクトリ {input_dir} が見つかりません。")
            return False

        # 出力ディレクトリが存在するか確認し、存在しない場合は作成
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # ファイルのリストを取得
        files = get_files(input_dir, recursive)
        if not files:
            print(f"警告: {input_dir} 内にファイルが見つかりません。")
            return False

        # ヘッダーを作成
        header = f"""# プロジェクト情報

このファイルは、materialsフォルダ内の資料を自動的にMarkdownに変換してまとめたものです。

**生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 目次

"""

        # 目次を作成
        toc = ""
        for i, file_path in enumerate(files, 1):
            file_name = os.path.basename(file_path)
            toc += f"{i}. [{file_name}](#{file_name.lower().replace('.', '-').replace(' ', '-')})\n"

        # 各ファイルの内容を変換
        content = ""
        for file_path in files:
            file_name = os.path.basename(file_path)
            content += f"\n\n## {file_name}\n\n"
            content += convert_to_markdown(file_path)
            content += "\n\n---\n"

        # 出力ファイルに書き込む
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(header + toc + content)

        print(f"プロジェクト情報を {output_file} に書き出しました。")
        return True

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メイン関数"""
    args = parse_arguments()
    success = generate_project_info(args.input_dir, args.output_file, not args.no_recursive)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
