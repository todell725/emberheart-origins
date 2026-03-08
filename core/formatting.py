import re

def sanitize_text(text: str) -> str:
    """Clean up 'smart' characters and common encoding artifacts for logs and Discord."""
    if not text: return ""
    # Smart Quotes & Apostrophes
    replacements = {
        "\u201c": '"', "\u201d": '"', # Double quotes
        "\u2018": "'", "\u2019": "'", # Single quotes
        "\u2014": "--", "\u2013": "-", # Dashes
        "\u2026": "..." # Ellipsis
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# Characters to NEVER parse as AI speakers (Prevents God-moding)
IGNORE_SPEAKERS = {"Kaelrath", "King Kaelrath", "The King", "Sovereign"}

def strip_god_moding(text: str) -> str:
    """
    Aggressively strips intra-paragraph god-moding narration.
    Removes sentences that describe the actions of Kaelrath/User.
    """
    if not text: return ""
    
    # 1. Preserve spacing by using a non-destructive split
    # We use capturing group for quotes to keep them in the parts list
    parts = re.split(r'(".*?")', text)
    
    # Patterns for god-moding (Third Person & Second Person)
    names = ["Kaelrath", "King Kaelrath", "The King", "Sovereign"]
    name_pattern = "|".join([re.escape(n) for n in names])
    
    # Sentence pattern: Starts with Name/You/Your, ends with punctuation.
    # We look for matches at the start of the string (ignoring whitespace) or following punctuation.
    gm_regex = re.compile(rf'(^\s*|[.!?]\s+)(?:{name_pattern}|You|Your)\b.*?[.!?](?=\s|$)', re.I)

    cleaned_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Narration: Apply regex to strip god-moding sentences
            # We strip sentences but try to keep the leading spaces for flow
            seg = part
            # Loop-replace to catch multiple sentences
            old_seg = ""
            while old_seg != seg:
                old_seg = seg
                seg = gm_regex.sub(r"\1", seg)
            cleaned_parts.append(seg)
        else:
            # Dialogue: Preserve as-is
            cleaned_parts.append(part)
            
    # Join and clean up double spaces/leading/trailing
    result = "".join(cleaned_parts)
    result = re.sub(r'\s+', ' ', result).strip()
    return result

def heuristic_prose_split(text: str, identities: dict) -> list:
    """
    Attempts to split 'Book-style' prose where multiple characters are narrated
    in a single block without **Name**: tags.
    """
    if not text: return []
    
    # 1. Collect all known character names
    names = sorted([identities[id_].get("name") for id_ in identities if isinstance(identities[id_], dict) and "name" in identities[id_]], key=len, reverse=True)
    names = list(dict.fromkeys(names))
    if not names: return [{"speaker": "DM", "identity": identities.get("DM"), "content": text}]

    # 2. Find all indices where a Name appears anywhere
    name_pattern = "|".join([re.escape(n) for n in names])
    # Match Start OR (Punctuation/Quotes/Asterisks + Space) followed by a Name
    # We allow explicit names anywhere as long as they are distinct words
    split_pattern = rf'(?:^|[\n.!?]["\'”’*]*\s+)({name_pattern})\b'
    
    matches = list(re.finditer(split_pattern, text))
    if not matches:
        return [{"speaker": "DM", "identity": identities.get("DM"), "content": text}]

    blocks = []
    
    # If the text doesn't start with a name, the first part is DM narration
    if matches[0].start() > 0:
        blocks.append({
            "speaker": "DM",
            "identity": identities.get("DM"),
            "content": text[:matches[0].start()].strip()
        })

    for i in range(len(matches)):
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
        
        # Adjust start_idx back if the prefix (punctuation) was part of the match
        # Actually match(1) is exactly the name.
        
        speaker_name = matches[i].group(1)
        # B-14: Start content after the name to avoid duplication
        # We take content after the speaker tag to avoid name duplication
        content = text[matches[i].end():end_idx].strip()
        
        if content:
            blocks.append({
                "speaker": speaker_name,
                "identity": identities.get(speaker_name, identities.get("DM")),
                "content": content
            })

    return blocks

def parse_speaker_blocks(text: str, identities: dict, ignore_headers: set) -> list:
    """
    Parses an AI response string for '<reply>' tags or '**Name**: "Dialogue"' patterns 
    and yields distinct blocks of text assigned to specific identities.
    """
    if not text: return []

    text = sanitize_text(text)
    
    # Optional XML Fallback parsing
    xml_blocks = []
    # Match <reply speaker="Name">content</reply> OR <reply speaker='Name'>content</reply> OR <reply speaker=Name>content</reply>
    for match in re.finditer(r'<reply\s+speaker=(?:"([^"]+)"|\'([^\']+)\'|([^>]+))>(.*?)</reply>', text, re.DOTALL | re.IGNORECASE):
        speaker = match.group(1) or match.group(2) or match.group(3)
        content = match.group(4).strip()
        if speaker and content:
            xml_blocks.append({"speaker": speaker.strip(), "content": content})
            
    if xml_blocks:
        blocks = []
        for b in xml_blocks:
            speaker = b["speaker"]
            content = b["content"]
            token = identities.get(speaker)
            if not token:
                id_match = re.search(r'\[(EH-\d+|DM-\d+|PC-\d+)\]', speaker)
                if id_match and id_match.group(1) in identities:
                    token = identities[id_match.group(1)]
                else:
                    clean_name = re.sub(r'\s*\[.*?\]', '', speaker).strip()
                    if clean_name in identities:
                        token = identities[clean_name]
                    else:
                        match_id = next((k for k in identities if clean_name.lower() in k.lower() or k.lower() in clean_name.lower()), None)
                        if match_id:
                            token = identities[match_id]
                        else:
                            token = {"name": clean_name, "avatar": identities.get("NPC", {}).get("avatar")}
            
            speaker_name = token["name"] if token else re.sub(r'\s*\[.*?\]', '', speaker).strip()
            blocks.append({
                "speaker": speaker_name,
                "identity": token,
                "content": content
            })
        if blocks:
             return blocks

    # Pattern to find Speaker tags (supports **Name**: and Name: and Name (action):)
    # The first capture group is the full delimiter to split on, the second is just the name part.
    pattern = r'((?:^|\n|[ \t]+)(?:\*\*[ \t]*)?([A-Z][A-Za-z0-9_\-\' ]+(?:\s*\([^)]*\))?)[ \t]*(?:\*\*[ \t]*)?:[ \t]*)'
    parts = re.split(pattern, text)

    if len(parts) == 1:
        # No tags found? Try heuristic splitting
        return heuristic_prose_split(text, identities)

    blocks = []
    current_speaker = "DM"
    buffer_text = ""
    
    if parts[0].strip():
        buffer_text += parts[0]

    i = 1
    while i < len(parts):
        if i + 2 >= len(parts): break
        
        raw_name = parts[i+1].strip().rstrip(":")
        segment_content = parts[i+2] 
        
        is_speaker = True
        
        # ID-Lock Protocol
        id_match = re.search(r'\[(EH-\d+|DM-\d+|PC-\d+)\]', raw_name)
        extracted_id = id_match.group(1) if id_match else None
        lookup_name = raw_name.strip("[]").strip()
        
        known_identity = None
        if extracted_id and extracted_id in identities:
            known_identity = identities[extracted_id]
        elif lookup_name in identities:
            known_identity = identities[lookup_name]
        else:
            temp_name = re.sub(r'\s*\[.*?\]', '', lookup_name).strip()
            match = next((k for k in identities if k.lower() in temp_name.lower() or temp_name.lower() in k.lower()), None)
            if match: known_identity = identities[match]

        if not known_identity:
            preceding_text = parts[i-1]
            if preceding_text and not preceding_text.rstrip(' ').endswith('\n') and preceding_text.strip():
                is_speaker = False

            if is_speaker and raw_name in ignore_headers:
                is_speaker = False
            
            if is_speaker and ("Agenda" in raw_name or "Notes" in raw_name or "State" in raw_name):
                is_speaker = False
                
            if is_speaker:
                word_count = len(raw_name.split())
                if word_count > 6: is_speaker = False 
                if word_count == 1 and raw_name.isupper(): is_speaker = False 
            
            if is_speaker and any(char.isdigit() for char in raw_name) and not extracted_id:
                is_speaker = False

            if is_speaker:
                clean_content = segment_content.strip()
                is_narrator = "DM" in lookup_name or "Chronicle" in lookup_name or "Weaver" in lookup_name
                if not is_narrator and not clean_content:
                     is_speaker = False

        if is_speaker:
            if buffer_text.strip():
                is_ignored = any(ign.lower() in current_speaker.lower() for ign in IGNORE_SPEAKERS)
                if not is_ignored:
                    token = identities.get(current_speaker)
                    if not token and current_speaker != "DM":
                        match = next((k for k in identities if k.lower() in current_speaker.lower()), None)
                        if match: token = identities[match]
                        else:
                            clean = re.sub(r'\s*\(.*?\)', '', current_speaker).strip()
                            if clean in identities: token = identities[clean]
                            else: token = {"name": current_speaker, "avatar": identities.get("NPC", {}).get("avatar")}
                    elif current_speaker == "DM":
                        token = identities.get("DM")

                    blocks.append({"speaker": current_speaker, "identity": token, "content": buffer_text.strip()})

            display_name = re.sub(r'\s*\[.*?\]', '', lookup_name).strip()
            display_name = re.sub(r'\s*\(.*?\)', '', display_name).strip()
            current_speaker = display_name
            if known_identity: current_speaker = known_identity["name"]
            buffer_text = segment_content
            
        else:
            buffer_text += f"\n{parts[i]}{segment_content}"

        i += 3
        
    if buffer_text.strip():
        is_ignored = any(ign.lower() in current_speaker.lower() for ign in IGNORE_SPEAKERS)
        if not is_ignored:
            token = identities.get(current_speaker)
            if not token and current_speaker != "DM":
                match = next((k for k in identities if current_speaker.lower() in k.lower()), None)
                if match: token = identities[match]
                else: token = {"name": current_speaker, "avatar": identities.get("NPC", {}).get("avatar")}
            elif current_speaker == "DM":
                token = identities.get("DM")
                
            blocks.append({"speaker": current_speaker, "identity": token, "content": buffer_text.strip()})

    return blocks

