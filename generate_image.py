#!/usr/bin/env python3
"""Generate an image from a topic using DALL-E 3 and save it to generated_images/."""

import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not found. Run: pip install openai")
    sys.exit(1)

OUTPUT_DIR = Path(__file__).parent / "generated_images"


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Set it with: export OPENAI_API_KEY=your-key-here")
        sys.exit(1)

    topic = input("Enter a topic for the image: ").strip()
    if not topic:
        print("No topic entered. Exiting.")
        sys.exit(1)

    prompt = f"An educational illustration related to: {topic}. Clear, colorful, suitable for ESL learners."

    print(f"\nGenerating image for: '{topic}' ...")
    client = OpenAI(api_key=api_key)

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c if c.isalnum() or c in " -" else "_" for c in topic)
    safe_topic = safe_topic.replace(" ", "_")[:50]
    filename = OUTPUT_DIR / f"{safe_topic}_{timestamp}.png"

    urllib.request.urlretrieve(image_url, filename)
    print(f"Image saved to: {filename}")


if __name__ == "__main__":
    main()
