import psycopg
from app.core.config import settings


CONN_STR = settings.DATABASE_URL


def main() -> None:
    if not CONN_STR:
        raise RuntimeError("DATABASE_URL is not set. Add it to your .env file before introspection.")

    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select table_name
                from information_schema.tables
                where table_schema='public' and table_type='BASE TABLE'
                order by table_name
                """
            )
            tables = [r[0] for r in cur.fetchall()]
            print("TABLES:", ", ".join(tables) if tables else "(none)")

            print("--- COLUMNS ---")
            cur.execute(
                """
                select table_name, column_name, data_type, is_nullable, column_default
                from information_schema.columns
                where table_schema='public'
                order by table_name, ordinal_position
                """
            )
            for t, c, dt, n, d in cur.fetchall():
                print(f"{t}.{c} | {dt} | nullable={n} | default={d}")

            print("--- PRIMARY KEYS ---")
            cur.execute(
                """
                select tc.table_name, kcu.column_name
                from information_schema.table_constraints tc
                join information_schema.key_column_usage kcu
                  on tc.constraint_name=kcu.constraint_name
                 and tc.table_schema=kcu.table_schema
                where tc.table_schema='public'
                  and tc.constraint_type='PRIMARY KEY'
                order by tc.table_name, kcu.ordinal_position
                """
            )
            for t, c in cur.fetchall():
                print(f"{t}.{c}")

            print("--- FOREIGN KEYS ---")
            cur.execute(
                """
                select tc.table_name, kcu.column_name,
                       ccu.table_name as foreign_table, ccu.column_name as foreign_column
                from information_schema.table_constraints tc
                join information_schema.key_column_usage kcu
                  on tc.constraint_name=kcu.constraint_name
                 and tc.table_schema=kcu.table_schema
                join information_schema.constraint_column_usage ccu
                  on ccu.constraint_name=tc.constraint_name
                 and ccu.table_schema=tc.table_schema
                where tc.table_schema='public'
                  and tc.constraint_type='FOREIGN KEY'
                order by tc.table_name, kcu.column_name
                """
            )
            for t, c, ft, fc in cur.fetchall():
                print(f"{t}.{c} -> {ft}.{fc}")


if __name__ == "__main__":
    main()
