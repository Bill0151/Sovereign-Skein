import re

class RedLineFilter:
    """
    Implements the OPSEC 'Red-Line' Protocol for MIND-SKEIN V12.
    Ensures internal telemetry never reaches public repositories.
    """
    
    FORBIDDEN_KEYWORDS = [
        r"skein", 
        r"target\s*#", 
        r"internal", 
        r"draft", 
        r"assessor", 
        r"executor", 
        "gemini"
    ]

    @staticmethod
    def scrub(raw_output):
        """
        Extracts content within <github_payload> tags and verifies OPSEC.
        Returns: (scrubbed_string, success_boolean)
        """
        # 1. Extraction via XML-style tags
        match = re.search(r'<github_payload>(.*?)</github_payload>', raw_output, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return None, False
            
        payload = match.group(1).strip()
        
        # 2. Forbidden Keyword Scan (Case Insensitive)
        for pattern in RedLineFilter.FORBIDDEN_KEYWORDS:
            if re.search(pattern, payload, re.IGNORECASE):
                # Critical OPSEC breach
                return f"OPSEC BREACH: Found forbidden pattern '{pattern}'", False
                
        return payload, True