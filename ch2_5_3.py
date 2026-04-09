import os
import json
from openai import OpenAI

def find_product(sql_query):
    # 执行查询
    results = [
        {"name": "pen", "color": "blue", "price": 1.99},
        {"name": "pen", "color": "red", "price": 1.78},
    ]
    return results

def main():
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "find_product",
                "description": "Get a list of products from a sql query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "A SQL query",
                        }
                    },
                    "required": ["sql_query"],
                },
            }
        }
    ]

    user_question = "I need the top 2 products where the price is less than 2.00"
    messages = [{"role": "user", "content": user_question}]
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=messages,
        tools=tools,
    )
    response_message = response.choices[0].message
    messages.append(response_message)

    # 调用函数
    function_args = json.loads(
        response_message.tool_calls[0].function.arguments
    )
    products = find_product(function_args.get("sql_query"))
    # 将函数的响应附加到消息中
    messages.append(
        {
            "role": "tool",
            "tool_call_id": response_message.tool_calls[0].id,
            "content": json.dumps(products),
        }
    )
    # 将函数的响应格式化为自然语言
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=messages,
    )
    print(response.choices[0].message.content)

if __name__ == '__main__':
    main()
