"""Usuarios: las tablas de Better Auth (frontend/lib/auth.ts)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-23

Generadas con `npx @better-auth/cli generate` (better-auth 1.7.12, plugin admin) y copiadas
tal cual: Better Auth es dueño del esquema, alembic sólo lo crea junto con el resto para que
un deploy tenga un solo paso de migración. Si se actualiza better-auth, regenerar y comparar.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""create table "user" ("id" text not null primary key, "name" text not null, "email" text not null unique, "emailVerified" boolean not null, "image" text, "createdAt" timestamptz default CURRENT_TIMESTAMP not null, "updatedAt" timestamptz default CURRENT_TIMESTAMP not null, "role" text, "banned" boolean, "banReason" text, "banExpires" timestamptz)""")
    op.execute("""create table "session" ("id" text not null primary key, "expiresAt" timestamptz not null, "token" text not null unique, "createdAt" timestamptz default CURRENT_TIMESTAMP not null, "updatedAt" timestamptz not null, "ipAddress" text, "userAgent" text, "userId" text not null references "user" ("id") on delete cascade, "impersonatedBy" text)""")
    op.execute("""create table "account" ("id" text not null primary key, "accountId" text not null, "providerId" text not null, "userId" text not null references "user" ("id") on delete cascade, "accessToken" text, "refreshToken" text, "idToken" text, "accessTokenExpiresAt" timestamptz, "refreshTokenExpiresAt" timestamptz, "scope" text, "password" text, "createdAt" timestamptz default CURRENT_TIMESTAMP not null, "updatedAt" timestamptz not null)""")
    op.execute("""create table "verification" ("id" text not null primary key, "identifier" text not null, "value" text not null, "expiresAt" timestamptz not null, "createdAt" timestamptz default CURRENT_TIMESTAMP not null, "updatedAt" timestamptz default CURRENT_TIMESTAMP not null)""")
    op.execute("""create index "session_userId_idx" on "session" ("userId")""")
    op.execute("""create index "account_userId_idx" on "account" ("userId")""")
    op.execute("""create index "verification_identifier_idx" on "verification" ("identifier")""")


def downgrade() -> None:
    for tabla in ("verification", "account", "session", "user"):
        op.execute(f'DROP TABLE "{tabla}"')
