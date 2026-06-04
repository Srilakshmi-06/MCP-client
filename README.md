#MCP client

MCP servers can provide the functionalities like:
 -Resources: File like data that can be read by client(like API responses or file contents)
 -Tools: Functions that can be called by the LLM(with user approval)
 -Prompts: Pre-written templates that help user accomplish specific tasks

### Requirements
 -Python 1.0 or higher
 -uv as packet manager
 -Python MCP SDK 1.2.0 or higher

### Setting up the environment

 1.Install uv if not available (curl -LsSf http://astral.sh/uv/install.sh | sh)
 2.Initialize the project with uv(uv init)
 3. Add the dependencies uv add mcp anthropic python-dotenv
 4.Create weather.py file which has contents for our MCP server
 5.Run the script with the help of uv run and gla MCP Inspector[uv run weather.py]
 [npx @modelcontextprotocol/inspector -- "uv" "run" "weather.py"]
