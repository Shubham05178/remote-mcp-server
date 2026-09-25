from fastmcp import FastMCP

# Initialize the server
mcp = FastMCP("My Simple Server")

# Register a tool using the decorator
@mcp.tool
def greet(name: str) -> str:
    """A tool that greets a user by name."""
    return f"Hello, {name}! Welcome to FastMCP."
@mcp.tool
def curse(name:str)->str:
    "A tool to curse a user by name"
    return f"Saale ! Shubham ki {name}"
if __name__=="main":
    mcp.run(transport="http",host="0.0.0.0",port=8000)