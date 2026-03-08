
from core.storage import load_json, save_json

class RelationshipManager:
    """Manages continuous dynamic relationships based on PARTY_RELATIONSHIP_ENGINE.md and ADULT_RELATIONSHIP_CALIBRATION.md

    Now includes romantic relationship mechanics with:
    - Sexual orientation compatibility
    - Romance progression stages
    - Polyamory support
    - Brotherhood bonds for incompatible male pairings
    """

    def __init__(self):
        self.filename = "PARTY_RELATIONSHIPS.json"
        self.orientations_file = "NPC_ORIENTATIONS.json"
        self._orientation_cache = None

    def _load_data(self) -> dict:
        try:
            return load_json(self.filename)
        except Exception:
            # Create default structure if not exists/migration
            return {"version": "1.0", "schema": "PARTY_RELATIONSHIPS.json", "relationships": []}

    def _load_orientations(self) -> dict:
        """Load NPC orientation data with caching"""
        if self._orientation_cache is None:
            try:
                self._orientation_cache = load_json(self.orientations_file)
            except Exception:
                # Return empty if file doesn't exist
                self._orientation_cache = {"version": "1.0", "characters": {}}
        return self._orientation_cache

    def _save_data(self, data: dict):
        save_json(self.filename, data)

    def _match_pair(self, rel: dict, char1: str, char2: str) -> bool:
        pair = set(rel.get("pair", []))
        return {char1, char2} == pair

    def get_relationship(self, char1: str, char2: str) -> dict:
        """Returns the relationship dict for a pair. If it doesn't exist, returns the engine baseline."""
        data = self._load_data()
        for rel in data.get("relationships", []):
            if self._match_pair(rel, char1, char2):
                return rel

        # Engine baseline for day 1 - now includes romance metrics
        baseline = {
            "pair": [char1, char2],
            "affection": 25,
            "trust": 40,
            "tension": 10,
            "public_perception": 5,
            "intimacy": 10,
            "romantic_interest": 0,
            "sexual_compatibility": 0,
            "jealousy": 0,
            "commitment": 0,
            "romance_stage": 0,
            "bond_type": "acquaintance",
            "confessed": False,
            "events": []
        }

        # Auto-detect bond type based on orientation compatibility
        bond_type = self.get_bond_type(char1, char2)
        baseline["bond_type"] = bond_type

        return baseline

    def update_metrics(self, char1: str, char2: str, affection=0, trust=0, tension=0, intimacy=0, public_perception=0) -> dict:
        """Updates metrics for a pair, clamps between 0-100, and saves."""
        data = self._load_data()
        relationships = data.get("relationships", [])
        
        target_rel = None
        for rel in relationships:
            if self._match_pair(rel, char1, char2):
                target_rel = rel
                break
                
        if not target_rel:
            target_rel = self.get_relationship(char1, char2)
            relationships.append(target_rel)
            
        target_rel["affection"] = max(0, min(100, target_rel.get("affection", 25) + affection))
        target_rel["trust"] = max(0, min(100, target_rel.get("trust", 40) + trust))
        target_rel["tension"] = max(0, min(100, target_rel.get("tension", 10) + tension))
        target_rel["intimacy"] = max(0, min(100, target_rel.get("intimacy", 10) + intimacy))
        target_rel["public_perception"] = max(0, min(100, target_rel.get("public_perception", 5) + public_perception))
        
        data["relationships"] = relationships
        self._save_data(data)
        
        return target_rel

    def set_metrics(self, char1: str, char2: str, **kwargs) -> dict:
        """Sets metrics to absolute values."""
        data = self._load_data()
        relationships = data.get("relationships", [])
        
        target_rel = None
        for rel in relationships:
            if self._match_pair(rel, char1, char2):
                target_rel = rel
                break
                
        if not target_rel:
            target_rel = self.get_relationship(char1, char2)
            relationships.append(target_rel)
            
        for k, v in kwargs.items():
            if k in ["affection", "trust", "tension", "intimacy", "public_perception"]:
                target_rel[k] = max(0, min(100, v))
                
        data["relationships"] = relationships
        self._save_data(data)
        return target_rel

    def get_status_labels(self, rel: dict) -> list[str]:
        """Calculates narrative status labels based on current metrics."""
        labels = []

        aff = rel.get("affection", 0)
        tru = rel.get("trust", 0)
        ten = rel.get("tension", 0)
        intm = rel.get("intimacy", 0)
        rom = rel.get("romantic_interest", 0)
        commit = rel.get("commitment", 0)
        bond_type = rel.get("bond_type", "acquaintance")

        # General Status
        if ten >= 75: labels.append("Fractured")
        elif ten >= 50: labels.append("Strained")

        if tru <= 25: labels.append("Distrustful")

        if aff >= 80: labels.append("Devoted")
        elif aff >= 60: labels.append("Bonded")
        elif aff >= 40: labels.append("Friendly")
        elif aff < 40 and ten < 50: labels.append("Neutral")

        # Brotherhood Bonds (non-romantic male intimacy)
        if bond_type == "brotherhood":
            if intm >= 70: labels.append("Blood Brothers")
            elif intm >= 50: labels.append("Shield Brothers")
            elif intm >= 30: labels.append("Comrades")
            return labels  # Skip romantic labels

        # Romance-specific labels
        if rom >= 80 and not rel.get("confessed", False):
            labels.append("Pining")

        if rom >= 60 and aff >= 70:
            labels.append("Crushing")

        if rel.get("confessed", False) and rom >= 50:
            if commit >= 90:
                labels.append("Life Partners")
            elif commit >= 70:
                labels.append("Committed Romance")
            elif intm >= 60:
                labels.append("Dating")
            else:
                labels.append("Romantic Interest")

        # Legacy intimacy status (for non-romantic closeness)
        if bond_type != "brotherhood" and rom < 50:
            if intm >= 85: labels.append("Exclusive Romance")
            elif intm >= 70: labels.append("Physical Romance")
            elif intm >= 50: labels.append("Romantic Bond")
            elif intm >= 30: labels.append("Emotional Closeness")

        return labels

    # ========== ROMANCE MECHANICS ==========

    def get_character_orientation(self, char_id: str) -> dict:
        """Get orientation data for a character"""
        orientations = self._load_orientations()
        return orientations.get("characters", {}).get(char_id, {
            "gender": "unknown",
            "orientation": "straight",
            "polyamorous": False
        })

    def is_orientation_compatible(self, char1_id: str, char2_id: str) -> bool:
        """Check if two characters are romantically compatible based on orientation"""
        c1 = self.get_character_orientation(char1_id)
        c2 = self.get_character_orientation(char2_id)

        g1 = c1.get("gender", "unknown")
        g2 = c2.get("gender", "unknown")
        o1 = c1.get("orientation", "straight")
        o2 = c2.get("orientation", "straight")

        # Handle special cases
        if o1 in ["child", "construct", "spectral"] or o2 in ["child", "construct", "spectral"]:
            return False

        # Bi/pan are compatible with everyone
        if o1 in ["bi", "pan"] and o2 in ["bi", "pan"]:
            return True

        # Bi/pan with straight (requires opposite genders)
        if o1 in ["bi", "pan"] and o2 == "straight":
            return g1 != g2
        if o2 in ["bi", "pan"] and o1 == "straight":
            return g1 != g2

        # Bi/pan with gay (requires same genders)
        if o1 in ["bi", "pan"] and o2 == "gay":
            return g1 == g2
        if o2 in ["bi", "pan"] and o1 == "gay":
            return g1 == g2

        # Straight compatibility (opposite genders)
        if o1 == "straight" and o2 == "straight":
            return g1 != g2

        # Gay compatibility (same genders)
        if o1 == "gay" and o2 == "gay":
            return g1 == g2

        # Ace can have romantic bonds with anyone (no sexual component)
        if o1 == "ace" or o2 == "ace":
            return True

        # Fluid can bond with anyone
        if o1 == "fluid" or o2 == "fluid":
            return True

        # Demi follows same rules as orientation after bond forms
        # (treat as their underlying orientation for compatibility check)

        return False

    def get_bond_type(self, char1_id: str, char2_id: str) -> str:
        """Determine bond type: romantic, brotherhood, or platonic"""
        c1 = self.get_character_orientation(char1_id)
        c2 = self.get_character_orientation(char2_id)

        g1 = c1.get("gender", "unknown")
        g2 = c2.get("gender", "unknown")
        o1 = c1.get("orientation", "straight")
        o2 = c2.get("orientation", "straight")

        # Brotherhood: two males who are NOT both bi/pan/gay/fluid
        if g1 == "male" and g2 == "male":
            if not (o1 in ["bi", "pan", "gay", "fluid"] and o2 in ["bi", "pan", "gay", "fluid"]):
                return "brotherhood"

        # Check if romantically compatible
        if self.is_orientation_compatible(char1_id, char2_id):
            return "romantic"

        return "platonic"

    def calculate_romance_stage(self, rel: dict) -> int:
        """Calculate romance stage (0-7) based on metrics"""
        aff = rel.get("affection", 0)
        tru = rel.get("trust", 0)
        ten = rel.get("tension", 0)
        intm = rel.get("intimacy", 0)
        rom = rel.get("romantic_interest", 0)
        commit = rel.get("commitment", 0)
        confessed = rel.get("confessed", False)

        # Tension blocks romance progression
        if ten >= 50:
            return max(0, rel.get("romance_stage", 0) - 1)

        # Stage 0: Strangers
        if aff < 20:
            return 0

        # Stage 1: Acquaintances
        if aff < 40:
            return 1

        # Stage 2: Friends
        if aff < 60 or tru < 30:
            return 2

        # Stage 3: Close Friends
        if aff < 75 or tru < 50:
            return 3

        # --- Beyond this point, aff >= 75 and tru >= 50 ---

        # Stage 7: Life Partners (check first to avoid false fallthrough)
        if aff >= 95 and tru >= 95 and intm >= 90 and commit >= 90:
            return 7

        # Stage 6: Committed Romance
        if aff >= 90 and intm >= 80 and commit >= 70:
            return 6

        # Stage 5: Romantic Partners
        if confessed and aff >= 80 and intm >= 60 and commit >= 40:
            return 5

        # Stage 4: Romantic Interest (requires confession or high metrics)
        if rom >= 50 and (confessed or (aff >= 75 and intm >= 30)):
            return 4

        # Fallback: high affection but no romantic progression = Close Friends
        return 3

    def confess_romance(self, char1_id: str, char2_id: str) -> dict:
        """Have char1 confess romantic feelings to char2"""
        rel = self.get_relationship(char1_id, char2_id)

        # Check compatibility
        bond_type = self.get_bond_type(char1_id, char2_id)
        if bond_type != "romantic":
            return {
                "success": False,
                "reason": f"Not romantically compatible ({bond_type} bond)",
                "relationship": rel
            }

        # Check if metrics are high enough
        if rel.get("affection", 0) < 60 or rel.get("trust", 0) < 40:
            return {
                "success": False,
                "reason": "Relationship not developed enough (need Affection 60+, Trust 40+)",
                "relationship": rel
            }

        # Confession succeeds!
        data = self._load_data()
        relationships = data.get("relationships", [])

        # Find or create relationship
        target_rel = None
        for r in relationships:
            if self._match_pair(r, char1_id, char2_id):
                target_rel = r
                break

        if not target_rel:
            target_rel = rel
            relationships.append(target_rel)

        # Update metrics
        target_rel["confessed"] = True
        target_rel["romantic_interest"] = max(target_rel.get("romantic_interest", 0), 60)
        target_rel["intimacy"] = min(100, target_rel.get("intimacy", 0) + 10)
        target_rel["bond_type"] = "romantic"

        # Add event
        events = target_rel.get("events", [])
        events.append("confession")
        target_rel["events"] = events

        # Recalculate stage
        target_rel["romance_stage"] = self.calculate_romance_stage(target_rel)

        data["relationships"] = relationships
        self._save_data(data)

        return {
            "success": True,
            "reason": "Confession accepted!",
            "relationship": target_rel
        }

    def add_romantic_partner(self, char_id: str, partner_id: str) -> bool:
        """Add a romantic partner to a character's profile"""
        # This would update character profile JSON
        # For now, just return True if compatible
        return self.is_orientation_compatible(char_id, partner_id)

    def update_romance_metrics(self, char1: str, char2: str, romantic_interest=0,
                               sexual_compatibility=0, jealousy=0, commitment=0) -> dict:
        """Update romance-specific metrics"""
        data = self._load_data()
        relationships = data.get("relationships", [])

        target_rel = None
        for rel in relationships:
            if self._match_pair(rel, char1, char2):
                target_rel = rel
                break

        if not target_rel:
            target_rel = self.get_relationship(char1, char2)
            relationships.append(target_rel)

        # Update romance metrics
        target_rel["romantic_interest"] = max(0, min(100,
            target_rel.get("romantic_interest", 0) + romantic_interest))
        target_rel["sexual_compatibility"] = max(0, min(100,
            target_rel.get("sexual_compatibility", 0) + sexual_compatibility))
        target_rel["jealousy"] = max(0, min(100,
            target_rel.get("jealousy", 0) + jealousy))
        target_rel["commitment"] = max(0, min(100,
            target_rel.get("commitment", 0) + commitment))

        # Recalculate romance stage
        target_rel["romance_stage"] = self.calculate_romance_stage(target_rel)

        data["relationships"] = relationships
        self._save_data(data)

        return target_rel

# Global instance for easy import
relationship_manager = RelationshipManager()
