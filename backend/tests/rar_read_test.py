import sys
import io
import os
from anyio import run
import rarfile

sys.path.append('../')

async def read_rar_file(file_path: str) -> None:
    """读取RAR文件并输出每个文件的字节数和文件名"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    try:
        # 读取RAR文件
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        # 创建RAR文件对象
        rar_buffer = io.BytesIO(file_bytes)
        with rarfile.RarFile(rar_buffer, 'r') as rar_ref:
            print(f"成功打开RAR文件: {file_path}")
            print(f"压缩包中共包含 {len(rar_ref.infolist())} 个文件")
            print("文件信息列表：")
            print("=" * 60)
            print(f"{'文件名':<30} {'字节数':<10} {'压缩比':<10}")
            print("=" * 60)
            
            # 遍历所有文件
            for file_info in rar_ref.infolist():
                # 跳过目录
                if file_info.is_dir():
                    continue
                
                # 处理文件名编码问题
                try:
                    filename = file_info.filename.encode('cp437').decode('gbk')
                except Exception:
                    filename = file_info.filename
                
                # 跳过系统文件
                if not filename or filename.startswith('__MACOSX'):
                    continue
                
                # 获取文件内容字节数
                try:
                    file_content_bytes = rar_ref.read(file_info.filename)
                    file_size = len(file_content_bytes)
                    # 计算压缩比
                    if file_info.compress_size > 0:
                        compression_ratio = f"{file_info.file_size / file_info.compress_size:.2f}x"
                    else:
                        compression_ratio = "N/A"
                    
                    print(f"{filename:<30} {file_size:<10} {compression_ratio:<10}")
                except rarfile.BadRarFile as e:
                    print(f"读取文件 {filename} 失败: {e}")
                    continue
        
        print("=" * 60)
        print("RAR文件读取完成")
    except Exception as e:
        print(f"读取RAR文件时发生错误: {e}")

async def init() -> None:
    # 示例RAR文件路径
    # 注意：请将此路径替换为您实际的RAR文件路径
    file_location = 'test.rar'
    await read_rar_file(file_location)

if __name__ == '__main__':
    run(init)