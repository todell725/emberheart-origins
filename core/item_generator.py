import os
import logging
from pathlib import Path
from core.config import ROOT_DIR

logger = logging.getLogger("ItemGenerator")


async def generate_custom_item_stats(llm_client, item_name: str, item_desc: str = "") -> bool:
    """
    Generates D&D 5e-style stats for a custom item and saves it as a markdown file
    in docs/RAW_DND/Custom_Items/ for the RAG system to index automatically.

    Args:
        llm_client: The OllamaClient instance.
        item_name: The name of the item.
        item_desc: Optional description of the item.

    Returns:
        True if the item was successfully generated and saved, False otherwise.
    """
    try:
        if not llm_client or not llm_client.is_available():
            logger.warning(f"LLM not available. Cannot generate stats for {item_name}.")
            return False

        custom_items_dir = ROOT_DIR / "docs" / "RAW_DND" / "Custom_Items"
        custom_items_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_name = "".join([c for c in item_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
        safe_name = safe_name.replace(" ", "_").replace("__", "_")
        if not safe_name: safe_name = "unknown_item"
        
        file_path = custom_items_dir / f"{safe_name}.md"
        
        # Skip if already exists so we don't bombard the LLM every craft
        if file_path.exists():
            return True

        prompt = f"""You are a D&D 5e game designer. I need a balanced, ready-to-use stat block for a custom item just forged by players in my server.
Do not include conversational text or explanations. Simply output the Markdown document representing the item.

ITEM NAME: {item_name}
CONTEXT/DESC: {item_desc}

Provide:
1. An # H1 header with the item name.
2. Italics detailing item type (Wondrous item, Weapon, Armor), Rarity, and Attunement requirement.
3. A short, flavorful description.
4. Bolded mechanical properties consistent with D&D 5e mechanics (e.g., AC bonus, damage dice, activated abilities specifying action types and save DCs if any).

Format strictly as Markdown."""

        logger.info(f"Generating stats for newly crafted custom item: {item_name}")
        content = llm_client.generate(prompt=prompt, temperature=0.6, max_tokens=300)

        if not content:
            logger.error(f"LLM returned empty generation for {item_name}.")
            return False

        file_path.write_text(content.strip(), encoding='utf-8')
        logger.info(f"Successfully generated and injected {item_name} into RAG at {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate custom item stats for {item_name}: {e}")
        return False
