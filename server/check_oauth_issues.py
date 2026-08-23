#!/usr/bin/env python3
"""
OAuth 账号安全检查脚本

检查以下问题：
1. 空的 provider_user_id（可能导致用户登录到其他人账号）
2. 重复的 provider + provider_user_id 组合
3. 孤立的 OAuth 记录（关联的用户不存在）

使用方法:
    cd server
    python check_oauth_issues.py
"""

import sys
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, ".")

from sqlalchemy import func, or_
from app.database import SessionLocal, engine
from app.models import User, OAuthAccount


def check_empty_provider_ids(db):
    """检查空的 provider_user_id"""
    print("\n" + "=" * 60)
    print("🔍 检查 1: 空的 provider_user_id")
    print("=" * 60)
    
    empty_records = db.query(OAuthAccount).filter(
        or_(
            OAuthAccount.provider_user_id == "",
            OAuthAccount.provider_user_id == None
        )
    ).all()
    
    if empty_records:
        print(f"\n⚠️  发现 {len(empty_records)} 条空 ID 记录（严重问题！）:\n")
        for record in empty_records:
            user = db.query(User).filter(User.id == record.user_id).first()
            username = user.username if user else "[用户已删除]"
            print(f"  - OAuth ID: {record.id}")
            print(f"    Provider: {record.provider}")
            print(f"    Provider User ID: '{record.provider_user_id}' (空!)")
            print(f"    关联用户: {username} (ID: {record.user_id})")
            print(f"    创建时间: {record.created_at}")
            print()
        return len(empty_records)
    else:
        print("\n✅ 未发现空的 provider_user_id，正常。")
        return 0


def check_duplicate_provider_ids(db):
    """检查重复的 provider + provider_user_id 组合"""
    print("\n" + "=" * 60)
    print("🔍 检查 2: 重复的 OAuth 绑定")
    print("=" * 60)
    
    # 查找重复组合
    duplicates = db.query(
        OAuthAccount.provider,
        OAuthAccount.provider_user_id,
        func.count(OAuthAccount.id).label("count")
    ).group_by(
        OAuthAccount.provider,
        OAuthAccount.provider_user_id
    ).having(
        func.count(OAuthAccount.id) > 1
    ).all()
    
    total_issues = 0
    
    if duplicates:
        print(f"\n⚠️  发现 {len(duplicates)} 组重复绑定:\n")
        for dup in duplicates:
            provider, provider_user_id, count = dup
            print(f"  Provider: {provider}, Provider User ID: {provider_user_id}")
            print(f"  重复次数: {count}")
            
            # 获取详细信息
            records = db.query(OAuthAccount).filter(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id
            ).all()
            
            for record in records:
                user = db.query(User).filter(User.id == record.user_id).first()
                username = user.username if user else "[用户已删除]"
                print(f"    - OAuth ID: {record.id}, 用户: {username} (ID: {record.user_id}), 创建: {record.created_at}")
            print()
            total_issues += count
        return total_issues
    else:
        print("\n✅ 未发现重复的 OAuth 绑定，正常。")
        return 0


def check_orphan_oauth_records(db):
    """检查孤立的 OAuth 记录（用户已删除但 OAuth 记录还在）"""
    print("\n" + "=" * 60)
    print("🔍 检查 3: 孤立的 OAuth 记录")
    print("=" * 60)
    
    # 查找关联用户不存在的记录
    orphans = db.query(OAuthAccount).outerjoin(
        User, OAuthAccount.user_id == User.id
    ).filter(User.id == None).all()
    
    if orphans:
        print(f"\n⚠️  发现 {len(orphans)} 条孤立记录:\n")
        for record in orphans:
            print(f"  - OAuth ID: {record.id}")
            print(f"    Provider: {record.provider}")
            print(f"    Provider User ID: {record.provider_user_id}")
            print(f"    原用户 ID: {record.user_id} (用户已不存在)")
            print(f"    创建时间: {record.created_at}")
            print()
        return len(orphans)
    else:
        print("\n✅ 未发现孤立的 OAuth 记录，正常。")
        return 0


def check_users_without_login_method(db):
    """检查没有任何登录方式的用户"""
    print("\n" + "=" * 60)
    print("🔍 检查 4: 无法登录的用户")
    print("=" * 60)
    
    # 找出没有密码且没有 OAuth 绑定的用户
    users_without_password = db.query(User).filter(
        or_(User.password_hash == None, User.password_hash == "")
    ).all()
    
    issues = []
    for user in users_without_password:
        oauth_count = db.query(func.count(OAuthAccount.id)).filter(
            OAuthAccount.user_id == user.id
        ).scalar()
        
        if oauth_count == 0:
            issues.append(user)
    
    if issues:
        print(f"\n⚠️  发现 {len(issues)} 个无法登录的用户（无密码且无 OAuth 绑定）:\n")
        for user in issues:
            print(f"  - 用户 ID: {user.id}")
            print(f"    用户名: {user.username}")
            print(f"    昵称: {user.nickname}")
            print(f"    创建时间: {user.created_at}")
            print()
        return len(issues)
    else:
        print("\n✅ 所有用户都有至少一种登录方式，正常。")
        return 0


def print_statistics(db):
    """打印统计信息"""
    print("\n" + "=" * 60)
    print("📊 统计信息")
    print("=" * 60)
    
    total_users = db.query(func.count(User.id)).scalar()
    total_oauth = db.query(func.count(OAuthAccount.id)).scalar()
    
    github_count = db.query(func.count(OAuthAccount.id)).filter(
        OAuthAccount.provider == "github"
    ).scalar()
    
    linuxdo_count = db.query(func.count(OAuthAccount.id)).filter(
        OAuthAccount.provider == "linuxdo"
    ).scalar()
    
    users_with_password = db.query(func.count(User.id)).filter(
        User.password_hash != None,
        User.password_hash != ""
    ).scalar()
    
    print(f"\n  总用户数: {total_users}")
    print(f"  OAuth 绑定总数: {total_oauth}")
    print(f"    - GitHub: {github_count}")
    print(f"    - LinuxDo: {linuxdo_count}")
    print(f"  设置了密码的用户: {users_with_password}")
    print()


def main():
    print("\n" + "=" * 60)
    print("🔐 AstrBook OAuth 账号安全检查")
    print(f"   运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 打印统计信息
        print_statistics(db)
        
        # 运行所有检查
        issues = 0
        issues += check_empty_provider_ids(db)
        issues += check_duplicate_provider_ids(db)
        issues += check_orphan_oauth_records(db)
        issues += check_users_without_login_method(db)
        
        # 总结
        print("\n" + "=" * 60)
        print("📋 检查总结")
        print("=" * 60)
        
        if issues > 0:
            print(f"\n❌ 发现 {issues} 个问题需要处理！")
            print("\n建议操作:")
            print("  1. 空 provider_user_id: 联系用户让其重新绑定 OAuth")
            print("  2. 重复绑定: 保留最早的记录，删除其他")
            print("  3. 孤立记录: 可以安全删除")
            print("  4. 无法登录的用户: 联系用户或标记为无效账号")
        else:
            print("\n✅ 所有检查通过，未发现问题！")
        
        print()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
