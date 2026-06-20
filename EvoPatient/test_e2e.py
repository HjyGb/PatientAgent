"""
End-to-end test script for PatientAgent — no medical knowledge required.

Usage:
    cd d:/Project/PatientAgent/EvoPatient
    python test_e2e.py

This script:
  1. Loads case #3 (respiratory infection — the easiest case to diagnose)
  2. Runs a pre-scripted doctor-patient dialogue
  3. Submits a diagnosis based on what the patient said
  4. Prints the AI evaluation

All questions are pre-written — you just watch it run.
"""

import asyncio
import json
from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)

# ── Pre-scripted medical interview for Case #3 ──
# Case 3: 35yo female, fever 39.2°C, cough with yellow sputum, chest pain when breathing
# This is a classic pneumonia / 急性支气管炎 case.

QUESTIONS = [
    "您好，请问您哪里不舒服？",
    "发烧最高多少度？有几天了？",
    "咳嗽吗？有痰吗？什么颜色？",
    "有没有胸痛或者呼吸困难的感觉？",
    "最近吃了什么药没有？效果怎么样？",
    "以前有没有得过类似的病？对什么药过敏吗？",
]

DIAGNOSIS_SUBMISSION = {
    "primary_diagnosis": "社区获得性肺炎（右侧）",
    "evidence": (
        "患者35岁女性，发热5天，体温最高39.2°C，伴畏寒、咳嗽、"
        "咳黄色脓痰，右侧胸痛，深呼吸时加重。自行服用头孢类抗生素3天效果不佳。"
        "查体：T38.6°C，右肺可闻及湿啰音。实验室检查：白细胞计数升高，中性粒细胞比例增加。"
    ),
    "differential_diagnosis": "急性支气管炎、肺结核、肺栓塞",
    "suggested_tests": "胸部X线片/CT、血常规、C反应蛋白、降钙素原、痰培养+药敏试验",
}


async def run_test():
    print("=" * 60)
    print("  PatientAgent E2E 自动化测试")
    print("  病例 #3 — 呼吸内科：发热、咳嗽、咳痰")
    print("=" * 60)

    # ── Step 1: Load case ──
    print("\n[1/4] 加载病例 #3 ...")
    resp = client.post("/api/v1/cases/3/load")
    if resp.status_code != 200:
        print(f"  ❌ 失败: {resp.status_code} — {resp.text[:200]}")
        return
    data = resp.json()
    session_id = data["session_id"]
    print(f"  ✅ session_id: {session_id[:8]}...")
    print(f"  科室: {data['department']}")
    print(f"  主诉: {data['chief_complaint'][:80]}...")

    # ── Step 2: Run Q&A dialogue ──
    print(f"\n[2/4] 问诊对话 ({len(QUESTIONS)} 轮)...")
    dialogue = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n  --- 第 {i} 轮 ---")
        print(f"  👨‍⚕️ 医生: {q}")

        resp = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"question": q},
        )
        if resp.status_code != 200:
            print(f"  ❌ 回答失败: {resp.text[:200]}")
            break

        ans = resp.json()
        # Truncate for display
        answer_preview = ans["answer"][:100].replace("\n", " ")
        print(f"  🤒 病人: {answer_preview}...")
        if ans.get("scores"):
            s = ans["scores"]
            print(f"  📊 评分: 综合={s['overall']} 相关={s['relevance']} 忠实={s['faithfulness']} 自然={s['robustness']}")
        dialogue.append({"question": q, "answer": ans["answer"]})

    # ── Step 3: Submit diagnosis ──
    print(f"\n[3/4] 提交诊断 ...")
    print(f"  初步诊断: {DIAGNOSIS_SUBMISSION['primary_diagnosis']}")

    resp = client.post(
        f"/api/v1/sessions/{session_id}/diagnosis",
        json=DIAGNOSIS_SUBMISSION,
    )
    if resp.status_code != 200:
        print(f"  ❌ 提交失败: {resp.status_code} — {resp.text[:300]}")
        return
    print(f"  ✅ evaluation_id: {resp.json()['evaluation_id']}")

    # ── Step 4: Get evaluation ──
    print(f"\n[4/4] 获取评估结果 ...")
    resp = client.get(f"/api/v1/sessions/{session_id}/evaluation")
    if resp.status_code != 200:
        print(f"  ❌ 获取失败: {resp.status_code} — {resp.text[:200]}")
        return

    ev = resp.json()
    print("\n" + "=" * 60)
    print("  📊 诊断评估报告")
    print("=" * 60)
    print(f"  综合评分: {ev['overall_score']:.1f} / 5.0")
    print(f"  问诊质量: {ev['consultation_quality']:.1f} / 5.0")
    print(f"  诊断准确性: {ev['diagnosis_accuracy']:.1f} / 5.0")
    print()
    print("  分维度评分:")
    for dim_name, dim_data in ev.get("diagnosis_dimensions", {}).items():
        bar = "█" * int(dim_data["score"]) + "░" * (5 - int(dim_data["score"]))
        print(f"    {dim_name}: {dim_data['score']}/5 {bar}")
    print()
    print(f"  📝 教师评语:")
    comment = ev.get("teacher_comment", "")
    # Wrap at ~60 chars
    for i in range(0, len(comment), 60):
        print(f"    {comment[i:i+60]}")
    print()
    standard = ev.get("standard_diagnosis", "")
    if standard:
        print(f"  🏥 标准诊断参考:")
        for i in range(0, len(standard), 60):
            print(f"    {standard[i:i+60]}")
    print("\n" + "=" * 60)
    print("  ✅ 测试完成！")

    # ── Bonus: Verify history ──
    print(f"\n[Bonus] 验证历史记录持久化 ...")
    resp = client.get("/api/v1/sessions/history")
    if resp.status_code == 200:
        items = resp.json()["items"]
        matching = [s for s in items if s["session_id"] == session_id]
        if matching:
            s = matching[0]
            print(f"  ✅ 会话已持久化: status={s['status']}, turns={s['turn_count']}")
        else:
            print(f"  ⚠️ 未在历史中找到此会话")
    print()

    # Cleanup: end session
    client.post(f"/api/v1/sessions/{session_id}/end")


if __name__ == "__main__":
    asyncio.run(run_test())
