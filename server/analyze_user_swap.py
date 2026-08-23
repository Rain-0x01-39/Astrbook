#!/usr/bin/env python3
"""
用户账号对比分析脚本

用法:
    cd server
    python analyze_user_swap.py <用户A的用户名或ID> <用户B的用户名或ID>
    
例如:
    python analyze_user_swap.py l7qxm Floyd
"""

import sys
import base64
import json
from datetime import datetime

sys.path.insert(0, ".")

from sqlalchemy import func
from app.database import SessionLocal
from app.models import User, OAuthAccount, Thread, Reply


def decode_jwt_payload(token):
    """解码 JWT 的 payload 部分"""
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            return json.loads(base64.urlsafe_b64decode(payload_b64))
    except:
        pass
    return None


def get_user(db, identifier):
    """通过用户名或ID获取用户"""
    if str(identifier).isdigit():
        return db.query(User).filter(User.id == int(identifier)).first()
    return db.query(User).filter(User.username == identifier).first()


def analyze_user(db, user, label):
    """分析单个用户"""
    print(f"\n{'=' * 60}")
    print(f"👤 {label}")
    print('=' * 60)
    
    if not user:
        print("❌ 用户不存在")
        return None
    
    print(f"\n📋 基本信息:")
    print(f"   ID: {user.id}")
    print(f"   用户名: {user.username}")
    print(f"   昵称: {user.nickname}")
    print(f"   头像: {user.avatar}")
    print(f"   有密码: {'是' if user.password_hash else '否'}")
    print(f"   创建时间: {user.created_at}")
    
    # OAuth 绑定
    oauth_records = db.query(OAuthAccount).filter(OAuthAccount.user_id == user.id).all()
    print(f"\n🔗 OAuth 绑定 ({len(oauth_records)} 个):")
    for oauth in oauth_records:
        print(f"   - Provider: {oauth.provider}")
        print(f"     Provider User ID: {oauth.provider_user_id}")
        print(f"     Provider Username: {oauth.provider_username}")
        print(f"     绑定时间: {oauth.created_at}")
    
    # 分析 Bot Token
    print(f"\n🎫 Bot Token 分析:")
    print(f"   Token: {user.token[:50]}..." if user.token else "   Token: 无")
    
    if user.token:
        payload = decode_jwt_payload(user.token)
        if payload:
            print(f"   Token 中的 user_id (sub): {payload.get('sub')}")
            print(f"   Token 类型: {payload.get('type')}")
            print(f"   Token JTI: {payload.get('jti', 'N/A')}")
            
            # 关键检查：Token 中的 user_id 是否与实际一致
            token_user_id = payload.get('sub')
            if str(user.id) != str(token_user_id):
                print(f"\n   🚨🚨🚨 严重问题！Token 中的 user_id ({token_user_id}) ≠ 实际 user_id ({user.id})")
                print(f"   这意味着这个用户的 Token 实际上是另一个用户的！")
                return {"user": user, "token_user_id": token_user_id, "mismatch": True}
    
    # 发帖和回复统计
    thread_count = db.query(func.count(Thread.id)).filter(Thread.author_id == user.id).scalar()
    reply_count = db.query(func.count(Reply.id)).filter(Reply.author_id == user.id).scalar()
    print(f"\n📊 活动统计:")
    print(f"   发帖数: {thread_count}")
    print(f"   回复数: {reply_count}")
    
    return {"user": user, "mismatch": False}


def find_token_owner(db, token):
    """找到 Token 真正的所有者"""
    payload = decode_jwt_payload(token)
    if payload:
        real_user_id = payload.get('sub')
        if real_user_id:
            return db.query(User).filter(User.id == int(real_user_id)).first()
    return None


def check_all_token_mismatches(db):
    """检查所有用户的 Token 是否匹配"""
    print(f"\n{'=' * 60}")
    print("🔍 全量检查：Token 与用户 ID 不匹配的情况")
    print('=' * 60)
    
    users = db.query(User).all()
    mismatches = []
    
    for user in users:
        if not user.token:
            continue
        payload = decode_jwt_payload(user.token)
        if payload:
            token_user_id = payload.get('sub')
            if str(user.id) != str(token_user_id):
                real_owner = db.query(User).filter(User.id == int(token_user_id)).first()
                mismatches.append({
                    "user": user,
                    "token_user_id": token_user_id,
                    "real_owner": real_owner
                })
    
    if mismatches:
        print(f"\n🚨 发现 {len(mismatches)} 个 Token 不匹配的用户:\n")
        for m in mismatches:
            user = m["user"]
            real_owner = m["real_owner"]
            real_owner_name = real_owner.username if real_owner else "[用户已删除]"
            print(f"   用户 {user.username} (ID: {user.id})")
            print(f"   → Token 实际属于: {real_owner_name} (ID: {m['token_user_id']})")
            print(f"   → 这意味着 {user.username} 登录后会显示为 {real_owner_name} ！")
            print()
        return mismatches
    else:
        print("\n✅ 所有用户的 Token 都正确匹配其用户 ID")
        return []


def main():
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 60)
        print("🔐 AstrBook 用户账号交换分析")
        print(f"   运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        if len(sys.argv) >= 3:
            # 分析两个指定用户
            user_a = get_user(db, sys.argv[1])
            user_b = get_user(db, sys.argv[2])
            
            result_a = analyze_user(db, user_a, f"用户 A: {sys.argv[1]}")
            result_b = analyze_user(db, user_b, f"用户 B: {sys.argv[2]}")
            
            # 交叉检查
            print(f"\n{'=' * 60}")
            print("🔄 交叉检查")
            print('=' * 60)
            
            if user_a and user_b:
                # 检查 A 的 token 是否指向 B
                if user_a.token:
                    payload_a = decode_jwt_payload(user_a.token)
                    if payload_a and str(payload_a.get('sub')) == str(user_b.id):
                        print(f"\n🚨 发现问题！用户 A ({user_a.username}) 的 Token 实际指向用户 B ({user_b.username})")
                
                # 检查 B 的 token 是否指向 A
                if user_b.token:
                    payload_b = decode_jwt_payload(user_b.token)
                    if payload_b and str(payload_b.get('sub')) == str(user_a.id):
                        print(f"\n🚨 发现问题！用户 B ({user_b.username}) 的 Token 实际指向用户 A ({user_a.username})")
                
                # 检查 OAuth 是否有交叉
                oauth_a = db.query(OAuthAccount).filter(OAuthAccount.user_id == user_a.id).all()
                oauth_b = db.query(OAuthAccount).filter(OAuthAccount.user_id == user_b.id).all()
                
                for oa in oauth_a:
                    for ob in oauth_b:
                        if oa.provider == ob.provider and oa.provider_user_id == ob.provider_user_id:
                            print(f"\n🚨 发现问题！两个用户绑定了相同的 {oa.provider} 账号: {oa.provider_user_id}")
        
        # 始终执行全量检查
        check_all_token_mismatches(db)
        
        print(f"\n{'=' * 60}")
        print("💡 建议")
        print('=' * 60)
        print("""
如果发现 Token 不匹配的问题，修复方法:

1. 直接在数据库中为受影响用户重新生成 Token:
   
   UPDATE users SET token = '<新生成的token>' WHERE id = <用户ID>;

2. 或者让用户登录后手动刷新 Token（在个人中心页面）

3. 找到问题根因后，需要修复代码防止再次发生
""")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
