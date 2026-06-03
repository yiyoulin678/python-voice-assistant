from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from app.agent.mcp.config import MCPConfig


WINDOWS_MCP_ENABLED_KEY = "WINDOWS_MCP_ENABLED"


@dataclass(frozen=True)
class MCPRuntimeSettings:
    """MCP 运行时开关；Windows 存 system_config，Playwright 存 mcp.yaml。"""

    windows_enabled: bool = False
    playwright_enabled: bool = False


def apply_mcp_runtime_settings(
    config: MCPConfig,
    settings: MCPRuntimeSettings,
) -> MCPConfig:
    """按运行时开关覆盖需要重启加载的 MCP server。"""

    servers = []
    for server in config.servers:
        if server.name == "windows":
            servers.append(replace(server, enabled=settings.windows_enabled))
        elif server.name == "playwright":
            servers.append(replace(server, enabled=settings.playwright_enabled))
        else:
            servers.append(server)
    return replace(config, servers=servers)
