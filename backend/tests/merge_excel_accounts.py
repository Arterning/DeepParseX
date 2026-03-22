#!/usr/bin/env python3
"""
合并多个 Excel 文件中的账号信息并去重

用法:
    python merge_excel_accounts.py <目录路径>

功能:
    - 遍历指定目录下所有的 xlsx 文件
    - 读取"账号"、"邮箱"、"密码"三个字段
    - 去除完全重复的数据（三个字段都相同）
    - 保存到当前工作目录下的 output.csv 文件
"""

import argparse
import sys
from pathlib import Path
import pandas as pd


def read_excel_files(directory: Path) -> pd.DataFrame:
    """
    读取目录下所有 xlsx 文件并合并数据

    Args:
        directory: 要扫描的目录路径

    Returns:
        合并后的 DataFrame
    """
    all_data = []
    xlsx_files = list(directory.glob('**/*.xlsx'))

    if not xlsx_files:
        print(f"警告: 在目录 {directory} 中没有找到任何 xlsx 文件")
        return pd.DataFrame(columns=['账号', '邮箱', '密码'])

    print(f"找到 {len(xlsx_files)} 个 xlsx 文件")

    for xlsx_file in xlsx_files:
        try:
            print(f"正在读取: {xlsx_file}")
            # 读取 Excel 文件
            df = pd.read_excel(xlsx_file)

            # 检查是否包含所需的列
            required_columns = ['账号', '邮箱', '密码']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                print(f"  警告: 文件 {xlsx_file.name} 缺少列: {missing_columns}，将使用空值填充")
                # 为缺失的列添加空值
                for col in missing_columns:
                    df[col] = None

            # 只保留需要的三列
            df_filtered = df[required_columns].copy()

            # 记录读取的行数
            print(f"  读取了 {len(df_filtered)} 行数据")
            all_data.append(df_filtered)

        except Exception as e:
            print(f"  错误: 读取文件 {xlsx_file} 时发生错误: {e}")
            continue

    if not all_data:
        print("错误: 没有成功读取任何数据")
        return pd.DataFrame(columns=['账号', '邮箱', '密码'])

    # 合并所有数据
    merged_df = pd.concat(all_data, ignore_index=True)
    print(f"\n合并后总计: {len(merged_df)} 行数据")

    return merged_df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    去除重复的数据行

    Args:
        df: 原始 DataFrame

    Returns:
        去重后的 DataFrame
    """
    initial_count = len(df)
    # 去除账号、邮箱、密码完全相同的重复行
    df_unique = df.drop_duplicates(subset=['账号', '邮箱', '密码'], keep='first')
    removed_count = initial_count - len(df_unique)

    print(f"去重前: {initial_count} 行")
    print(f"去重后: {len(df_unique)} 行")
    print(f"移除了 {removed_count} 行重复数据")

    return df_unique


def save_to_csv(df: pd.DataFrame, output_file: str = 'output.csv'):
    """
    保存 DataFrame 到 CSV 文件

    Args:
        df: 要保存的 DataFrame
        output_file: 输出文件名
    """
    try:
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        output_path = Path(output_file).resolve()
        print(f"\n成功保存到: {output_path}")
        print(f"共保存 {len(df)} 条记录")
    except Exception as e:
        print(f"错误: 保存文件时发生错误: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='合并目录下所有 xlsx 文件中的账号信息并去重',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python merge_excel_accounts.py ./data
    python merge_excel_accounts.py "C:/Users/username/Documents/accounts"
        """
    )
    parser.add_argument(
        'directory',
        type=str,
        help='包含 xlsx 文件的目录路径'
    )

    args = parser.parse_args()

    # 验证目录是否存在
    directory = Path(args.directory)
    if not directory.exists():
        print(f"错误: 目录不存在: {directory}")
        sys.exit(1)

    if not directory.is_dir():
        print(f"错误: 路径不是目录: {directory}")
        sys.exit(1)

    print(f"开始处理目录: {directory.resolve()}\n")
    print("=" * 60)

    # 读取所有 Excel 文件
    merged_df = read_excel_files(directory)

    if merged_df.empty:
        print("\n没有数据可以保存")
        sys.exit(0)

    print("=" * 60)

    # 去重
    unique_df = remove_duplicates(merged_df)

    print("=" * 60)

    # 保存到 CSV
    save_to_csv(unique_df)


if __name__ == '__main__':
    main()
