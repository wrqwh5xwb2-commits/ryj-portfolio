import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.dataset import TEST, TRAIN
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as value:
        yield value


def test_training_and_test_sentences_are_disjoint():
    train = {x for rows in TRAIN.values() for x in rows}
    test = {x for rows in TEST.values() for x in rows}
    assert train.isdisjoint(test)


def test_question_has_verifiable_citation(client):
    result = client.post("/api/questions", json={"text": "退款验收通过后多久能到账"}).json()
    assert result["supported"]
    assert result["sources"][0]["id"] == "refund-time"
    assert result["sources"][0]["content"] in result["answer"]
    assert result["prediction"]["category"] == "退货退款"
    assert client.get("/api/overview").json()["questions"] == 1


def test_unrelated_question_abstains(client):
    result = client.post("/api/questions", json={"text": "明天天气怎么样"}).json()
    assert not result["supported"]
    assert "人工" in result["answer"]


@pytest.mark.parametrize("text", ["", " ", "a", "问" * 2001])
def test_invalid_questions_rejected(client, text):
    assert client.post("/api/questions", json={"text": text}).status_code == 422


def test_import_reindexes_and_rejects_duplicate(client):
    doc = {"title": "会员积分兑换规范", "category": "支付订单", "content": "会员积分兑换规则：每100积分兑换1元优惠券，每天最多兑换10张。积分有效期为12个月。"}
    response = client.post("/api/documents", json=doc)
    assert response.status_code == 201
    result = client.post("/api/questions", json={"text": "会员积分兑换比例是多少"}).json()
    assert result["sources"][0]["id"] == response.json()["id"]
    assert "100积分" in result["answer"]
    assert client.post("/api/documents", json=doc).status_code == 409
    assert client.get("/api/overview").json()["documents"] == 13


def test_ticket_state_machine_and_audit(client):
    ticket = {"title": "重复扣款核实", "content": "银行卡对同一个订单重复扣款了", "category": "支付订单", "priority": "高"}
    ident = client.post("/api/tickets", json=ticket).json()["id"]
    assert client.patch(f"/api/tickets/{ident}", json={"status": "已关闭", "note": "跳过处理"}).status_code == 409
    for status, note in [("处理中", "已核对两笔流水"), ("已关闭", "已退回重复金额"), ("待处理", "用户反馈未到账")]:
        assert client.patch(f"/api/tickets/{ident}", json={"status": status, "note": note}).status_code == 200
    result = client.get("/api/tickets").json()[0]
    assert len(result["events"]) == 4
    assert result["events"][-1]["note"] == "用户反馈未到账"
    assert result["status"] == "待处理"


def test_feedback_updates_instead_of_duplicate(client):
    ident = client.post("/api/questions", json={"text": "发票怎么申请"}).json()["id"]
    for feedback in ("helpful", "unhelpful"):
        assert client.post(f"/api/questions/{ident}/feedback", json={"value": feedback}).status_code == 200
    assert client.get("/api/overview").json()["feedback"] == {"unhelpful": 1}
    assert client.post("/api/questions/999/feedback", json={"value": "helpful"}).status_code == 404


def test_records_survive_restart(tmp_path):
    path = tmp_path / "persist.db"
    with TestClient(create_app(path)) as first:
        first.post("/api/questions", json={"text": "保修期限多久"})
    with TestClient(create_app(path)) as second:
        assert second.get("/api/overview").json()["questions"] == 1
        assert second.get("/api/overview").json()["documents"] == 12


def test_cross_site_write_blocked(client):
    assert client.post("/api/questions", json={"text": "退款到账"}, headers={"Origin": "https://other.example"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "other.example"}).status_code == 403


def test_evaluation_does_not_pollute_business_data(client):
    before = client.get("/api/overview").json()
    report = client.post("/api/evaluation").json()
    assert report["counts"]["classification_test"] == 24
    assert len(report["retrieval"]) == 3
    assert report["classification"]["macro_f1"] >= .65
    assert before == client.get("/api/overview").json()


def test_parallel_import_is_consistent(client):
    docs = [{"title": f"专用规范{i}", "category": "商品保修", "content": f"专用设备{i}服务规则：所有设备须在维修前提交检测申请和有效的购买凭证。"} for i in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda doc: client.post("/api/documents", json=doc), docs))
    assert all(r.status_code == 201 for r in responses)
    assert client.get("/api/overview").json()["documents"] == 16


def test_html_payload_is_plain_data(client):
    content = "<script>alert('xss')</script>这是用于确认内容只作为文字保存的测试规范。"
    result = client.post("/api/documents", json={"title": "脚本测试规范", "category": "账户安全", "content": content})
    assert result.status_code == 201
    assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]
    assert any(d["content"] == content for d in client.get("/api/documents").json())


def test_static_assets_have_browser_compatible_types(client):
    assert client.get("/static/app.js").headers["content-type"].startswith("text/javascript")
    assert client.get("/static/style.css").headers["content-type"].startswith("text/css")
