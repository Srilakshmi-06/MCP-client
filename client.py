import asyncio
import json
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from groq import Groq

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        self.groq = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.stdio = None
        self.write = None

    async def connect_to_server(self, server_script_path: str):
        """
        Connect to MCP server.
        """

        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")

        if not (is_python or is_js):
            raise ValueError(
                "Server script must be a .py or .js file"
            )

        command = sys.executable if is_python else "node"

        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        response = await self.session.list_tools()

        print(
            "\nConnected to server with tools:",
            [tool.name for tool in response.tools],
        )

    async def process_query(self, query: str) -> str:
        """
        Process query using Groq + MCP tools.
        """

        if self.session is None:
            raise RuntimeError(
                "Not connected to an MCP server."
            )

        tool_response = await self.session.list_tools()

        available_tools = []

        for tool in tool_response.tools:
            available_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
            )

        messages = [
            {
                "role": "user",
                "content": query,
            }
        ]

        while True:

            response = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=available_tools,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            # No tool calls -> final answer
            if not assistant_message.tool_calls:
                return assistant_message.content

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                }
            )

            for tool_call in assistant_message.tool_calls:

                tool_name = tool_call.function.name
                tool_args = json.loads(
                    tool_call.function.arguments
                )

                print(
                    f"\nCalling tool: {tool_name}"
                )

                result = await self.session.call_tool(
                    tool_name,
                    tool_args,
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result.content),
                    }
                )

    async def chat_loop(self):
        """
        Interactive chat loop.
        """

        print("\nMCP Client Started!")
        print(
            "Type your query or 'quit' to exit."
        )

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(
                    query
                )

                print("\nAssistant:")
                print(response)

            except Exception as e:
                print(f"\nError: {e}")

    async def cleanup(self):
        """
        Cleanup resources.
        """

        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python client.py <path_to_server_script>"
        )
        sys.exit(1)

    client = MCPClient()

    try:
        await client.connect_to_server(
            sys.argv[1]
        )

        await client.chat_loop()

    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())