import csv
import asyncio
from googletrans import Translator

async def translate_bulk(texts):
    async with Translator() as translator:
        results = await translator.translate(texts, dest="fa")
        with open("translated-fa.csv", "w", newline='', encoding='utf-8') as translatedfile:
            wordwriter = csv.writer(translatedfile)
            for word in results:
                print(word.text)  # Optional, prints out each translation
                wordwriter.writerow([word.text])  # Write each translated word on a new line

untranslated_words = []

# Read untranslated words from the CSV
with open("untranslated-fa.csv", "r", encoding='utf-8') as untranslatedfile:
    wordreader = csv.reader(untranslatedfile)
    for word in wordreader:
        untranslated_words.append(word[0])

# Run the translation
asyncio.run(translate_bulk(untranslated_words))

