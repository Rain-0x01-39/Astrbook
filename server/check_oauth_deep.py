#!/usr/bin/env python3
"""
OAuth 账号深度检查脚本

进一步排查用户登录到其他人账号的问题

使用方法:
    cd server
    python check_oauth_deep.py
"""

import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, ".")

from sqlalchemy import func, or_, and_
from app.database import SessionLocal
from app.models import User, OAuthAccount


def check_similar_usernames(db):
    """检查相似用户名（可能导致混淆）"""
    print("\n" + "=" * 60)
    print("🔍 检查 1: 相似/相同前缀的用户名")
    print("=" * 60)
    
    users = db.query(User).all()
    
    # 按前缀分组
    prefix_groups = defaultdict(list)
    for user in users:
        # 提取前缀（去掉 _数字 后缀）
        username = user.username
        if username.startswith("gh_"):
            base = username[3:].rsplit("_", 1)[0] if "_" in username[3:] else username[3:]
            prefix_groups[f"gh_{base}"].append(user)
        elif username.startswith("ld_"):
            base = username[3:].rsplit("_", 1)[0] if "_" in username[3:] else username[3:]
            prefix_groups[f"ld_{base}"].append(user)
    
    issues = [(prefix, users) for prefix, users in prefix_groups.items() if len(users) > 1]
    
    if issues:
        print(f"\n⚠️  发现 {len(issues)} 组相似用户名:\n")
        for prefix, user_list in issues[:10]:  # 只显示前10组
            print(f"  前缀: {prefix}")
            for user in user_list:
                oauth = db.query(OAuthAccount).filter(OAuthAccount.user_id == user.id).first()
                oauth_info = f"{oauth.provider}:{oauth.provider_user_id}" if oauth else "无OAuth"
                print(f"    - ID:{user.id} 用户名:{user.username} OAuth:{oauth_info} 创建:{user.created_at}")
            print()
        if len(issues) > 10:
            print(f"  ... 还有 {len(issues) - 10} 组未显示")
    else:
        print("\n✅ 未发现相似用户名问题。")


def check_same_time_registrations(db):
    """检查短时间内的注册（可能是并发问题）"""
    print("\n" + "=" * 60)
    print("🔍 检查 2: 短时间内的批量注册")
    print("=" * 60)
    
    users = db.query(User).order_by(User.created_at).all()
    
    close_registrations = []
    for i in range(1, len(users)):
        if users[i].created_at and users[i-1].created_at:
            time_diff = users[i].created_at - users[i-1].created_at
            # 5秒内的连续注册
            if abs(time_diff.total_seconds()) < 5:
                close_registrations.append((users[i-1], users[i], time_diff))
    
    if close_registrations:
        print(f"\n⚠️  发现 {len(close_registrations)} 对在5秒内注册的用户:\n")
        for user1, user2, diff in close_registrations[:10]:
            print(f"  用户1: ID:{user1.id} {user1.username} @ {user1.created_at}")
            print(f"  用户2: ID:{user2.id} {user2.username} @ {user2.created_at}")
            print(f"  时间差: {diff.total_seconds():.2f}秒")
            print()
    else:
        print("\n✅ 未发现异常的短时间批量注册。")


def check_token_collisions(db):
    """检查 Bot Token 是否有冲突"""
    print("\n" + "=" * 60)
    print("🔍 检查 3: Bot Token 冲突")
    print("=" * 60)
    
    # 检查重复的 token
    duplicates = db.query(
        User.token,
        func.count(User.id).label("count")
    ).group_by(User.token).having(func.count(User.id) > 1).all()
    
    if duplicates:
        print(f"\n🚨 严重！发现 {len(duplicates)} 组重复的 Bot Token:\n")
        for token, count in duplicates:
            users = db.query(User).filter(User.token == token).all()
            print(f"  Token: {token[:20]}... (共 {count} 个用户)")
            for user in users:
                print(f"    - ID:{user.id} 用户名:{user.username}")
            print()
        return len(duplicates)
    else:
        print("\n✅ 未发现 Bot Token 冲突。")
        return 0


def check_oauth_user_id_mapping(db):
    """检查 OAuth provider_user_id 与用户的映射关系"""
    print("\n" + "=" * 60)
    print("🔍 检查 4: OAuth ID 映射详情")
    print("=" * 60)
    
    # 列出所有 OAuth 绑定
    oauth_records = db.query(OAuthAccount).order_by(OAuthAccount.created_at.desc()).limit(20).all()
    
    print(f"\n最近 20 条 OAuth 绑定记录:\n")
    print(f"{'OAuth ID':<10} {'Provider':<10} {'Provider UID':<20} {'User ID':<10} {'Username':<25} {'Created'}")
    print("-" * 100)
    
    for record in oauth_records:
        user = db.query(User).filter(User.id == record.user_id).first()
        username = user.username if user else "[已删除]"
        provider_uid = record.provider_user_id[:15] + "..." if len(record.provider_user_id) > 15 else record.provider_user_id
        created = record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else "N/A"
        print(f"{record.id:<10} {record.provider:<10} {provider_uid:<20} {record.user_id:<10} {username:<25} {created}")


def check_jwt_token_analysis(db):
    """分析 JWT Token 的结构"""
    print("\n" + "=" * 60)
    print("🔍 检查 5: JWT Token 分析")
    print("=" * 60)
    
    import base64
    import json
    
    # 取几个用户的 token 分析
    users = db.query(User).limit(5).all()
    
    print("\n分析前 5 个用户的 Bot Token 结构:\n")
    
    for user in users:
        if not user.token:
            print(f"用户 {user.username}: 无 Token")
            continue
            
        try:
            # JWT 格式: header.payload.signature
            parts = user.token.split(".")
            if len(parts) == 3:
                # 解码 payload
                payload_b64 = parts[1]
                # 添加 padding
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                
                print(f"用户 ID:{user.id} {user.username}")
                print(f"  Token 中的 sub (user_id): {payload.get('sub')}")
                print(f"  Token 类型: {payload.get('type')}")
                print(f"  Token ID (jti): {payload.get('jti', 'N/A')[:16]}...")
                
                # 检查 sub 是否匹配
                if str(user.id) != str(payload.get('sub')):
                    print(f"  🚨 警告: Token 中的 user_id ({payload.get('sub')}) 与实际 user_id ({user.id}) 不匹配!")
                print()
        except Exception as e:
            print(f"用户 {user.username}: Token 解析失败 - {e}")


def analyze_specific_user(db, username_or_id):
    """分析特定用户"""
    print("\n" + "=" * 60)
    print(f"🔍 分析特定用户: {username_or_id}")
    print("=" * 60)
    
    if str(username_or_id).isdigit():
        user = db.query(User).filter(User.id == int(username_or_id)).first()
    else:
        user = db.query(User).filter(User.username == username_or_id).first()
    
    if not user:
        print(f"\n❌ 未找到用户: {username_or_id}")
        return
    
    print(f"\n用户信息:")
    print(f"  ID: {user.id}")
    print(f"  用户名: {user.username}")
    print(f"  昵称: {user.nickname}")
    print(f"  头像: {user.avatar}")
    print(f"  有密码: {'是' if user.password_hash else '否'}")
    print(f"  创建时间: {user.created_at}")
    
    oauth_records = db.query(OAuthAccount).filter(OAuthAccount.user_id == user.id).all()
    print(f"\nOAuth 绑定 ({len(oauth_records)} 个):")
    for record in oauth_records:
        print(f"  - {record.provider}: {record.provider_user_id}")
        print(f"    用户名: {record.provider_username}")
        print(f"    创建时间: {record.created_at}")


def main():
    print("\n" + "=" * 60)
    print("🔐 AstrBook OAuth 深度检查")
    print(f"   运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        check_similar_usernames(db)
        check_same_time_registrations(db)
        check_token_collisions(db)
        check_oauth_user_id_mapping(db)
        check_jwt_token_analysis(db)
        
        # 如果知道具体受影响的用户，可以取消下面的注释来分析
        # analyze_specific_user(db, "具体用户名或ID")
        
        print("\n" + "=" * 60)
        print("💡 排查建议")
        print("=" * 60)
        print("""
如果以上检查都正常，可能的原因还包括:

1. 【浏览器缓存问题】
   - 用户 A 在设备上登录后，用户 B 在同一浏览器登录
   - localStorage 中的 token 没有正确更新
   
2. 【前端 Token 存储问题】
   - OAuth 回调时 token 写入失败或被覆盖
   - 检查前端 OAuthCallback.vue 的 localStorage 操作

3. 【CDN/代理缓存】
   - 如果使用了 CDN，可能缓存了包含 token 的响应
   
4. 【多标签页登录冲突】
   - 用户在多个标签页同时进行 OAuth 登录

建议:
   - 让受影响用户清除浏览器缓存后重新登录
   - 收集受影响用户的具体用户名/ID 进行对比分析
   - 在服务端日志中查找 OAuth 回调记录
""")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
