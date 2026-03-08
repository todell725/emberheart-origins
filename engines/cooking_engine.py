import logging
from engines.idle_engine import IdleTaskEngine

logger = logging.getLogger("Engine_Cooking")

class CookingEngine(IdleTaskEngine):
    """
    Handles passive cooking, recipe progression, and culinary drops.
    Inherits math, active state management, and loot rolling from IdleTaskEngine.
    """
    def __init__(self, llm_client=None):
        super().__init__("IDLE_COOKING_DB.json", "COOKING_ACTIVE.json")
        self.llm = llm_client
        self.skill_name = "Cooking"

    async def generate_cooking_report(self, task: dict, recipe_count: int, total_xp: int, loot: list, character_class: str, solo: bool = False) -> str:
        """Use LLM to generate flavor text for the culinary success (or chaotic failure) of cooking meals."""
        if not self.llm:
            return self._generic_cooking_report(task, recipe_count, solo)

        # Simplified prompt focusing on culinary mechanics
        prompt = f"""
        Roleplay an omniscient narrator describing a passive cooking session in a D&D 5e fantasy setting.
        The {character_class} has been actively cooking: {task['recipe_name']}.
        Total recipes completed: {recipe_count}
        Loot obtained: {', '.join(loot) if loot else 'None'}
        Solo task: {solo}
        
        Write exactly ONE short, flavorful paragraph (2-3 sentences max).
        Focus on:
        - The sizzle, heat, or aroma of the ingredients.
        - The culinary precision (or minor burns/mistakes) applied.
        - The visual appeal of the final {task['recipe_name']} dishes.
        
        Do NOT mention specific XP numbers or game mechanics. Be highly atmospheric and slightly mouth-watering. 
        """
        
        try:
            response = await self.llm.generate("cooking_narrator", prompt, max_tokens=150)
            return response.strip()
        except Exception as e:
            logger.error(f"Cooking LLM error: {e}")
            return self._generic_cooking_report(task, recipe_count, solo)

    def _generic_cooking_report(self, task: dict, recipe_count: int, solo: bool) -> str:
        """Fallback when LLM is offline or fails."""
        if solo:
            return f"Working alone over the hot flames, you successfully prepared {recipe_count} portions of {task['recipe_name']}. Your hands are singed, but the aroma is divine."
        return f"Working together in the makeshift kitchen, your party managed to cook up {recipe_count} portions of {task['recipe_name']}. The delicious smell drifts through the camp."
