c = get_config()  # noqa: F821

c.MCPExtensionApp.mcp_name = "Jupyter MCP Server"
c.MCPExtensionApp.mcp_port = 3002

c.MCPExtensionApp.mcp_tools = [
    "jupyter_ai_tools.toolkits.notebook:read_notebook",
    "jupyter_ai_tools.toolkits.notebook:read_notebook_cells",
    "jupyter_ai_tools.toolkits.notebook:read_notebook_json",
    "jupyter_ai_tools.toolkits.notebook:read_cell",
    "jupyter_ai_tools.toolkits.notebook:read_cell_json",
    "jupyter_ai_tools.toolkits.notebook:create_notebook",
    "jupyter_ai_tools.toolkits.notebook:add_cell",
    "jupyter_ai_tools.toolkits.notebook:edit_cell",
    "jupyter_ai_tools.toolkits.notebook:delete_cell",
    "jupyter_ai_tools.toolkits.notebook:list_available_kernelspecs",
]
