import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import auth
from app.dependencies import get_db
from app.main import app

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()


class FakeSigningKey:
    key = PUBLIC_KEY.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


class FakeJwkClient:
    def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
        return FakeSigningKey()


def make_token(role: str = 'seller', **overrides: Any) -> str:
    now = int(time.time())
    claims = {
        'sub': 'usr_seller_1',
        'email': 'ana@example.com',
        'name': 'Ana',
        'role': role,
        'iat': now,
        'exp': now + 3600,
        'iss': 'marketplace-auth',
        **overrides,
    }
    return jwt.encode(claims, PRIVATE_KEY, algorithm='RS256')


@pytest.fixture
def client(conn, monkeypatch):
    # Troca só a busca do JWKS; a validação de assinatura, expiração e issuer é a real
    monkeypatch.setattr(auth, 'jwk_client', lambda url: FakeJwkClient())
    app.dependency_overrides[get_db] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestRequireRole:
    def test_aceita_token_valido_de_vendedor(self, client):
        response = client.get(
            '/reports/sales',
            params={'sellerId': 'usr_seller_1'},
            headers={'Authorization': f'Bearer {make_token()}'},
        )

        assert response.status_code == 200

    def test_responde_401_sem_token(self, client):
        response = client.get('/reports/sales', params={'sellerId': 'usr_seller_1'})

        assert response.status_code == 401
        assert response.json() == {'success': False, 'message': 'Token de acesso não informado', 'errors': []}

    def test_responde_401_com_token_expirado(self, client):
        token = make_token(exp=int(time.time()) - 10)

        response = client.get('/reports/sales', headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 401
        assert response.json()['message'] == 'Token de acesso inválido ou expirado'

    def test_responde_401_com_issuer_errado(self, client):
        token = make_token(iss='outro-servico')

        response = client.get('/reports/sales', headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 401

    def test_responde_401_com_assinatura_de_outra_chave(self, client):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode({'sub': 'x', 'role': 'admin', 'iss': 'marketplace-auth'}, other_key, algorithm='RS256')

        response = client.get('/reports/sales', headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 401

    def test_responde_403_para_comprador(self, client):
        response = client.get('/reports/sales', headers={'Authorization': f'Bearer {make_token("buyer")}'})

        assert response.status_code == 403
        assert response.json()['message'] == 'Perfil sem permissão para este recurso'

    def test_admin_consulta_sem_seller_id(self, client):
        response = client.get('/reports/sales', headers={'Authorization': f'Bearer {make_token("admin")}'})

        assert response.status_code == 200
