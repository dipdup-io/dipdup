from headmcp import HeadMCP

def get_indexer_state():
    # Initialize Head MCP client
    head_mcp = HeadMCP()
    
    # Fetch the current indexer state
    indexer_state = head_mcp.get_indexer_state()
    
    return indexer_state

def main():
    try:
        state = get_indexer_state()
        print(f"Current Indexer State: {state}")
    except Exception as e:
        print(f"Error fetching indexer state: {e}")

if __name__ == "__main__":
    main() 