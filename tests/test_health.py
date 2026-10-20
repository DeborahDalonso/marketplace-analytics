from app.main import app


class FakeConsumer:
    def __init__(self, connected: bool) -> None:
        self.connected = connected


class TestGetHealth:
    def test_responde_200_com_sqlite_e_kafka_ok(self, client):
        app.state.consumer = FakeConsumer(connected=True)

        response = client.get('/health')

        assert response.status_code == 200
        assert response.json() == {
            'success': True,
            'message': None,
            'data': {'service': 'marketplace-analytics', 'version': '1.0.0', 'sqlite': 'ok', 'kafka': 'ok'},
        }

    def test_responde_503_quando_kafka_esta_fora(self, client):
        app.state.consumer = FakeConsumer(connected=False)

        response = client.get('/health')

        assert response.status_code == 503
        assert response.json()['data']['kafka'] == 'down'

    def test_responde_503_quando_o_banco_nao_tem_schema(self, client, conn):
        app.state.consumer = FakeConsumer(connected=True)
        conn.execute('DROP TABLE schema_migrations')

        response = client.get('/health')

        assert response.status_code == 503
        assert response.json()['data']['sqlite'] == 'down'
