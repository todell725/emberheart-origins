"""
EmberHeart: Origins — Main Entry Point

Forked from Claudes-EmberHeart and rethemed for the golden-age
kingdom-building campaign under Kaelrath Emberhide.

Combines:
- Flame Chronicler (RAG), Router, Parser for intelligent NPC dialogue
- Quest/Shop/Slayer engines, Cogs, and full character system

This is the complete integration.
"""
import os
import sys
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from bot.client_unified import EmberHeartBotUnified

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emberheart_unified.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from environment"""
    load_dotenv()

    # Required settings
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        raise ValueError("DISCORD_TOKEN not set in .env file")

    config = {
        # Discord
        'discord_token': discord_token,
        'guild_id': os.getenv('GUILD_ID'),
        'command_prefix': os.getenv('COMMAND_PREFIX', '!'),

        # Channels
        'channel_ids': {
            'council_chambers': int(os.getenv('COUNCIL_CHAMBERS_CHANNEL_ID') or 0) or None,
            'off_topic': int(os.getenv('OFF_TOPIC_CHANNEL_ID') or 0) or None,
            'kingdom_herald': int(os.getenv('KINGDOM_HERALD_CHANNEL_ID') or 0) or None,
            'quest_log': int(os.getenv('QUEST_LOG_CHANNEL_ID') or 0) or None,
            'hearth': int(os.getenv('HEARTH_CHANNEL_ID') or 0) or None,
            'whispers': int(os.getenv('WHISPERS_CHANNEL_ID') or 0) or None,
        },

        # Ollama
        'ollama_url': os.getenv('OLLAMA_URL', 'http://localhost:11434'),
        'default_model': os.getenv('DEFAULT_MODEL', 'llama3.1'),
        'temperature': float(os.getenv('TEMPERATURE', '0.7')),

        # Paths
        'character_dir': os.getenv('CHARACTER_DIR', 'characters'),

        # Debugging
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',
    }

    return config


async def main():
    """Main application entry point"""
    logger.info("=" * 60)
    logger.info("EmberHeart: Origins — Kingdom of the Flamekeeper")
    logger.info("=" * 60)
    logger.info("Features:")
    logger.info("  - NPC Council Dialogue with RAG (Chronicle)")
    logger.info("  - Quest/Shop/Slayer Systems")
    logger.info("  - Commands (!quest, !slayer, !shop)")
    logger.info("  - 43+ Characters (JSON profiles)")
    logger.info("=" * 60)

    # Load configuration
    try:
        config = load_config()
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Set debug logging if enabled
    if config['debug']:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")

    # Initialize unified bot
    bot = EmberHeartBotUnified(config)

    # Run bot
    try:
        logger.info("Starting unified Discord bot...")
        await bot.start(config['discord_token'])
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
    finally:
        await bot.close()
        logger.info("Bot shut down")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
