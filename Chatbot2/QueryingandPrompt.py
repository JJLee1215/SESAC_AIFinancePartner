import os
import sys
current_directory = os.path.dirname(os.path.abspath(__file__))
full_path = os.path.join(current_directory, '..')
sys.path.append(full_path)
from access import get_openai_key, get_pinecone_env, get_pinecone_key

import pinecone

from llama_index import VectorStoreIndex, ServiceContext
from llama_index.vector_stores import PineconeVectorStore

from llama_index import VectorStoreIndex, get_response_synthesizer
from llama_index.retrievers import VectorIndexRetriever
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.postprocessor import SimilarityPostprocessor,KeywordNodePostprocessor
from llama_index.prompts import PromptTemplate

import time


# 1. Key값 설정
os.environ["OPENAI_API_KEY"] = get_openai_key()
os.environ["PINECONE_ENV"] = get_pinecone_env()
environment = get_pinecone_env()
os.environ["PINECONE_API_KEY"] = get_pinecone_key()
pinecone.init(api_key = get_pinecone_key(), environment = get_pinecone_env())

# 2. LlammaIndex - Pinecone 연동
pinecone_index = pinecone.Index("openai")
vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
index = VectorStoreIndex.from_vector_store(vector_store)

# 3. Querying Stage 조작: configure retriever, Configuring node postprocessors, configure response synthesizer
## 3.1 configure retriever
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=3,
)

## 3.2 Configuring node postprocessors
node_postprocessors = [SimilarityPostprocessor(similarity_cutoff=0.3)]

## 3.3 configure response synthesizer
#response_synthesizer = get_response_synthesizer(response_mode="tree_summarize",) #(streaming = True, response_mode="tree_summarize",)
response_synthesizer = get_response_synthesizer(response_mode="tree_summarize",) #(streaming = True, response_mode="tree_summarize",)
  #synth = get_response_synthesizer(text_qa_template=custom_qa_prompt, refine_template=custom_refine_prompt)
  # 이 함수를 사용하면 쉽게 prompt engineering을 할 수 있다.
  # 지금 streaming 기능이 작동하지 않음.
  # streaming = True -> response.response로 응답 할 수 없음
  # prompts_dict = query_engine.get_prompts() # (response_mode="compact") 일때
  # print(list(prompts_dict.keys()))
  
## 3.4 assemble query engine
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    response_synthesizer=response_synthesizer,
    node_postprocessors=node_postprocessors,
)

# 4. Prompt Engineering: shakespeare!
qa_prompt_tmpl_str = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "You are finance expert"
    "Given the context information and not prior knowledge\n"
    "한국말로만 대답해주세요"
    "Answer example: {2024년 이차전지 주가는 예측은 약 3.5%상승 될 것이며, 글로벌 증시의 경우 약 -75pb 하락할 것으로 예상됩니다.}"
    
    "Query: {query_str}\n"
    "Answer: "
)
qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)

query_engine.update_prompts(
    {"response_synthesizer:text_qa_template": qa_prompt_tmpl}
)


if __name__ == "__main__":
    
    text_input = "코리안리 목표주가와 주주환원 정책에 관해 설명해줘"

    start_time = time.time()
    response = query_engine.query(text_input)
    response_time = time.time() - start_time
    
    selected_metadata = []
    if response.metadata is not None:
        for metadata in response.metadata.values():
            page_label = metadata.get('page_label', None)
            file_name = metadata.get('file_name', None)
            selected_metadata.append({'page_label': page_label, 'file_name': file_name})
            
    if not selected_metadata:
        selected_metadata = 'Reference가 없습니다.'
    
    # 5. chat
    
    print("Response:", response.response)
        
    print("Response Time: {:.2f} seconds".format(response_time))
    print("===============================================================")
    
    if response.metadata:
        for source_node in response.source_nodes:
            file_name, page_label = source_node.metadata['file_name'], source_node.metadata['page_label']
            selected_node, similarity_score = source_node.get_content(), source_node.get_score()
            print('file_name :', file_name)
            print('page_label :', page_label)
            print('selected_node :', selected_node)
            print('similarity_score :', similarity_score)
            print("===============================================================")
    # 참고링크: https://docs.llamaindex.ai/en/stable/examples/query_engine/custom_query_engine.html
        
        
    # if response.metadata is None:
    #     print('Reference가 없습니다.')
    # else:
    #     selected_metadata = [{'page_label': metadata['page_label'], 'file_name': metadata['file_name']} for metadata in response.metadata.values()]
    #     print("Metadata:", selected_metadata)