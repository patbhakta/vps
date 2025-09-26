Important notes:

Replace your-password-here with a secure password for Neo4j
You may need to adjust the Graphiti image name (graphiti/graphiti:latest) based on the actual Docker image available
The Tailscale state is stored in ./tailscale-neo4j/state to keep it separate from your other services
Neo4j will be accessible on ports 7474 (HTTP) and 7687 (Bolt) through the Tailscale network
Memory settings for Neo4j are configured for moderate usage - adjust based on your VPS resources

Make sure to create the ./tailscale-neo4j/state directory before running the compose file.

Neo4j Configuration:

Authentication credentials
Memory settings (heap and page cache)
Network listeners for Bolt and HTTP protocols
Security settings for procedures and plugins

Graphiti Configuration:

Database connection settings
Logging and API port configuration
Optional OpenAI API key for AI features

Key Security Notes:

Replace your-secure-password-here with a strong password
The password appears in both NEO4J_AUTH and NEO4J_PASSWORD - keep them synchronized
Add your OpenAI API key if Graphiti requires it for AI functionality
Consider using Docker secrets for sensitive values in production

Memory Settings:

Configured for a moderate VPS setup
Adjust heap sizes based on your available RAM
Page cache should be roughly 50% of available memory after heap allocation

Make sure to:

Copy the .env file to the same directory as your docker-compose.yaml
Update all placeholder values with your actual credentials
Set appropriate file permissions: chmod 600 .env