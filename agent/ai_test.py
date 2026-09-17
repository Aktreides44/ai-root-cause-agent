from ollama import Client

client = Client(host="http://172.29.160.1:11434")

response = client.chat(
    model="qwen3:8b",
    messages=[
        {
            "role": "user",
            "content": "What is an AI agent? Answer in one sentence."
        }
    ],
    think=False,
    options={
        "num_predict": 50
    }
)

print(response.message.content)
