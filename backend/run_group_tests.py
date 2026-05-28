import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest

pytest.main([__file__ + "/../tests/test_ssh_group.py", "-v"])

from pathlib import Path
from unittest.mock import patch

from app.services.ssh_account_service import SSHAccountService
from app.models.ssh_account import SSHAccountCreate, SSHAccountUpdate, AccountGroup


def run_service_tests():
    print("\n" + "=" * 60)
    print("  SSH Group 功能测试")
    print("=" * 60)

    import tempfile
    tmp = Path(tempfile.mkdtemp())
    accounts_json = tmp / "accounts.json"

    with patch("app.services.ssh_account_service._PERSIST_DIR", tmp), \
         patch("app.services.ssh_account_service._PERSIST_PATH", accounts_json):
        svc = SSHAccountService()
        passed = 0
        failed = 0

        def check(name, condition, detail=""):
            nonlocal passed, failed
            if condition:
                passed += 1
                print(f"  [PASS] {name}")
            else:
                failed += 1
                print(f"  [FAIL] {name} - {detail}")

        # 1. 创建分组
        g = svc.create_group("生产环境")
        check("创建分组", g.name == "生产环境" and g.accounts == [])

        # 2. 重复创建分组
        try:
            svc.create_group("生产环境")
            check("重复创建分组应报错", False, "未抛出异常")
        except ValueError:
            check("重复创建分组应报错", True)

        # 3. 列出分组
        svc.create_group("测试环境")
        groups = svc.list_groups()
        check("列出分组", len(groups) == 2)

        # 4. 创建账户自动创建分组
        acc = svc.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="开发环境"
        ))
        check("创建账户自动创建分组", acc.group == "开发环境")
        dev_group = next((g for g in svc.list_groups() if g.name == "开发环境"), None)
        check("新分组包含该账户", dev_group is not None and "srv1" in dev_group.accounts)

        # 5. 创建账户加入已有分组
        acc2 = svc.create_account(SSHAccountCreate(
            alias="srv2", host="192.168.1.2", username="root", group="生产环境"
        ))
        prod_group = next(g for g in svc.list_groups() if g.name == "生产环境")
        check("加入已有分组", "srv2" in prod_group.accounts)

        # 6. 更新账户分组 - 从旧组移到新组
        svc.update_account("srv1", SSHAccountUpdate(group="生产环境"))
        acc1_updated = svc.get_account("srv1")
        check("更新账户分组-字段变更", acc1_updated.group == "生产环境")
        groups_after = svc.list_groups()
        dev_g = next((g for g in groups_after if g.name == "开发环境"), None)
        prod_g = next(g for g in groups_after if g.name == "生产环境")
        check("更新账户分组-从旧组移出", dev_g is None or "srv1" not in dev_g.accounts)
        check("更新账户分组-加入新组", "srv1" in prod_g.accounts)

        # 7. 更新账户移除分组
        svc.update_account("srv2", SSHAccountUpdate(group=None))
        acc2_updated = svc.get_account("srv2")
        check("移除账户分组", acc2_updated.group is None)
        prod_g2 = next(g for g in svc.list_groups() if g.name == "生产环境")
        check("从分组列表中移除", "srv2" not in prod_g2.accounts)

        # 8. 重命名分组
        svc.update_group("生产环境", new_name="生产集群")
        groups_renamed = svc.list_groups()
        check("重命名分组", any(g.name == "生产集群" for g in groups_renamed))
        acc1_renamed = svc.get_account("srv1")
        check("重命名后账户group同步", acc1_renamed.group == "生产集群")

        # 9. 更新分组的账户列表
        svc.update_group("测试环境", accounts=["srv2"])
        acc2_in_group = svc.get_account("srv2")
        check("通过分组添加账户", acc2_in_group.group == "测试环境")

        # 10. 删除分组 - 清除账户group字段
        svc.create_account(SSHAccountCreate(
            alias="srv3", host="192.168.1.3", username="root", group="测试环境"
        ))
        svc.delete_group("测试环境")
        acc2_after = svc.get_account("srv2")
        acc3_after = svc.get_account("srv3")
        check("删除分组-清除账户group", acc2_after.group is None and acc3_after.group is None)

        # 11. 删除账户从分组中移除
        svc.create_group("临时组")
        svc.create_account(SSHAccountCreate(
            alias="srv4", host="192.168.1.4", username="root", group="临时组"
        ))
        svc.delete_account("srv4")
        tmp_group = next((g for g in svc.list_groups() if g.name == "临时组"), None)
        check("删除账户-从分组列表移除", tmp_group is None or "srv4" not in tmp_group.accounts)

        print("\n" + "-" * 60)
        total = passed + failed
        print(f"  结果: {passed}/{total} 通过", end="")
        if failed:
            print(f", {failed} 失败 ❌")
        else:
            print(" ✅")
        print("-" * 60)

        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

        return failed == 0


if __name__ == "__main__":
    success = run_service_tests()
    sys.exit(0 if success else 1)
