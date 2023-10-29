import os
import openai
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceInstructEmbeddings, HuggingFaceEmbeddings, HuggingFaceBgeEmbeddings
from chromadb.config import Settings
import yaml
import torch

ROOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
SOURCE_DIRECTORY = f"{ROOT_DIRECTORY}/Docs_for_DB"
PERSIST_DIRECTORY = f"{ROOT_DIRECTORY}/Vector_DB"
INGEST_THREADS = os.cpu_count() or 8

CHROMA_SETTINGS = Settings(
    chroma_db_impl="duckdb+parquet", persist_directory=PERSIST_DIRECTORY, anonymized_telemetry=False
)

def validate_config(config):
    required_keys = ['EMBEDDING_MODEL_NAME', 'server']
    server_sub_keys = ['connection_str', 'api_key', 'prefix', 'suffix', 'model_temperature', 'model_max_tokens']
    missing_keys = []

    for key in required_keys:
        if key not in config:
            missing_keys.append(key)

    if 'server' in config:
        for sub_key in server_sub_keys:
            if sub_key not in config['server']:
                missing_keys.append(f'server.{sub_key}')

    if missing_keys:
        raise KeyError(f"Missing required keys in config file: {', '.join(missing_keys)}")

def connect_to_local_chatgpt(prompt):
    with open('config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)
        validate_config(config)
        server_config = config.get('server', {})
        openai_api_base = server_config.get('connection_str')
        openai_api_key = server_config.get('api_key')
        prefix = server_config.get('prefix')
        suffix = server_config.get('suffix')
        model_temperature = server_config.get('model_temperature')
        model_max_tokens = server_config.get('model_max_tokens')

    openai.api_base = openai_api_base
    openai.api_key = openai_api_key

    formatted_prompt = f"{prefix}{prompt}{suffix}"
    response = openai.ChatCompletion.create(
        model="local model",
        temperature=model_temperature,
        max_tokens=model_max_tokens,
        messages=[{"role": "user", "content": formatted_prompt}]
    )
    return response.choices[0].message["content"]

def ask_local_chatgpt(query, persist_directory=PERSIST_DIRECTORY, client_settings=CHROMA_SETTINGS):
    with open('config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)
        validate_config(config)
        EMBEDDING_MODEL_NAME = config['EMBEDDING_MODEL_NAME']
        COMPUTE_DEVICE = config.get("COMPUTE_DEVICE", "cpu")
        config_data = config.get('embedding-models', {})

    model_kwargs = {"device": COMPUTE_DEVICE}

    if "instructor" in EMBEDDING_MODEL_NAME:
        embed_instruction = config_data['instructor'].get('embed_instruction')
        query_instruction = config_data['instructor'].get('query_instruction')
        
        embeddings = HuggingFaceInstructEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs=model_kwargs,
            embed_instruction=embed_instruction,
            query_instruction=query_instruction
        )

    elif "bge" in EMBEDDING_MODEL_NAME:
        query_instruction = config_data['bge'].get('query_instruction')
        
        embeddings = HuggingFaceBgeEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs=model_kwargs,
            query_instruction=query_instruction
        )

    else:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs=model_kwargs
        )

    db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        client_settings=client_settings,
    )
    retriever = db.as_retriever()
    relevant_contexts = retriever.get_relevant_documents(query)
    contexts = [document.page_content for document in relevant_contexts]
    prepend_string = "Only base your answer to the following question on the provided context."
    augmented_query = "\n\n---\n\n".join(contexts) + "\n\n-----\n\n" + query
    response_json = connect_to_local_chatgpt(augmented_query)
        
    return {"answer": response_json, "sources": relevant_contexts}

def interact_with_chat(user_input):
    global last_response
    response = ask_local_chatgpt(user_input)
    answer = response['answer']
    last_response = answer
    return answer
