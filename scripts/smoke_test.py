from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Say hello in 5 words."}]
)
print("CHAT:", resp.choices[0].message.content)

emb = client.embeddings.create(
    model="text-embedding-3-small",
    input="The quick brown fox."
)
print("EMBEDDING LENGTH:", len(emb.data[0].embedding))