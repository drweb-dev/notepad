import os
import yaml
import requests

# ==================== 配置区域 ====================
ARGOCD_URL = "https://127.0.0.1"  # 您的 Argo CD 网页访问地址
ARGOCD_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"  # 填入您在网页端生成的 Token
OUTPUT_DIR = "./argocd_complete_backup" # 统一输出总目录

requests.packages.urllib3.disable_warnings()
VERIFY_SSL = False  
# ==================================================

headers = {"Authorization": f"Bearer {ARGOCD_TOKEN}"}

def extract_real_metadata(resource_data, fallback_kind, fallback_name):
    """智能深度解析器：从各种奇怪的嵌套/字符串结构中，榨取出 Kubernetes 原生真实的 Kind 和 Name 属性。"""
    target_dict = None
    if isinstance(resource_data, str):
        try:
            target_dict = yaml.safe_load(resource_data)
        except Exception:
            pass
    elif isinstance(resource_data, dict):
        target_dict = resource_data
        
    if target_dict and isinstance(target_dict, dict):
        real_kind = target_dict.get("kind")
        real_name = target_dict.get("metadata", {}).get("name")
        if not real_name:
            for key, val in target_dict.items():
                if isinstance(val, dict) and "metadata" in val:
                    real_kind = val.get("kind", real_kind)
                    real_name = val.get("metadata", {}).get("name")
                    break
        if real_kind and real_name:
            return str(real_kind), str(real_name)
    return fallback_kind, fallback_name

def save_and_beautify_resource(target_sub_dir, filename_base, data):
    """
    在指定的子目录（desired 或 live）中安全保存并原地美化。
    非标准资产与内嵌美化配置文件将平铺在同一个子目录下。
    """
    try:
        parsed_data = yaml.safe_load(data) if isinstance(data, str) else data
        if not parsed_data:
            return False
            
        # 1. 保存 K8s 清单资产主体（落地时自动执行 YAML 树状结构美化）
        main_filename = f"{filename_base}.yaml"
        main_file_path = os.path.join(target_sub_dir, main_filename)
        with open(main_file_path, "w", encoding="utf-8") as f:
            yaml.dump(parsed_data, f, allow_unicode=True, default_flow_style=False, indent=2, sort_keys=False)
            
        # 2. 🔍 解包内嵌配置并原位美化
        if isinstance(parsed_data, dict) and "data" in parsed_data:
            data_block = parsed_data.get("data", {})
            if isinstance(data_block, dict):
                for inner_file_name, escaped_content in data_block.items():
                    if isinstance(escaped_content, str):
                        try:
                            # 平铺命名规则：原资源名_EMBEDDED_内嵌文件名
                            embedded_filename = f"{filename_base}_EMBEDDED_{inner_file_name}"
                            embedded_path = os.path.join(target_sub_dir, embedded_filename)
                            
                            inner_parsed = yaml.safe_load(escaped_content)
                            
                            with open(embedded_path, "w", encoding="utf-8") as out_f:
                                if isinstance(inner_parsed, dict):
                                    # 如果内嵌是 YAML，输出标准换行和 2 空格缩进
                                    yaml.dump(inner_parsed, out_f, allow_unicode=True, default_flow_style=False, indent=2, sort_keys=False)
                                else:
                                    # 如果内嵌是 properties 文本，还原换行符
                                    cleaned_text = escaped_content.replace("\\n", "\n").replace("\\r", "\r")
                                    out_f.write(cleaned_text)
                                    
                            print(f"       ⚡ [内嵌资产原位美化成功] -> {inner_file_name}")
                        except Exception:
                            pass
        return True
    except Exception:
        pass
    return False

def download_all_manifests():
    apps_url = f"{ARGOCD_URL.rstrip('/')}/api/v1/applications"
    try:
        response = requests.get(apps_url, headers=headers, verify=VERIFY_SSL, timeout=15)
        if response.status_code == 401:
            print("❌ 鉴权失败！请检查您的 Token 是否正确或是否已过期。")
            return
        elif response.status_code != 200:
            print(f"❌ 无法连接，状态码: {response.status_code}")
            return
        
        apps = response.json().get("items", [])
        if not apps:
            print("⚠️ 未发现任何 Application。")
            return
            
        print(f"📦 成功获取到 {len(apps)} 个应用，开始执行【DESIRED / LIVE 分层独立平铺】全量备份...")
        
        for app in apps:
            app_name = app.get("metadata", {}).get("name", "unknown")
            print(f"\n🚀 [正在处理应用]: {app_name}")
            
            # 建立应用根目录
            app_dir = os.path.join(OUTPUT_DIR, app_name)
            
            # 🔴【核心修改】：建立独立的 DESIRED 与 LIVE 平铺子目录
            desired_dir = os.path.join(app_dir, "desired_manifests")
            live_dir = os.path.join(app_dir, "live_manifests")
            os.makedirs(desired_dir, exist_ok=True)
            os.makedirs(live_dir, exist_ok=True)
            
            # 保存 Application 自身的控制配置（放在应用根线下）
            clean_app = {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Application",
                "metadata": {
                    "name": app_name,
                    "namespace": app.get("metadata", {}).get("namespace", "argocd"),
                },
                "spec": app.get("spec", {})
            }
            if "labels" in app.get("metadata", {}):
                clean_app["metadata"]["labels"] = app["metadata"]["labels"]
            
            with open(os.path.join(app_dir, "_application_config.yaml"), "w", encoding="utf-8") as f:
                yaml.dump(clean_app, f, allow_unicode=True, default_flow_style=False, indent=2, sort_keys=False)
            print(f"   📂 [已保存] 应用控制主配置文件 -> _application_config.yaml")
            
            # 2. 拉取清单数据
            manifests_url = f"{ARGOCD_URL.rstrip('/')}/api/v1/applications/{app_name}/manifests"
            try:
                m_res = requests.get(manifests_url, headers=headers, verify=VERIFY_SSL, timeout=20)
                if m_res.status_code != 200:
                    print(f"   ❌ 无法拉取该应用的清单数据，状态码: {m_res.status_code}")
                    continue
                    
                m_data = m_res.json()
                manifest_list = m_data.get("manifests", [])
                
                if not manifest_list:
                    print(f"   ℹ️  该应用当前没有检测到任何下属资源清单。")
                    continue
                
                print(f"   📂 发现 {len(manifest_list)} 个底层资产，正在分类平铺归档并原位美化...")
                
                for idx, resource in enumerate(manifest_list):
                    outer_kind = "UnknownKind"
                    outer_name = f"unknown-name-{idx}"
                    if isinstance(resource, dict):
                        outer_kind = resource.get("kind", outer_kind)
                        outer_name = resource.get("name", outer_name)
                    
                    test_target = resource.get("liveManifest") if isinstance(resource, dict) else resource
                    if not test_target and isinstance(resource, dict):
                        test_target = resource.get("desiredManifest")
                    if not test_target:
                        test_target = resource
                        
                    real_kind, real_name = extract_real_metadata(test_target, outer_kind, outer_name)
                    filename_base = f"{real_kind}_{real_name}".replace("/", "-")
                    
                    # 🟢 A. 处理并平铺到 desired_manifests 目录
                    desired_str = resource.get("desiredManifest") if isinstance(resource, dict) else None
                    desired_success = False
                    if desired_str:
                        desired_success = save_and_beautify_resource(desired_dir, filename_base, desired_str)
                    
                    # 🟢 B. 处理并平铺到 live_manifests 目录
                    live_str = resource.get("liveManifest") if isinstance(resource, dict) else None
                    live_success = False
                    if live_str:
                        live_success = save_and_beautify_resource(live_dir, filename_base, live_str)
                    
                    # 针对非标准资产整体强行落地的兜底
                    if not desired_success and not live_success:
                        raw_filename_base = f"RAW_{filename_base}"
                        save_and_beautify_resource(desired_dir, raw_filename_base, resource)
                        save_and_beautify_resource(live_dir, raw_filename_base, resource)
                        print(f"      ⚠️  [非标准原始资产已平铺归档]: {raw_filename_base}")
                    else:
                        print(f"      ✅ [资产解析并原位美化成功]: {real_kind} / {real_name}")
                    
            except Exception as e:
                print(f"   ❌ 请求应用 {app_name} 的清单详情时发生异常: {e}")

        print(f"\n🎉 完美收官！DESIRED 与 LIVE 已完美实现分流目录独立平铺存储。")
        print(f"📂 全量资产总根目录: {os.path.abspath(OUTPUT_DIR)}")

    except Exception as e:
        print(f"❌ 运行过程中发生全局异常: {e}")

if __name__ == "__main__":
    download_all_manifests()
