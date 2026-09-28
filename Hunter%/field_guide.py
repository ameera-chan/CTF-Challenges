import os
import sqlite3
import tempfile
from functools import lru_cache
from pathlib import Path

from graphql import (
    GraphQLArgument,
    GraphQLField,
    GraphQLFloat,
    GraphQLInt,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
)


TROPHY_QUERY = "getTrophy"
TROPHY_TYPE = "TrophyBoar0x000141a0"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("HUNTER_DB_PATH", str(Path(tempfile.gettempdir()) / "hunter.db")))

PUBLIC_BOARS = [
    {
        "id": 1,
        "Name": "Grugyn",
        "Weight": 135.2,
        "TuskScore": 42,
        "Method": "Camera trap",
        "Location": "Ardennes",
        "Date": "2024-11-03",
    },
    {
        "id": 2,
        "Name": "Ysgithyrwen",
        "Weight": 187.0,
        "TuskScore": 55,
        "Method": "Driven hunt",
        "Location": "Bia\u0142owie\u017ca",
        "Date": "2024-10-17",
    },
    {
        "id": 3,
        "Name": "Twrch",
        "Weight": 201.5,
        "TuskScore": 61,
        "Method": "High seat",
        "Location": "Carpathians",
        "Date": "2024-09-25",
    },
    {
        "id": 4,
        "Name": "Gullinbursti",
        "Weight": 122.8,
        "TuskScore": 38,
        "Method": "Stalked",
        "Location": "Fontainebleau",
        "Date": "2024-12-01",
    },
]


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _build_trophy_name(index):
    adjectives = [
        "Mud",
        "Iron",
        "Thorn",
        "Stone",
        "Ash",
        "Cinder",
        "Night",
        "Bramble",
        "Storm",
        "Ridge",
    ]
    nouns = [
        "Ripper",
        "Tusk",
        "Mauler",
        "Runner",
        "Snout",
        "Razor",
        "Stalker",
        "Grunter",
        "Charger",
        "Howler",
    ]
    return f"{adjectives[(index - 1) % len(adjectives)]} {nouns[(index - 1) % len(nouns)]}"


def _seed_trophy_rows():
    rows = []
    for boar_id in range(1, 51):
        rows.append(
            {
                "id": boar_id,
                "Name": _build_trophy_name(boar_id),
                "Weight": round(180 + boar_id * 2.7, 1),
                "TuskScore": 28 + (boar_id % 34),
                "Method": "Logged by the Lodge",
                "Location": f"Sector-{(boar_id % 7) + 1}",
                "Date": f"2024-12-{((boar_id - 1) % 28) + 1:02d}",
                "Flag": "Flag not here hahahahahaha",
                "token_a1b2c3": "Not here",
                "token_d4e5f6": "Keep digging",
                "token_g7h8i9": "CSUFSEC{fake_flag_hehe}",
            }
        )

    rows[41] = {
        "id": 42,
        "Name": os.getenv("FLAG", "CSUFSEC{2f1d2d60-44a1-47bf-95f4-38e2536ca49c}"),
        "Weight": 999.9,
        "TuskScore": 999,
        "Method": "Classified",
        "Location": "Classified",
        "Date": "2099-01-01",
        "Flag": "Flag not here hahahahahaha",
        "token_a1b2c3": "Not here",
        "token_d4e5f6": "Keep digging",
        "token_g7h8i9": "CSUFSEC{fake_flag_hehe}",
    }
    return rows


def bootstrap_db():
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS common_boars (
                id INTEGER PRIMARY KEY,
                Name TEXT NOT NULL UNIQUE,
                Weight REAL NOT NULL,
                TuskScore INTEGER NOT NULL,
                Method TEXT NOT NULL,
                Location TEXT NOT NULL,
                Date TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trophy_boars (
                id INTEGER PRIMARY KEY,
                Name TEXT NOT NULL,
                Weight REAL NOT NULL,
                TuskScore INTEGER NOT NULL,
                Method TEXT NOT NULL,
                Location TEXT NOT NULL,
                Date TEXT NOT NULL,
                Flag TEXT NOT NULL,
                token_a1b2c3 TEXT NOT NULL,
                token_d4e5f6 TEXT NOT NULL,
                token_g7h8i9 TEXT NOT NULL
            )
            """
        )

        cursor.execute("DELETE FROM common_boars")
        cursor.executemany(
            """
            INSERT INTO common_boars (id, Name, Weight, TuskScore, Method, Location, Date)
            VALUES (:id, :Name, :Weight, :TuskScore, :Method, :Location, :Date)
            """,
            PUBLIC_BOARS,
        )

        cursor.execute("DELETE FROM trophy_boars")
        cursor.executemany(
            """
            INSERT INTO trophy_boars (
                id, Name, Weight, TuskScore, Method, Location, Date,
                Flag, token_a1b2c3, token_d4e5f6, token_g7h8i9
            )
            VALUES (
                :id, :Name, :Weight, :TuskScore, :Method, :Location, :Date,
                :Flag, :token_a1b2c3, :token_d4e5f6, :token_g7h8i9
            )
            """,
            _seed_trophy_rows(),
        )
        connection.commit()


def _boar_fields():
    return {
        "Name": GraphQLField(GraphQLString),
        "Weight": GraphQLField(GraphQLFloat),
        "TuskScore": GraphQLField(GraphQLInt),
        "Method": GraphQLField(GraphQLString),
        "Location": GraphQLField(GraphQLString),
        "Date": GraphQLField(GraphQLString),
    }


def _trophy_fields():
    fields = _boar_fields()
    fields["Flag"] = GraphQLField(GraphQLString)
    fields["token_a1b2c3"] = GraphQLField(GraphQLString)
    fields["token_d4e5f6"] = GraphQLField(GraphQLString)
    fields["token_g7h8i9"] = GraphQLField(GraphQLString)
    return fields


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def _get_boar(_root, _info, name):
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT Name, Weight, TuskScore, Method, Location, Date
            FROM common_boars
            WHERE lower(Name) = lower(?)
            """,
            (name,),
        ).fetchone()
    return _row_to_dict(row)


def _get_trophy_record(_root, _info, boarId):
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT Name, Weight, TuskScore, Method, Location, Date, Flag, token_a1b2c3, token_d4e5f6, token_g7h8i9
            FROM trophy_boars
            WHERE id = ?
            """,
            (boarId,),
        ).fetchone()
    return _row_to_dict(row)


def _hello(_root, _info):
    return "hello"


def _bye(_root, _info):
    return "bye"


def _make_decoy_type(index):
    return GraphQLObjectType(
        name=f"SightingRecord_{index:08d}",
        fields=lambda: {
            "id": GraphQLField(GraphQLInt),
            "timestamp": GraphQLField(GraphQLString),
            "latitude": GraphQLField(GraphQLFloat),
            "longitude": GraphQLField(GraphQLFloat),
            "observer": GraphQLField(GraphQLString),
            "herdSize": GraphQLField(GraphQLInt),
            "weather": GraphQLField(GraphQLString),
            "habitat": GraphQLField(GraphQLString),
            "behavior": GraphQLField(GraphQLString),
            "notes": GraphQLField(GraphQLString),
        },
    )


@lru_cache(maxsize=1)
def build_schema():
    bootstrap_db()
    boar_type = GraphQLObjectType("Boar", _boar_fields)
    trophy_type = GraphQLObjectType(TROPHY_TYPE, _trophy_fields)

    query_type = GraphQLObjectType(
        "Query",
        lambda: {
            "hello": GraphQLField(GraphQLString, resolve=_hello),
            "bye": GraphQLField(GraphQLString, resolve=_bye),
            "boar": GraphQLField(
                boar_type,
                args={
                    "name": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                },
                resolve=_get_boar,
            ),
            TROPHY_QUERY: GraphQLField(
                trophy_type,
                args={"boarId": GraphQLArgument(GraphQLNonNull(GraphQLInt))},
                resolve=_get_trophy_record,
            ),
        },
    )

    decoy_count = int(os.getenv("DECOY_TYPE_COUNT", "50000"))
    decoy_types = [_make_decoy_type(index) for index in range(1, decoy_count + 1)]
    return GraphQLSchema(
        query=query_type,
        types=[boar_type, trophy_type, *decoy_types],
    )
