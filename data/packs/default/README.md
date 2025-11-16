# 默认表情包

这是默认表情包目录，包含基本的表情模板。

## 文件说明

- `doge.png` - Doge 表情模板
- `cat.png` - 猫咪表情模板
- `config.json` - 包级别配置文件（可选）

## 添加新表情

1. 将图片文件放入此目录
2. 支持的格式：PNG, JPG, JPEG, GIF, BMP, WEBP
3. 在主配置文件中添加对应的快捷方式配置
4. 运行 `python scripts/gen_checksum.py` 更新校验和

## 注意事项

- 图片文件名应与命令名称一致
- 建议使用透明背景的 PNG 格式
- 图片大小建议不超过 2MB