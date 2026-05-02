import uuid
from unittest.mock import MagicMock


def _make_agent(**kwargs):
    a = MagicMock()
    a.id = kwargs.get('id', uuid.uuid4())
    a.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    a.name = kwargs.get('name', 'Service Advisor')
    a.role_tagline = kwargs.get('role_tagline', 'Front desk · Customer intake')
    a.accent_color = kwargs.get('accent_color', '#d97706')
    a.initials = kwargs.get('initials', 'SA')
    a.system_prompt = kwargs.get('system_prompt', 'You are the Service Advisor.')
    a.tools = kwargs.get('tools', [])
    a.sort_order = kwargs.get('sort_order', 0)
    a.persona_name = kwargs.get('persona_name', None)
    return a


def test_list_agents_persona_name_present_in_response(client, auth_headers, mock_db):
    agent = _make_agent(persona_name='Tom')
    # _ensure_seeded checks scalar_one_or_none; list query uses scalars().all()
    mock_db.execute.return_value.scalar_one_or_none.return_value = agent
    mock_db.execute.return_value.scalars.return_value.all.return_value = [agent]
    resp = client.get("/agents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['persona_name'] == 'Tom'


def test_list_agents_persona_name_null_when_unset(client, auth_headers, mock_db):
    agent = _make_agent(persona_name=None)
    mock_db.execute.return_value.scalar_one_or_none.return_value = agent
    mock_db.execute.return_value.scalars.return_value.all.return_value = [agent]
    resp = client.get("/agents", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()[0]['persona_name'] is None


def test_update_agent_persona_name(client, auth_headers, mock_db):
    agent = _make_agent(persona_name=None)
    mock_db.execute.return_value.scalar_one_or_none.return_value = agent
    resp = client.put(
        f"/agents/{agent.id}",
        json={"persona_name": "Maria"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert agent.persona_name == "Maria"
