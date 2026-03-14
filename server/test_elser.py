from elastic_service import client, settings, generate_degree_plan
import json

response = generate_degree_plan("Bachelors of Computer Science", 2, "Software Engineer", "Google")
print(json.dumps(response, indent=2))

# Let's run the raw query
query = {
    "size": 10,
    "query": {
        "text_expansion": {
            "text_embedding": {
                "model_id": "my-elser-model",
                "model_text": "I am studying Bachelors of Computer Science and I want to become a Software Engineer working at Google."
            }
        }
    }
}
resp = client.search(index=settings.elastic_index, body=query)
print("\nRAW SEARCH:")
print(json.dumps(dict(resp), indent=2))
