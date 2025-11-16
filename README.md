# Meme Maker 表情包制作插件

一个功能强大的 AstrBot 表情包制作插件，支持动态快捷方式注册、多包管理和自定义表情包生成。

## 功能特性

- 🎨 **动态快捷方式注册** - 根据配置文件自动注册/注销命令，无需重启
- 📦 **多包管理** - 支持多个表情包集合，可独立启用/禁用
- 🔄 **热重载** - 支持运行时重载配置，即时生效
- 🎯 **智能命令** - 自动识别包状态，禁用包自动注销相关命令
- 📊 **状态监控** - 实时查看插件运行状态和统计信息
- 🛡️ **错误重试** - 内置重试机制，提高稳定性

## 安装说明

### 1. 环境要求

- Python 3.8+
- AstrBot 框架

### 2. 依赖安装

插件需要以下依赖包，请确保安装：

```bash
pip install skia-python>=129.0.0
pip install cookit>=1.8.0
pip install httpx>=0.27.0
pip install tenacity>=9.0.0
```

或者使用 requirements.txt：

```bash
pip install -r requirements.txt
```

### 3. 插件安装

1. 将插件目录放置到 AstrBot 的插件目录
2. 重启 AstrBot 或重新加载插件
3. 插件会自动创建数据目录和默认配置

## 使用指南

### 基本命令

#### 表情包生成
```bash
/doge 这是一段文字        # 生成 doge 表情包
/cat 另一段文字          # 生成猫咪表情包
```

#### 包管理
```bash
/meme list               # 列出所有表情包
/meme enable default     # 启用默认表情包
/meme disable default    # 禁用默认表情包
/meme reload             # 重新加载配置
/meme status             # 显示插件状态
```

### 配置文件

插件会在数据目录下自动创建 `config.json` 配置文件：

```json
{
  "packs": {
    "default": {
      "display_name": "默认表情包",
      "description": "默认表情包集合",
      "enabled": true,
      "shortcuts": [
        {
          "name": "doge",
          "command": "doge",
          "description": "发送 doge 表情",
          "enabled": true
        },
        {
          "name": "cat",
          "command": "cat",
          "description": "发送猫咪表情",
          "enabled": true
        }
      ],
      "checksum": null
    }
  }
}
```

### 数据目录结构

```
data/
├── config.json          # 主配置文件
├── packs/               # 表情包目录
│   ├── default/         # 默认表情包
│   │   ├── doge.png     # doge 模板图
│   │   ├── cat.png      # 猫咪模板图
│   │   └── config.json  # 包配置文件
│   └── custom/          # 自定义表情包
└── output/              # 生成的表情包输出目录
```

## 高级功能

### 动态快捷方式注册

插件支持根据包配置动态注册/注销命令：

- **启用包时** - 自动注册该包的所有启用的快捷方式
- **禁用包时** - 自动注销该包的所有快捷方式
- **重载配置时** - 清空所有命令，重新按配置注册

### 添加自定义表情包

1. 在 `data/packs/` 下创建新目录，如 `custom/`
2. 放入模板图片文件（如 `meme1.png`, `meme2.png`）
3. 在配置文件中添加包配置：

```json
{
  "packs": {
    "custom": {
      "display_name": "自定义表情包",
      "description": "我的自定义表情包",
      "enabled": true,
      "shortcuts": [
        {
          "name": "meme1",
          "command": "meme1",
          "description": "自定义表情1",
          "enabled": true
        }
      ],
      "checksum": null
    }
  }
}
```

4. 使用 `/meme reload` 重载配置

### 校验和维护

#### 生成校验和

为表情包文件生成校验和以确保完整性：

```bash
python scripts/gen_checksum.py
```

校验和会自动更新到配置文件的 `checksum` 字段。

#### 文件完整性检查

插件会在加载时检查校验和，如果文件被修改会记录警告。

## 故障排除

### 常见问题

**Q: 命令无法识别？**
A: 检查包是否启用，使用 `/meme status` 查看状态，或尝试 `/meme reload` 重载配置。

**Q: 表情包生成失败？**
A: 检查模板文件是否存在，确保依赖包正确安装。

**Q: 配置文件错误？**
A: 删除 `config.json`，插件会重新创建默认配置。

### 日志查看

插件会输出详细的日志信息，包括：
- 命令注册/注销状态
- 配置加载结果
- 错误信息和重试记录

## 开发说明

### 核心架构

- **MemeMakerPlugin** - 主插件类，处理生命周期管理
- **PackConfig** - 表情包配置数据类
- **ShortcutConfig** - 快捷方式配置数据类
- **动态注册** - 运行时命令注册/注销机制

### 扩展开发

如需添加新的图像处理功能：

1. 在 `generate_meme` 方法中添加处理逻辑
2. 使用 skia-python 进行图像渲染
3. 使用 cookit 进行图像操作
4. 返回 `event.image_result()` 发送图片

### API 接口

插件提供以下内部 API：

- `register_shortcut()` - 注册快捷方式
- `unregister_shortcut()` - 注销快捷方式
- `load_config()` - 加载配置
- `save_config()` - 保存配置

## 测试清单

### 功能测试

- [ ] 插件正常初始化
- [ ] 默认表情包命令响应
- [ ] 动态启用/禁用表情包
- [ ] 配置重载功能
- [ ] 状态查询命令
- [ ] 错误处理和重试机制

### 兼容性测试

- [ ] 不同 AstrBot 版本兼容性
- [ ] 多平台部署测试
- [ ] 并发命令处理
- [ ] 大量表情包加载

### 性能测试

- [ ] 命令响应时间
- [ ] 内存使用情况
- [ ] 配置加载速度
- [ ] 动态注册效率

## 更新日志

### v1.3.0
- ✨ 新增动态快捷方式注册功能
- ✨ 新增多包管理支持
- ✨ 新增配置热重载
- 🐛 修复命令冲突问题
- 📚 完善文档和示例

### v1.2.0
- ✨ 基础表情包生成功能
- ✨ 简单命令处理
- 📚 初始文档

## 支持与反馈

如有问题或建议，请通过以下方式联系：

- GitHub Issues: [提交 Issue](https://github.com/kamicry/meme-maker/issues)
- 文档网站: [AstrBot 帮助文档](https://astrbot.app)

## 许可证

本项目采用 AGPL-3.0 许可证，详见 [LICENSE](LICENSE) 文件。

---

**注意**: 本插件为 AstrBot 生态的一部分，请确保使用最新版本的 AstrBot 框架以获得最佳体验。