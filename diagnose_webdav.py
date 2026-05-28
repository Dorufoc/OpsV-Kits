"""WebDAV 完整诊断 - 检查所有可能的问题并自动修复"""
import socket
import time
import base64
import subprocess
import sys
import os

host = "127.0.0.1"
port = 8081

print("=" * 60)
print("OpsV-Kits WebDAV 完整诊断")
print("=" * 60)

# 1. 检查注册表
print("\n[1] 检查 Windows WebClient 注册表设置")
try:
    import winreg
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
        r"SYSTEM\CurrentControlSet\Services\WebClient\Parameters", 0, winreg.KEY_READ)
    
    basic_auth_level, _ = winreg.QueryValueEx(key, "BasicAuthLevel")
    file_size_limit, _ = winreg.QueryValueEx(key, "FileSizeLimitInBytes")
    server_not_found_cache, _ = winreg.QueryValueEx(key, "ServerNotFoundCacheLifeTimeInSec")
    winreg.CloseKey(key)
    
    print(f"  BasicAuthLevel = {basic_auth_level}")
    if basic_auth_level == 0:
        print("  [FAIL] Basic 认证完全禁用！WebDAV 无法工作")
    elif basic_auth_level == 1:
        print("  [FAIL] Basic 认证仅允许 HTTPS！HTTP 上的 WebDAV 无法工作")
        print("         这就是 0x80070043 的直接原因！")
    elif basic_auth_level == 2:
        print("  [OK] Basic 认证允许 HTTP+HTTPS")
    
    print(f"  FileSizeLimitInBytes = {file_size_limit} ({file_size_limit // 1024 // 1024}MB)")
    print(f"  ServerNotFoundCacheLifeTimeInSec = {server_not_found_cache}")
    
    need_fix = basic_auth_level != 2
except Exception as e:
    print(f"  ⚠️ 无法读取注册表: {e}")
    need_fix = True

# 2. 检查 WebClient 服务
print("\n[2] 检查 WebClient 服务状态")
try:
    result = subprocess.run(["sc", "query", "WebClient"], capture_output=True, text=True, timeout=5)
    if "RUNNING" in result.stdout:
        print("  ✅ WebClient 服务正在运行")
    else:
        print("  ❌ WebClient 服务未运行！")
        need_fix = True
except Exception as e:
    print(f"  ⚠️ 无法检查: {e}")

# 3. 测试 TCP 连接
print("\n[3] 测试 WebDAV 服务器 TCP 连接")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((host, port))
    s.close()
    print(f"  ✅ {host}:{port} 可连接")
except Exception as e:
    print(f"  ❌ 无法连接 {host}:{port}: {e}")
    print("  请确保 OpsV-Kits 已启动且远程硬盘功能已开启")
    sys.exit(1)

# 4. 发送请求并检查响应
def http_request(req_str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((host, port))
        sock.sendall(req_str.encode("utf-8"))
        time.sleep(0.5)
        resp = b""
        sock.settimeout(2)
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
        except socket.timeout:
            pass
        sock.close()
        return resp.decode("utf-8", errors="replace")
    except Exception as e:
        try: sock.close()
        except: pass
        return f"ERROR: {e}"

creds = base64.b64encode(b"opsv:opsv").decode()

print("\n[4] 测试 OPTIONS 请求")
resp = http_request(
    f"OPTIONS / HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
)
status_line = resp.split('\r\n')[0] if resp else ""
print(f"  状态: {status_line}")
has_dav = "DAV:" in resp or "DAV" in resp
print(f"  DAV 头: {'✅' if has_dav else '❌ 缺少 DAV 头！'}")

print("\n[5] 测试 PROPFIND 无认证 (应返回 401)")
resp = http_request(
    f"PROPFIND / HTTP/1.1\r\nHost: {host}:{port}\r\nDepth: 0\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
)
status_line = resp.split('\r\n')[0] if resp else ""
has_www_auth = "WWW-Authenticate" in resp
has_basic = 'Basic realm=' in resp
print(f"  状态: {status_line}")
print(f"  WWW-Authenticate: {'✅' if has_www_auth else '❌ 缺少！'}")
print(f"  支持 Basic: {'✅' if has_basic else '❌ 不支持 Basic！'}")

# 关键检查: NTLM
has_ntlm = "NTLM" in resp
print(f"  支持 NTLM: {'✅' if has_ntlm else '❌ 不支持 NTLM'}")
if not has_ntlm and basic_auth_level == 1 if 'basic_auth_level' in dir() else True:
    print("  ⚠️ 服务器只支持 Basic 认证，但 Windows 默认不允许 HTTP 上的 Basic！")
    print("     这就是为什么 Windows 报 '找不到网络名'")

print("\n[6] 测试 PROPFIND 带 Basic 认证")
resp = http_request(
    f"PROPFIND / HTTP/1.1\r\nHost: {host}:{port}\r\nAuthorization: Basic {creds}\r\n"
    f"Depth: 0\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
)
status_line = resp.split('\r\n')[0] if resp else ""
print(f"  状态: {status_line}")
is_207 = "207" in status_line
print(f"  结果: {'✅ 认证成功' if is_207 else '❌ 认证失败'}")

# 5. 检查 HTTP 协议版本
print("\n[7] 检查 HTTP 协议版本")
resp = http_request(f"OPTIONS / HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n")
if resp.startswith("HTTP/1.1"):
    print("  ✅ 服务器使用 HTTP/1.1")
elif resp.startswith("HTTP/1.0"):
    print("  ❌ 服务器使用 HTTP/1.0！Windows WebClient 要求 HTTP/1.1")
else:
    print(f"  ⚠️ 异常响应: {resp[:50]}")

# 6. Keep-alive 测试
print("\n[8] 测试 Keep-Alive 连接复用")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
try:
    sock.connect((host, port))
    # 第一个请求
    sock.sendall(f"OPTIONS / HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: Keep-Alive\r\n\r\n".encode())
    time.sleep(0.5)
    resp1 = b""
    sock.settimeout(1)
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk: break
            resp1 += chunk
    except socket.timeout: pass
    
    # 第二个请求 (在同一连接上)
    sock.sendall(f"PROPFIND / HTTP/1.1\r\nHost: {host}:{port}\r\nAuthorization: Basic {creds}\r\nDepth: 0\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".encode())
    time.sleep(0.5)
    resp2 = b""
    sock.settimeout(1)
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk: break
            resp2 += chunk
    except socket.timeout: pass
    sock.close()
    
    r1_ok = b"200" in resp1
    r2_ok = b"207" in resp2
    print(f"  第一个请求 (OPTIONS): {'✅' if r1_ok else '❌'}")
    print(f"  第二个请求 (PROPFIND): {'✅' if r2_ok else '❌ 连接已断开！'}")
    if not r2_ok:
        print("  ❌ Keep-Alive 失败！服务器在第一个请求后关闭了连接")
except Exception as e:
    print(f"  ❌ Keep-Alive 测试失败: {e}")
    try: sock.close()
    except: pass

# 7. 最终诊断
print("\n" + "=" * 60)
print("诊断结论:")
print("=" * 60)

issues = []
if basic_auth_level != 2:
    issues.append("BasicAuthLevel != 2: Windows 不允许 HTTP 上的 Basic 认证")
if not has_ntlm:
    issues.append("服务器不提供 NTLM 认证: Windows WebClient 优先使用 NTLM")

if issues:
    print("\n❌ 发现以下问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    print("\n🔧 推荐修复方案:")
    print("\n  方案 A: 修改注册表允许 HTTP Basic 认证 (需要管理员权限)")
    print("  ─────────────────────────────────────────")
    print("  以管理员身份打开 CMD，执行:")
    print()
    print("    reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\WebClient\\Parameters /v BasicAuthLevel /t REG_DWORD /d 2 /f")
    print("    net stop WebClient && net start WebClient")
    print()
    print("  方案 B: 也增大文件大小限制到 4GB:")
    print("    reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\WebClient\\Parameters /v FileSizeLimitInBytes /t REG_DWORD /d 4294967295 /f")
    print("    net stop WebClient && net start WebClient")
    
    print("\n  修复后执行映射:")
    print("    net use Z: http://localhost:8081/ /user:opsv opsv /persistent:yes")
else:
    print("\n✅ 服务端配置正常，WebDAV 应该可以工作")
    print("  如果仍然失败，请尝试:")
    print("  1. 重启 WebClient: net stop WebClient && net start WebClient")
    print("  2. 清除缓存: 等待 60 秒后重试 (ServerNotFoundCacheLifeTimeInSec)")
    print("  3. 使用 net use 命令而不是资源管理器")

# 自动修复选项
if basic_auth_level != 2:
    print("\n" + "=" * 60)
    try:
        answer = input("是否立即自动修复注册表? (需要管理员权限) [y/N]: ")
        if answer.lower() == 'y':
            print("\n正在修复...")
            r1 = subprocess.run(["reg", "add", 
                r"HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters",
                "/v", "BasicAuthLevel", "/t", "REG_DWORD", "/d", "2", "/f"],
                capture_output=True, text=True)
            if r1.returncode == 0:
                print("  ✅ BasicAuthLevel 已设为 2")
            else:
                print(f"  ❌ 修改失败: {r1.stderr}")
                print("  请以管理员身份运行此脚本")
            
            r2 = subprocess.run(["net", "stop", "WebClient"], capture_output=True, text=True)
            r3 = subprocess.run(["net", "start", "WebClient"], capture_output=True, text=True)
            if r3.returncode == 0:
                print("  ✅ WebClient 服务已重启")
            else:
                print(f"  ⚠️ WebClient 重启: {r3.stderr}")
            
            print("\n修复完成！现在尝试映射:")
            print("  net use Z: http://localhost:8081/ /user:opsv opsv")
    except KeyboardInterrupt:
        print()
