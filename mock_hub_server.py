#!/usr/bin/env python3
"""
模拟在线表情包中心API服务器
用于测试插件的在线功能
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

class MockHubHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/packs':
            self.handle_get_packs()
        elif parsed_path.path == '/health':
            self.handle_health()
        else:
            self.send_404()
    
    def handle_get_packs(self):
        """返回模拟的表情包列表"""
        packs = [
            {
                "name": "anime_meme",
                "display_name": "动漫表情包",
                "description": "经典动漫表情包集合",
                "url": "https://example.com/packs/anime_meme.zip",
                "version": "1.0.0",
                "author": "AnimeLover",
                "size": 2048576,  # 2MB
                "preview_url": "https://example.com/previews/anime_meme.jpg",
                "downloads": 1250
            },
            {
                "name": "cat_meme",
                "display_name": "猫咪表情包",
                "description": "可爱的猫咪表情包",
                "url": "https://example.com/packs/cat_meme.zip",
                "version": "1.2.0",
                "author": "CatFan",
                "size": 1536000,  # 1.5MB
                "preview_url": "https://example.com/previews/cat_meme.jpg",
                "downloads": 890
            },
            {
                "name": "programming",
                "display_name": "程序员表情包",
                "description": "程序员专用表情包",
                "url": "https://example.com/packs/programming.zip",
                "version": "2.0.0",
                "author": "DevTeam",
                "size": 3072000,  # 3MB
                "preview_url": "https://example.com/previews/programming.jpg",
                "downloads": 567
            },
            {
                "name": "gaming",
                "display_name": "游戏表情包",
                "description": "游戏玩家表情包",
                "url": "https://example.com/packs/gaming.zip",
                "version": "1.5.0",
                "author": "GamerHub",
                "size": 2560000,  # 2.5MB
                "preview_url": "https://example.com/previews/gaming.jpg",
                "downloads": 2340
            },
            {
                "name": "reaction",
                "display_name": "反应表情包",
                "description": "日常反应表情包",
                "url": "https://example.com/packs/reaction.zip",
                "version": "1.0.0",
                "author": "ReactionMaster",
                "size": 1792000,  # 1.75MB
                "preview_url": "https://example.com/previews/reaction.jpg",
                "downloads": 3420
            }
        ]
        
        response_data = {
            "status": "success",
            "total": len(packs),
            "packs": packs,
            "timestamp": int(time.time())
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
        
        print(f"返回 {len(packs)} 个表情包信息")
    
    def handle_health(self):
        """健康检查"""
        response_data = {
            "status": "ok",
            "timestamp": int(time.time())
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response_json = json.dumps(response_data)
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_404(self):
        """返回404错误"""
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        error_data = {"error": "Not Found"}
        response_json = json.dumps(error_data)
        self.wfile.write(response_json.encode('utf-8'))
    
    def log_message(self, format, *args):
        """重写日志方法以减少输出"""
        print(f"[{self.address_string()}] {format % args}")

def run_mock_server(port=8888):
    """运行模拟服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, MockHubHandler)
    
    print(f"模拟表情包中心API服务器启动在端口 {port}")
    print("可用的API端点:")
    print("  GET /packs - 获取表情包列表")
    print("  GET /health - 健康检查")
    print()
    print("测试命令:")
    print("  curl http://localhost:8888/packs")
    print("  curl http://localhost:8888/health")
    print()
    print("按 Ctrl+C 停止服务器")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
        httpd.shutdown()
        print("服务器已关闭")

if __name__ == "__main__":
    run_mock_server()