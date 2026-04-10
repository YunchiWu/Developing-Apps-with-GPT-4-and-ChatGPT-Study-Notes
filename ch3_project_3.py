# 结论：效果非常不好
import os
import numpy as np
import redis
from redis.commands.search.query import Query
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.json.path import Path
from pypdf import PdfReader
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY"),
)

class DataService():
    """信息检索服务"""
    def __init__(self):
        # 连接Redis
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
    
    def pdf_to_embeddings(self, pdf_path: str, chunk_length: int=10):
        # 从 PDF 文件中读取数据并将其拆分为块
        reader = PdfReader(pdf_path)
        chunks = []
        for page in reader.pages:
            text_page = page.extract_text()
            chunks.extend([text_page[i:i+chunk_length] for i in range(0, len(text_page), chunk_length)])
        # 创建嵌入
        response = client.embeddings.create(
            model="openai/text-embedding-ada-002",
            input=chunks,
        )
        return [{'id': value.index, 'vector': value.embedding, 'text': chunks[value.index]} for value in response.data]
    
    def load_data_to_redis(self, embeddings):
        self.redis_client.flushdb()
        # Constants
        vector_dim = len(embeddings[0]['vector'])
        # Initial number of vectors
        vector_number = len(embeddings)

        # Create the index
        try:
            self.redis_client.ft("vector_idx").dropindex(True)
        except redis.exceptions.ResponseError:
            pass

        # Define RediSearch fields
        text = TextField(name="text")
        text_embedding = VectorField(
            "vector",
            "FLAT",
            {
                "TYPE": "FLOAT32",
                "DIM": vector_dim,
                "DISTANCE_METRIC": "COSINE",
            }
        )
        fields = [text, text_embedding]
        # Check if index exists
        try:
            self.redis_client.ft("vector_index").info()
            print("Index already exists")
        except:
            # Create RediSearch Index
            self.redis_client.ft("vector_index").create_index(
                fields=fields,
                definition=IndexDefinition(
                    prefix=["doc:"], index_type=IndexType.HASH
                )
            )
        for embedding in embeddings:
            key = f"doc:{str(embedding['id'])}"
            embedding['vector'] = np.array(embedding['vector'], dtype=np.float32).tobytes()
            self.redis_client.hset(key, mapping=embedding)

    def search_redis(self, 
                     user_query: str="vector_index",
                     vector_field: str="vector"):
        # 根据用户输入创建嵌入向量
        embedded_query = client.embeddings.create(
            model="text-embedding-ada-002",
            input=user_query,
        ).data[0].embedding

        # Prepare the Query
        base_query = f'*=>[KNN 5 @{vector_field} $vector AS vector_score]'
        query = (
            Query(base_query)
            .return_fields("text", "vector_score")
            .sort_by("vector_score")
            .paging(0, 5)
            .dialect(2)
        )
        params_dict = {"vector": np.array(
            embedded_query).astype(dtype=np.float32).tobytes()}
        # Perform vector search
        results = self.redis_client.ft("vector_index").search(query, params_dict)
        return [doc['text'] for doc in results.docs]


class IntentService():
    """意图服务"""
    def __init__(self):
        pass

    def get_intent(self, user_question: str):
        # 调用 ChatCompletion 端点
        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": f"""Extract the keywords from the following 
                    question: {user_question}."""
                }
            ]
        )
        # 提取响应
        return response.choices[0].message.content

class ResponseService():
    """响应服务"""
    def __init__(self):
        pass

    def generate_response(self, facts, user_question):
        # 调用 ChatCompletion 端点
        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": f"""Based on the FACTS, answer the QUESTION.
                    QUESTION: {user_question}. FACTS: {facts}"""
                }
            ]
        )
        # 提取响应
        return response.choices[0].message.content

def run(question: str, file: str):
    """初始化数据"""
    data_service = DataService()
    data = data_service.pdf_to_embeddings(file)
    data_service.load_data_to_redis(data)

    # 获取意图
    intent_service = IntentService()
    intents = intent_service.get_intent(question)

    # 获取事实
    facts = data_service.search_redis(intents)

    # # 获得答案
    return ResponseService().generate_response(facts, question)

def main():
    question = "Who is the first person proposing bottleneck model?"
    file = "Vickrey_1969.pdf"
    answer = run(question, file)
    with open("output.txt", "w") as f:
        f.write(answer)

if __name__ == '__main__':
    main()

