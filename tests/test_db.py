from datetime import UTC, datetime, timedelta, timezone

from app.db import MIGRATIONS, connect, migrate, parse_iso, utc_iso


class TestMigrate:
    def test_aplica_todas_na_primeira_vez(self):
        conn = connect(':memory:')

        assert migrate(conn) == len(MIGRATIONS)

        names = [row['name'] for row in conn.execute('SELECT name FROM schema_migrations ORDER BY name')]
        assert names == [name for name, _ in MIGRATIONS]

    def test_nao_reaplica_na_segunda_vez(self):
        conn = connect(':memory:')
        migrate(conn)

        assert migrate(conn) == 0

    def test_cria_as_tabelas_do_servico(self):
        conn = connect(':memory:')
        migrate(conn)

        tables = {row['name'] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {'processed_events', 'sales', 'products', 'product_views'} <= tables


class TestUtcIso:
    def test_converte_fuso_local_para_utc(self):
        value = datetime(2026, 10, 5, 7, 0, tzinfo=timezone(timedelta(hours=-3)))

        assert utc_iso(value) == '2026-10-05T10:00:00'

    def test_mantem_datetime_sem_fuso_como_esta(self):
        assert utc_iso(datetime(2026, 10, 5, 10, 0)) == '2026-10-05T10:00:00'


class TestParseIso:
    def test_aceita_sufixo_z(self):
        assert parse_iso('2026-10-05T10:00:00.000Z') == datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
