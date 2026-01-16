#!/usr/bin/env python3
import argparse
import asyncio
import subprocess
import sys


async def create_invite_code() -> None:
    from core.database import async_session, engine
    from models.models import Base
    from services.invite_service import InviteService

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as db:
            service = InviteService(db)
            invite = await service.create_invite_code()
            print(f"Created invite code: {invite.code}")
    finally:
        await engine.dispose()


async def list_users() -> None:
    from sqlalchemy import select

    from core.database import async_session, engine
    from models.models import Base, User

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as db:
            result = await db.execute(select(User).order_by(User.id))
            users = result.scalars().all()

            if not users:
                print("No users found.")
                return

            print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Created'}")
            print("-" * 75)
            for user in users:
                created = user.created_at.strftime("%Y-%m-%d %H:%M")
                print(f"{user.id:<5} {user.username:<20} {user.email:<30} {created}")
    finally:
        await engine.dispose()


def run_in_container(container: str, command: str) -> int:
    docker_cmd = ["docker", "exec", container, "python", "cli.py", command]
    result = subprocess.run(docker_cmd)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="tastie administration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--container",
        metavar="NAME",
        help="Run command inside Docker container (default: tastie)",
        nargs="?",
        const="tastie",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.add_parser("create-invite", help="Create a new invite code")
    subparsers.add_parser("list-users", help="List all users")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.container:
        sys.exit(run_in_container(args.container, args.command))

    if args.command == "create-invite":
        asyncio.run(create_invite_code())
    elif args.command == "list-users":
        asyncio.run(list_users())
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
