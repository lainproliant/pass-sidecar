# --------------------------------------------------------------------
# agent.py
#
# Author: Lain Musgrove (lain.musgrove@hearst.com)
# Date: Monday September 25, 2023
# --------------------------------------------------------------------

import asyncio
import functools
import os
from dataclasses import dataclass

from pathlib import Path
from dataclass_wizard import YAMLWizard

from bivalve.agent import BivalveAgent
from bivalve.aio import Connection
from bivalve.logging import LogManager
from xeno.shell import check

# --------------------------------------------------------------------
log = LogManager().get(__name__)


# --------------------------------------------------------------------
def env(key: str) -> str:
    if key not in os.environ:
        raise ValueError("Environment variable is undefined: " + key)
    return os.environ[key]


# --------------------------------------------------------------------
@dataclass
class Config(YAMLWizard):
    repo: str
    path: str
    secrets: list[str]


# --------------------------------------------------------------------
class PassSecretVault:
    def __init__(self, config: Config):
        self.config = config
        path = Path(self.config.path)

        if not path.exists():
            check(["git", "clone", config.repo, path.absolute()])

    def get_secret(self, name) -> str:
        return check(["pass", name])


# --------------------------------------------------------------------
def require_auth(f, *params):
    @functools.wraps(f)
    def wrapper(self, conn: Connection, auth_token, *argv):
        session = self.sessions.get(conn.id)
        if auth_token not in self.auth_tokens:
            raise RuntimeError("Not authenticated.")
        return f(conn, *params)


# --------------------------------------------------------------------
class SidecarAgent(BivalveAgent):
    def __init__(self):
        self.auth_tokens: set[str] = set()
        self.config = Config.from_yaml_file("config.yaml")

    async def run(self):
        try:
            await self.serve(host="0.0.0.0", port="8510")
        except Exception:
            log.exception("Failed to start server.")
            self.shutdown()
        await super().run()

    @require_auth
    def fn_get_secret(self, conn: Connection, secret_name: str):
        return self.vault.get_secret(secret_name)


# --------------------------------------------------------------------
async def main():
    agent = SidecarAgent()
    await agent.run()


# --------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
