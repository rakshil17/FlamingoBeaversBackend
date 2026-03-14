from elastic_service import client, settings
import json

query = {
    "size": 10,
    "query": {
        "sparse_vector": {
            "field": "text_embedding",
            "inference_id": "my-elser-model",
            "query": "I am studying Bachelors of Computer Science and I want to become a Software Engineer working at Google."
        }
    }
}
resp = client.search(index=settings.elastic_index, body=query)
print(json.dumps(dict(resp), indent=2))
