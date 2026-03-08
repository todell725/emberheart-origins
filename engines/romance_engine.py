"""
Romance Engine - Natural Relationship Progression
Handles automatic romance metric updates based on gameplay events
"""

from core.relationships import relationship_manager
from core.storage import load_json, save_json
import logging
import random

logger = logging.getLogger("RomanceEngine")


class RomanceEngine:
    """Manages natural romance progression through gameplay events"""

    def __init__(self):
        self.rm = relationship_manager
        self.event_cooldowns = {}  # Prevent spam of same event

    # ========== EVENT TRIGGERS ==========

    def on_combat_victory(self, char1_id: str, char2_id: str, difficulty: str = "normal", kill_count: int = 1):
        """Triggered when two characters fight alongside each other

        Args:
            char1_id: First character ID
            char2_id: Second character ID
            difficulty: Combat difficulty (normal, hard, deadly)
            kill_count: Number of enemies defeated (scales bonding for idle slayer grinding)
        """
        bond_type = self.rm.get_bond_type(char1_id, char2_id)

        # Base bonuses from shared combat
        affection_gain = 2
        trust_gain = 3
        romantic_interest_gain = 0

        # Scale with difficulty
        if difficulty == "hard":
            affection_gain = 4
            trust_gain = 5
            romantic_interest_gain = 3
        elif difficulty == "deadly":
            affection_gain = 6
            trust_gain = 8
            romantic_interest_gain = 5

        # Scale bonding based on kill count (with diminishing returns)
        # Using logarithmic scaling so 1000 kills doesn't give 1000x bonding
        # Formula: multiplier = 1 + log10(kill_count) for kill_count > 1
        if kill_count > 1:
            import math
            # Cap at 1000x scaling (log10(1000) = 3, so max multiplier is 4)
            multiplier = 1 + math.log10(min(kill_count, 1000))
            affection_gain = int(affection_gain * multiplier)
            trust_gain = int(trust_gain * multiplier)
            romantic_interest_gain = int(romantic_interest_gain * multiplier)
            logger.info(f"Combat bonding scaled by {multiplier:.2f}x for {kill_count} kills")

        # Romance interest only for compatible pairs
        if bond_type == "romantic" and romantic_interest_gain > 0:
            self.rm.update_romance_metrics(
                char1_id, char2_id,
                romantic_interest=romantic_interest_gain
            )

        # Everyone gets affection/trust
        self.rm.update_metrics(
            char1_id, char2_id,
            affection=affection_gain,
            trust=trust_gain
        )

        logger.info(f"Combat victory: {char1_id} & {char2_id} (+{affection_gain} aff, +{trust_gain} trust, {kill_count} kills)")

        # Check for automatic confession at high metrics
        self._check_auto_confession(char1_id, char2_id)

    def on_life_saving_rescue(self, rescuer_id: str, rescued_id: str):
        """Triggered when one character saves another's life"""
        bond_type = self.rm.get_bond_type(rescuer_id, rescued_id)

        # MAJOR bonuses for life-saving
        affection_gain = 10
        trust_gain = 15
        intimacy_gain = 8
        romantic_interest_gain = 0

        if bond_type == "romantic":
            romantic_interest_gain = 15  # Big romantic boost!

        self.rm.update_metrics(
            rescuer_id, rescued_id,
            affection=affection_gain,
            trust=trust_gain,
            intimacy=intimacy_gain
        )

        if bond_type == "romantic":
            self.rm.update_romance_metrics(
                rescuer_id, rescued_id,
                romantic_interest=romantic_interest_gain
            )

            # Add rescue event
            rel = self.rm.get_relationship(rescuer_id, rescued_id)
            events = rel.get("events", [])
            if "rescue" not in events:
                events.append("rescue")
                data = self.rm._load_data()
                for r in data.get("relationships", []):
                    if self.rm._match_pair(r, rescuer_id, rescued_id):
                        r["events"] = events
                        break
                self.rm._save_data(data)

        logger.info(f"Life-saving rescue: {rescuer_id} saved {rescued_id} (MAJOR BOND INCREASE)")

        # Very likely to trigger confession
        self._check_auto_confession(rescuer_id, rescued_id, threshold=0.6)

    def on_deep_conversation(self, char1_id: str, char2_id: str, emotional_depth: str = "normal"):
        """Triggered during meaningful dialogue exchanges"""
        bond_type = self.rm.get_bond_type(char1_id, char2_id)

        affection_gain = 3
        trust_gain = 5
        intimacy_gain = 4
        romantic_interest_gain = 0

        # Deeper conversations = stronger bonds
        if emotional_depth == "vulnerable":
            affection_gain = 5
            trust_gain = 8
            intimacy_gain = 7
            if bond_type == "romantic":
                romantic_interest_gain = 5
        elif emotional_depth == "confession":  # Emotional confession, not romantic
            affection_gain = 8
            trust_gain = 12
            intimacy_gain = 10
            if bond_type == "romantic":
                romantic_interest_gain = 8

        self.rm.update_metrics(
            char1_id, char2_id,
            affection=affection_gain,
            trust=trust_gain,
            intimacy=intimacy_gain
        )

        if bond_type == "romantic" and romantic_interest_gain > 0:
            self.rm.update_romance_metrics(
                char1_id, char2_id,
                romantic_interest=romantic_interest_gain
            )

        logger.info(f"Deep conversation: {char1_id} & {char2_id} ({emotional_depth})")

        # Chance to trigger confession
        if emotional_depth in ["vulnerable", "confession"]:
            self._check_auto_confession(char1_id, char2_id, threshold=0.4)

    def on_gift_given(self, giver_id: str, receiver_id: str, gift_quality: str = "common"):
        """Triggered when character gives a gift to another"""
        bond_type = self.rm.get_bond_type(giver_id, receiver_id)

        affection_gain = 2
        romantic_interest_gain = 0

        # Quality matters
        quality_bonuses = {
            "common": (2, 2),
            "uncommon": (3, 4),
            "rare": (5, 6),
            "legendary": (8, 10)
        }

        affection_gain, romantic_boost = quality_bonuses.get(gift_quality, (2, 2))

        self.rm.update_metrics(
            giver_id, receiver_id,
            affection=affection_gain
        )

        if bond_type == "romantic":
            self.rm.update_romance_metrics(
                giver_id, receiver_id,
                romantic_interest=romantic_boost
            )

        logger.info(f"Gift given: {giver_id} → {receiver_id} ({gift_quality})")

    def on_shared_trauma(self, char1_id: str, char2_id: str):
        """Triggered when characters survive traumatic event together"""
        # Trauma bonds people together
        trust_gain = 8
        intimacy_gain = 10
        affection_gain = 5

        self.rm.update_metrics(
            char1_id, char2_id,
            affection=affection_gain,
            trust=trust_gain,
            intimacy=intimacy_gain
        )

        logger.info(f"Shared trauma: {char1_id} & {char2_id} (trauma bonding)")

    def on_betrayal(self, betrayer_id: str, betrayed_id: str, severity: str = "minor"):
        """Triggered when one character betrays another's trust"""
        trust_loss = 10
        tension_gain = 15
        affection_loss = 5
        romantic_interest_loss = 8

        if severity == "major":
            trust_loss = 25
            tension_gain = 30
            affection_loss = 15
            romantic_interest_loss = 20
        elif severity == "catastrophic":
            trust_loss = 50
            tension_gain = 60
            affection_loss = 30
            romantic_interest_loss = 40

        self.rm.update_metrics(
            betrayer_id, betrayed_id,
            affection=-affection_loss,
            trust=-trust_loss,
            tension=tension_gain
        )

        bond_type = self.rm.get_bond_type(betrayer_id, betrayed_id)
        if bond_type == "romantic":
            self.rm.update_romance_metrics(
                betrayer_id, betrayed_id,
                romantic_interest=-romantic_interest_loss,
                commitment=-trust_loss
            )

        logger.info(f"Betrayal: {betrayer_id} betrayed {betrayed_id} ({severity})")

    def on_jealousy_incident(self, jealous_char_id: str, partner_id: str, rival_id: str):
        """Triggered when jealousy occurs in polyamorous situations"""
        # Increase jealousy with partner
        self.rm.update_romance_metrics(
            jealous_char_id, partner_id,
            jealousy=15
        )

        # Tension with rival
        self.rm.update_metrics(
            jealous_char_id, rival_id,
            tension=10
        )

        logger.info(f"Jealousy: {jealous_char_id} jealous of {partner_id}'s attention to {rival_id}")

    def on_quality_time(self, char1_id: str, char2_id: str, activity: str = "casual"):
        """Triggered when characters spend time together"""
        bond_type = self.rm.get_bond_type(char1_id, char2_id)

        affection_gain = 2
        intimacy_gain = 2
        romantic_interest_gain = 0

        # Activity type matters
        if activity == "date":
            affection_gain = 5
            intimacy_gain = 6
            if bond_type == "romantic":
                romantic_interest_gain = 7
        elif activity == "adventure":
            affection_gain = 4
            intimacy_gain = 3
            if bond_type == "romantic":
                romantic_interest_gain = 3

        self.rm.update_metrics(
            char1_id, char2_id,
            affection=affection_gain,
            intimacy=intimacy_gain
        )

        if bond_type == "romantic" and romantic_interest_gain > 0:
            self.rm.update_romance_metrics(
                char1_id, char2_id,
                romantic_interest=romantic_interest_gain,
                commitment=2
            )

        logger.info(f"Quality time: {char1_id} & {char2_id} ({activity})")

    def on_public_display_affection(self, char1_id: str, char2_id: str):
        """Triggered when romantic partners show affection publicly"""
        bond_type = self.rm.get_bond_type(char1_id, char2_id)

        if bond_type == "romantic":
            self.rm.update_metrics(
                char1_id, char2_id,
                public_perception=5
            )

            self.rm.update_romance_metrics(
                char1_id, char2_id,
                commitment=3
            )

            logger.info(f"Public affection: {char1_id} & {char2_id}")

    # ========== PASSIVE SYSTEMS ==========

    def passive_romance_growth(self, char1_id: str, char2_id: str) -> str:
        """Gradual romance growth for high-affection compatible pairs. Returns a string report, or None."""
        bond_type = self.rm.get_bond_type(char1_id, char2_id)

        if bond_type != "romantic":
            return None

        rel = self.rm.get_relationship(char1_id, char2_id)
        affection = rel.get("affection", 0)
        trust = rel.get("trust", 0)
        tension = rel.get("tension", 0)
        romantic_interest = rel.get("romantic_interest", 0)

        # High affection + low tension = natural romantic interest growth
        if affection >= 60 and trust >= 50 and tension < 30:
            # Slow, natural growth
            growth = 1

            # Demisexual characters need higher trust
            c1 = self.rm.get_character_orientation(char1_id)
            c2 = self.rm.get_character_orientation(char2_id)

            if c1.get("orientation") == "demi" or c2.get("orientation") == "demi":
                if trust >= 80:
                    growth = 2  # Faster once trust is established
                else:
                    growth = 0  # No growth until deep trust

            if romantic_interest < 100 and growth > 0:
                self.rm.update_romance_metrics(
                    char1_id, char2_id,
                    romantic_interest=growth
                )
                
                # Fetch actual names
                name1 = self.rm.get_character(char1_id).get("name", char1_id)
                name2 = self.rm.get_character(char2_id).get("name", char2_id)

                logger.debug(f"Passive romance growth: {char1_id} & {char2_id} (+{growth} romantic interest)")
                return f"[{name1} & {name2}] +{growth} Romantic Interest"
            
        return None

    def passive_relationship_decay(self, char1_id: str, char2_id: str, days_since_interaction: int):
        """Relationships slowly decay without interaction"""
        if days_since_interaction < 7:
            return  # No decay if interacted recently

        # Slow decay for neglected relationships
        affection_decay = -1
        intimacy_decay = -1
        romantic_interest_decay = -2

        # Faster decay after longer periods
        if days_since_interaction > 30:
            affection_decay = -3
            intimacy_decay = -3
            romantic_interest_decay = -5

        self.rm.update_metrics(
            char1_id, char2_id,
            affection=affection_decay,
            intimacy=intimacy_decay
        )

        bond_type = self.rm.get_bond_type(char1_id, char2_id)
        if bond_type == "romantic":
            self.rm.update_romance_metrics(
                char1_id, char2_id,
                romantic_interest=romantic_interest_decay
            )

        logger.debug(f"Relationship decay: {char1_id} & {char2_id} ({days_since_interaction} days no contact)")

    # ========== AUTO-CONFESSION SYSTEM ==========

    def _check_auto_confession(self, char1_id: str, char2_id: str, threshold: float = 0.3):
        """
        Check if romance is strong enough to trigger automatic confession
        threshold: probability multiplier (0.0 to 1.0)
        """
        bond_type = self.rm.get_bond_type(char1_id, char2_id)

        if bond_type != "romantic":
            return

        rel = self.rm.get_relationship(char1_id, char2_id)

        # Don't confess if already confessed
        if rel.get("confessed", False):
            return

        affection = rel.get("affection", 0)
        trust = rel.get("trust", 0)
        romantic_interest = rel.get("romantic_interest", 0)
        tension = rel.get("tension", 0)

        # Requirements for auto-confession
        if affection >= 70 and trust >= 60 and romantic_interest >= 65 and tension < 30:
            # Calculate confession probability
            base_chance = (affection + trust + romantic_interest) / 300  # 0.0 to 1.0
            final_chance = base_chance * threshold

            # Roll the dice
            if random.random() < final_chance:
                result = self.rm.confess_romance(char1_id, char2_id)
                if result["success"]:
                    logger.info(f"🔥 AUTO-CONFESSION: {char1_id} confessed to {char2_id}! (Natural progression)")
                    return True

        return False

    # ========== BATCH PROCESSING ==========

    def process_daily_passive_updates(self) -> list[str]:
        """Run once per in-game day to update all relationships. Returns a list of growth reports."""
        data = self.rm._load_data()
        relationships = data.get("relationships", [])
        daily_reports = []

        for rel in relationships:
            pair = rel.get("pair", [])
            if len(pair) != 2:
                continue

            char1, char2 = pair

            # Passive romance growth for compatible pairs
            growth_report = self.passive_romance_growth(char1, char2)
            if growth_report:
                daily_reports.append(growth_report)

            # Auto-recalculate romance stages
            rel["romance_stage"] = self.rm.calculate_romance_stage(rel)

        # Save updates
        data["relationships"] = relationships
        self.rm._save_data(data)

        logger.info("Daily passive relationship updates complete")
        return daily_reports


# Global instance
romance_engine = RomanceEngine()
