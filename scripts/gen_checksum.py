#!/usr/bin/env python3
"""
表情包文件校验和生成工具

用于为表情包文件生成 MD5 校验和，确保文件完整性。
校验和会自动更新到配置文件中。

使用方法:
    python scripts/gen_checksum.py [pack_name]

参数:
    pack_name: 可选，指定要生成校验和的表情包名称
              如果不指定，则为所有包生成校验和
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional

def calculate_file_checksum(file_path: Path) -> str:
    """计算文件的 MD5 校验和"""
    if not file_path.exists():
        return ""
    
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"计算文件校验和失败 {file_path}: {e}")
        return ""

def calculate_pack_checksum(pack_dir: Path) -> str:
    """计算整个包的校验和"""
    if not pack_dir.exists():
        return ""
    
    # 收集所有图片文件
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']:
        image_files.extend(pack_dir.glob(ext))
        image_files.extend(pack_dir.glob(ext.upper()))
    
    if not image_files:
        return ""
    
    # 按文件名排序确保一致性
    image_files.sort(key=lambda x: x.name.lower())
    
    # 计算所有文件的组合校验和
    combined_hash = hashlib.md5()
    for file_path in image_files:
        file_checksum = calculate_file_checksum(file_path)
        if file_checksum:
            combined_hash.update(file_checksum.encode('utf-8'))
    
    return combined_hash.hexdigest()

def load_config(config_path: Path) -> Dict:
    """加载配置文件"""
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return {}

def save_config(config_path: Path, config: Dict):
    """保存配置文件"""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"配置文件已更新: {config_path}")
    except Exception as e:
        print(f"保存配置文件失败: {e}")

def update_pack_checksum(config: Dict, pack_name: str, checksum: str) -> bool:
    """更新包的校验和"""
    if 'packs' not in config:
        config['packs'] = {}
    
    if pack_name not in config['packs']:
        print(f"包 {pack_name} 在配置中不存在")
        return False
    
    old_checksum = config['packs'][pack_name].get('checksum')
    config['packs'][pack_name]['checksum'] = checksum
    
    if old_checksum != checksum:
        print(f"包 {pack_name} 校验和已更新: {old_checksum} -> {checksum}")
        return True
    else:
        print(f"包 {pack_name} 校验和无变化: {checksum}")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成表情包文件校验和')
    parser.add_argument('pack_name', nargs='?', help='指定包名称（可选）')
    parser.add_argument('--data-dir', default='data', help='数据目录路径')
    args = parser.parse_args()
    
    # 设置路径
    data_dir = Path(args.data_dir)
    packs_dir = data_dir / "packs"
    config_path = data_dir / "config.json"
    
    if not data_dir.exists():
        print(f"数据目录不存在: {data_dir}")
        return
    
    if not packs_dir.exists():
        print(f"表情包目录不存在: {packs_dir}")
        return
    
    # 加载配置
    config = load_config(config_path)
    if not config:
        return
    
    updated = False
    
    # 处理指定的包或所有包
    if args.pack_name:
        pack_name = args.pack_name
        pack_dir = packs_dir / pack_name
        
        if not pack_dir.exists():
            print(f"包目录不存在: {pack_dir}")
            return
        
        print(f"正在为包 {pack_name} 生成校验和...")
        checksum = calculate_pack_checksum(pack_dir)
        
        if checksum:
            if update_pack_checksum(config, pack_name, checksum):
                updated = True
        else:
            print(f"包 {pack_name} 没有找到图片文件")
    else:
        # 处理所有包
        pack_dirs = [d for d in packs_dir.iterdir() if d.is_dir()]
        
        if not pack_dirs:
            print("没有找到任何表情包目录")
            return
        
        print(f"正在为 {len(pack_dirs)} 个包生成校验和...")
        
        for pack_dir in pack_dirs:
            pack_name = pack_dir.name
            print(f"处理包: {pack_name}")
            
            checksum = calculate_pack_checksum(pack_dir)
            
            if checksum:
                if update_pack_checksum(config, pack_name, checksum):
                    updated = True
            else:
                print(f"包 {pack_name} 没有找到图片文件")
    
    # 保存配置（如果有更新）
    if updated:
        save_config(config_path, config)
        print("校验和更新完成")
    else:
        print("校验和无需更新")

if __name__ == "__main__":
    main()