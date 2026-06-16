# Model Context Protocol (MCP)

## What is MCP?

Model Context Protocol (MCP) enables Cursor to connect to external tools and data sources. Instead of explaining your project structure repeatedly, integrate directly with your tools. Write MCP servers in any language that can print to `stdout` or serve an HTTP endpoint — Python, JavaScript, Go, etc.

### How it works

Cursor supports three transport methods:

| Transport | Execution | Deployment | Users | Auth |
| :--- | :--- | :--- | :--- | :--- |
| `stdio` | Local | Cursor manages | Single user | Manual |
| `SSE` | Local/Remote | Deploy as server | Multiple users | OAuth |
| `Streamable HTTP` | Local/Remote | Deploy as server | Multiple users | OAuth |

Cursor supports MCP Tools, Prompts, Resources, Roots, Elicitation, and the Apps extension (interactive UI views returned by MCP tools).

## Installing MCP servers

### One-click installation
Browse the Cursor Marketplace for official plugins with one-click install. Click "Add to Cursor" on a marketplace entry to install and authenticate with OAuth.

### Using mcp.json
Configure custom MCP servers with a JSON file:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "mcp-server"],
      "env": { "API_KEY": "value" }
    }
  }
}
```

For a Python server use `"command": "python", "args": ["mcp-server.py"]`. For a remote server use a `"url"` plus optional `"headers"`.

### STDIO server configuration fields
- **type** (required): `"stdio"`
- **command** (required): e.g. `"npx"`, `"node"`, `"python"`, `"docker"`
- **args** (optional): array of arguments
- **env** (optional): environment variables
- **envFile** (optional): path to an env file (STDIO only)

### Configuration locations
- Project: `.cursor/mcp.json` for project-specific tools
- Global: `~/.cursor/mcp.json` for tools available everywhere

### Config interpolation
Use variables in `mcp.json`: `${env:NAME}`, `${userHome}`, `${workspaceFolder}`, `${workspaceFolderBasename}`, `${pathSeparator}` and `${/}`.

### Authentication
MCP servers use environment variables for authentication. Cursor supports OAuth for servers that require it, including static OAuth client credentials for providers that don't support dynamic client registration.

## Using MCP in chat

Cursor automatically uses MCP tools listed under Available Tools when relevant, including in Plan Mode. Cursor asks for approval before using MCP tools by default. Use Run Mode to let Cursor use MCP tools without asking; allowlisted tools can be pre-configured in `permissions.json`.

## Security considerations
- Verify the source — only install from trusted developers
- Review permissions
- Limit API keys to minimum required permissions
- Audit code for critical integrations

## FAQ

### How do I debug MCP server issues?
Open the Output panel (Cmd+Shift+U), select "MCP Logs", and check for connection errors.

### Can I temporarily disable an MCP server?
Yes. Settings (Cmd+Shift+J) → Features → Model Context Protocol → toggle the server.
