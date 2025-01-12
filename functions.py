
from typing import List, Dict

def parse_ass_file(content: str) -> List[Dict[str, str]]:
    """Parse ASS subtitle file and extract dialogue lines"""
    subtitles = []
    lines = content.split('\n')
    for line in lines:
        if line.startswith('Dialogue:'):
            # Split at first 9 commas to separate format from content
            parts = line.split(',', 9)
            if len(parts) > 9:
                subtitle = {
                    'start_time': parts[1],
                    'end_time': parts[2],
                    'style': parts[3],
                    'text': parts[9].strip()
                }
                subtitles.append(subtitle)
    return subtitles