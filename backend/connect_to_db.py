import os
from pathlib import Path

import boto3
import psycopg2
from dotenv import load_dotenv

# Load backend/.env no matter which directory the script is run from.
# Variables already set in the shell take precedence over the file.
load_dotenv(Path(__file__).with_name(".env"))

REQUIRED_VARS = ["AWS_REGION", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER"]


def require_env(names):
    """Return the values of the named env vars, or exit listing every missing one."""
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise SystemExit(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in backend/.env (see backend/.env.example)."
        )
    return {name: os.environ[name] for name in names}


config = require_env(REQUIRED_VARS)
port = int(config["DB_PORT"])

# IAM database auth: a short-lived token (15 min) signed with your AWS credentials
# is used as the password, so no database password is stored anywhere.
auth_token = boto3.client("rds", region_name=config["AWS_REGION"]).generate_db_auth_token(
    DBHostname=config["DB_HOST"],
    Port=port,
    DBUsername=config["DB_USER"],
    Region=config["AWS_REGION"],
)

conn = None
try:
    conn = psycopg2.connect(
        host=config["DB_HOST"],
        port=port,
        database=config["DB_NAME"],
        user=config["DB_USER"],
        password=auth_token,
        sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(cur.fetchone()[0])
    cur.close()
except Exception as e:
    print(f"Database error: {e}")
    raise
finally:
    if conn:
        conn.close()
