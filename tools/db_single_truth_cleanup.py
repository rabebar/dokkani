import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


CATEGORY_ALIASES = {
    "خضروات وفواكه": "خضار وفواكه",
}


def connect():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(database_url)


def fetch_all(cur, sql, params=None):
    cur.execute(sql, params or ())
    return [dict(row) for row in cur.fetchall()]


def backup(cur):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    path = backup_dir / f"single_truth_cleanup_{stamp}.json"
    payload = {
        "created_at": stamp,
        "categories": fetch_all(cur, "SELECT * FROM categories ORDER BY id"),
        "subcategories": fetch_all(cur, "SELECT * FROM subcategories ORDER BY id"),
        "products": fetch_all(
            cur,
            """
            SELECT id, name, price, unit, category_id, subcategory_id, barcode,
                   image, visible, sort
            FROM products
            ORDER BY id
            """,
        ),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)


def taxonomy_report(cur):
    return {
        "categories": fetch_all(
            cur,
            """
            SELECT c.id, c.name, c.visible, c.sort,
                   COUNT(DISTINCT s.id) AS subcategory_count,
                   COUNT(DISTINCT p.id) AS product_count
            FROM categories c
            LEFT JOIN subcategories s ON s.category_id = c.id
            LEFT JOIN products p ON p.category_id = c.id
            GROUP BY c.id, c.name, c.visible, c.sort
            ORDER BY c.sort, c.id
            """,
        ),
        "duplicate_category_names": fetch_all(
            cur,
            """
            SELECT TRIM(name) AS name, COUNT(*) AS count, array_agg(id ORDER BY id) AS ids
            FROM categories
            GROUP BY TRIM(name)
            HAVING COUNT(*) > 1
            ORDER BY TRIM(name)
            """,
        ),
        "duplicate_subcategory_names": fetch_all(
            cur,
            """
            SELECT category_id, TRIM(name) AS name, COUNT(*) AS count, array_agg(id ORDER BY id) AS ids
            FROM subcategories
            GROUP BY category_id, TRIM(name)
            HAVING COUNT(*) > 1
            ORDER BY category_id, TRIM(name)
            """,
        ),
        "category_aliases_present": fetch_all(
            cur,
            """
            SELECT id, name, visible, sort
            FROM categories
            WHERE name = ANY(%s)
            ORDER BY id
            """,
            (list(set(CATEGORY_ALIASES.keys()) | set(CATEGORY_ALIASES.values())),),
        ),
        "inconsistent_product_taxonomy": fetch_all(
            cur,
            """
            SELECT p.id, p.name, p.category_id AS product_category_id,
                   s.category_id AS subcategory_category_id, p.subcategory_id
            FROM products p
            JOIN subcategories s ON s.id = p.subcategory_id
            WHERE p.category_id IS DISTINCT FROM s.category_id
            ORDER BY p.id
            LIMIT 100
            """,
        ),
        "duplicate_product_barcodes": fetch_all(
            cur,
            """
            SELECT TRIM(barcode) AS barcode, COUNT(*) AS count, array_agg(id ORDER BY id) AS ids
            FROM products
            WHERE barcode IS NOT NULL AND TRIM(barcode) <> ''
            GROUP BY TRIM(barcode)
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, TRIM(barcode)
            LIMIT 100
            """,
        ),
    }


def merge_category(cur, source_id, target_id):
    cur.execute("UPDATE products SET category_id = %s WHERE category_id = %s", (target_id, source_id))
    cur.execute("UPDATE subcategories SET category_id = %s WHERE category_id = %s", (target_id, source_id))
    cur.execute("DELETE FROM categories WHERE id = %s", (source_id,))


def merge_exact_duplicate_categories(cur):
    rows = fetch_all(
        cur,
        """
        SELECT TRIM(name) AS name, array_agg(id ORDER BY id) AS ids
        FROM categories
        GROUP BY TRIM(name)
        HAVING COUNT(*) > 1
        """,
    )
    merges = []
    for row in rows:
        ids = row["ids"]
        target_id = ids[0]
        for source_id in ids[1:]:
            merge_category(cur, source_id, target_id)
            merges.append({"type": "exact_category", "name": row["name"], "from": source_id, "to": target_id})
    return merges


def merge_alias_categories(cur):
    merges = []
    for alias, canonical in CATEGORY_ALIASES.items():
        cur.execute("SELECT id FROM categories WHERE TRIM(name) = TRIM(%s) ORDER BY id", (canonical,))
        target_rows = cur.fetchall()
        cur.execute("SELECT id FROM categories WHERE TRIM(name) = TRIM(%s) ORDER BY id", (alias,))
        source_rows = cur.fetchall()
        if target_rows and source_rows:
            target_id = target_rows[0]["id"]
            for row in source_rows:
                source_id = row["id"]
                if source_id != target_id:
                    merge_category(cur, source_id, target_id)
                    merges.append({"type": "alias_category", "name": alias, "from": source_id, "to": target_id})
        elif source_rows and not target_rows:
            source_id = source_rows[0]["id"]
            cur.execute("UPDATE categories SET name = %s WHERE id = %s", (canonical, source_id))
            merges.append({"type": "rename_category", "from_name": alias, "to_name": canonical, "id": source_id})
    return merges


def merge_duplicate_subcategories(cur):
    rows = fetch_all(
        cur,
        """
        SELECT category_id, TRIM(name) AS name, array_agg(id ORDER BY id) AS ids
        FROM subcategories
        GROUP BY category_id, TRIM(name)
        HAVING COUNT(*) > 1
        """,
    )
    merges = []
    for row in rows:
        ids = row["ids"]
        target_id = ids[0]
        for source_id in ids[1:]:
            cur.execute("UPDATE products SET subcategory_id = %s WHERE subcategory_id = %s", (target_id, source_id))
            cur.execute("DELETE FROM subcategories WHERE id = %s", (source_id,))
            merges.append(
                {
                    "type": "duplicate_subcategory",
                    "category_id": row["category_id"],
                    "name": row["name"],
                    "from": source_id,
                    "to": target_id,
                }
            )
    return merges


def fix_product_category_from_subcategory(cur):
    cur.execute(
        """
        UPDATE products p
        SET category_id = s.category_id
        FROM subcategories s
        WHERE p.subcategory_id = s.id
          AND p.category_id IS DISTINCT FROM s.category_id
        """
    )
    return cur.rowcount


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply cleanup changes. Default is report only.")
    args = parser.parse_args()

    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            before = taxonomy_report(cur)
            if not args.apply:
                conn.rollback()
                print(json.dumps({"mode": "report", "before": before}, ensure_ascii=False, indent=2, default=str))
                return

            backup_path = backup(cur)
            changes = []
            changes.extend(merge_alias_categories(cur))
            changes.extend(merge_exact_duplicate_categories(cur))
            changes.extend(merge_duplicate_subcategories(cur))
            fixed_products = fix_product_category_from_subcategory(cur)
            after = taxonomy_report(cur)
            conn.commit()
            print(
                json.dumps(
                    {
                        "mode": "apply",
                        "backup": backup_path,
                        "changes": changes,
                        "fixed_product_category_from_subcategory": fixed_products,
                        "before": before,
                        "after": after,
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
