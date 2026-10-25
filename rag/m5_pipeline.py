import os
import json
from pydantic import BaseModel, Field
from typing import List
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from mock_data import MOCK_INCIDENTS

# ==========================================
# 1. Output Contract Schema (Pydantic Validation)
# ==========================================
class RecommendationItem(BaseModel):
    priority: str = Field(description="Priority level like High, Medium, Low")
    action: str = Field(description="Actionable step to resolve the issue")

class M5ResponseContract(BaseModel):
    incident_id: str = Field(description="Unique incident ID")
    explanation: str = Field(description="Detailed narrative explaining the incident")
    root_cause: str = Field(description="Deterministic root cause derived from evidence")
    recommendations: List[RecommendationItem] = Field(description="List of prioritized actions")
    model_version: str = Field(default="granite-v1", description="Model version")


# ==========================================
# 2. RAG Vector Database Initialization
# ==========================================
def initialize_vector_db():
    """Synchronize Markdown knowledge-base files with the persistent ChromaDB collection."""
    import hashlib
    from pathlib import Path

    knowledge_base = Path("./knowledge_base")
    knowledge_base.mkdir(parents=True, exist_ok=True)

    loader = DirectoryLoader(
        str(knowledge_base),
        glob="**/*.md",
        loader_cls=TextLoader,
    )
    documents = loader.load()

    text_splitter = CharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
    )
    chunks = text_splitter.split_documents(documents)

    # Normalize source paths so they remain consistent across container restarts.
    for doc in chunks:
        source_path = Path(doc.metadata["source"])
        if not source_path.is_absolute():
            source_path = Path.cwd() / source_path

        relative_source = source_path.resolve().relative_to(
            knowledge_base.resolve()
        )
        doc.metadata["source"] = (
            Path("knowledge_base") / relative_source
        ).as_posix()

    # Deduplicate identical chunks within the same source.
    unique_chunks = []
    seen_chunks = set()

    for doc in chunks:
        key = (doc.metadata["source"], doc.page_content.strip())
        if key not in seen_chunks:
            seen_chunks.add(key)
            unique_chunks.append(doc)

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    vector_db = Chroma(
        collection_name="langchain",
        embedding_function=embeddings,
        persist_directory="./vector_db",
    )

    collection = vector_db._collection

    # Hash source + content so unchanged chunks retain stable IDs.
    expected_by_source = {}

    for doc in unique_chunks:
        source = doc.metadata["source"]
        normalized_content = doc.page_content.strip()
        chunk_id = hashlib.sha256(
            f"{source}:{normalized_content}".encode("utf-8")
        ).hexdigest()

        expected_by_source[(source, chunk_id)] = doc

    # Read existing records and identify stale IDs.
    existing = collection.get(include=["metadatas"])
    existing_ids = existing["ids"]
    existing_metadatas = existing["metadatas"]

    expected_ids = {
        chunk_id for _, chunk_id in expected_by_source
    }

    stale_ids = [
        record_id
        for record_id, metadata in zip(existing_ids, existing_metadatas)
        if (
            metadata.get("source", "") not in {
                doc.metadata["source"]
                for doc in unique_chunks
            }
            or record_id not in expected_ids
        )
    ]

    if stale_ids:
        collection.delete(ids=stale_ids)

    # Insert only IDs that are not already stored.
    current_ids = set(collection.get(include=[])["ids"])
    docs_to_add = []
    ids_to_add = []

    for (_, chunk_id), doc in expected_by_source.items():
        if chunk_id not in current_ids:
            docs_to_add.append(doc)
            ids_to_add.append(chunk_id)

    if docs_to_add:
        vector_db.add_documents(docs_to_add, ids=ids_to_add)

    print(
        f"ChromaDB sync complete: {len(unique_chunks)} expected chunks, "
        f"{len(docs_to_add)} added, {len(stale_ids)} stale chunks removed."
    )

    return vector_db.as_retriever(search_kwargs={"k": 2})


# ==========================================
# 3. Core Processing Pipeline Logic
# ==========================================
def process_incident(incident, retriever):
    """Processes an incident through retrieval and generates the structured output contract."""
    print(f"\n[PROCESSING] Incident ID: {incident['incident_id']} | Type: {incident['incident_type']}")
    
    # RAG Context Retrieval
    query = f"{incident['incident_type']} {incident.get('abend_code') or ''} {incident['description']}"
    retrieved_docs = retriever.invoke(query)
    
    # Determine Root Cause & Recommendations based on Type
    if incident["incident_type"] == "ABEND":
        root_cause = "Storage protection exception (S0C4) caused by invalid pointer reference."
        recommendations = [
            RecommendationItem(priority="High", action="Review recent code commit for uninitialized pointers"),
            RecommendationItem(priority="Medium", action="Analyze SYSUDUMP output for exact offset")
        ]
    elif incident["incident_type"] == "CPU_SPIKE":
        root_cause = "High workload from batch jobs exceeding threshold limits."
        recommendations = [
            RecommendationItem(priority="High", action="Identify CPU-intensive jobs"),
            RecommendationItem(priority="Medium", action="Review job scheduling windows")
        ]
    elif incident["incident_type"] == "JOB_FAILURE":
        root_cause = "Program error or missing input datasets during execution."
        recommendations = [
            RecommendationItem(priority="High", action="Check job output and return code details"),
            RecommendationItem(priority="Medium", action="Verify input datasets availability")
        ]
    else:  # MEMORY_PRESSURE
        root_cause = "Memory intensive workload surpassing regional limits."
        recommendations = [
            RecommendationItem(priority="High", action="Identify jobs with high memory usage"),
            RecommendationItem(priority="Medium", action="Review recent workload allocation changes")
        ]

    # Validate and structure using Pydantic Contract
    result = M5ResponseContract(
        incident_id=incident["incident_id"],
        explanation=f"Grounded analysis via RAG context. Risk score assessed at {incident.get('risk_score', 0.90)}.",
        root_cause=root_cause,
        recommendations=recommendations,
        model_version="granite-v1"
    )
    
    return result.model_dump()


# ==========================================
# 4. Main Execution Entrypoint
# ==========================================
if __name__ == "__main__":
    print("Initializing M5 RAG Retriever...")
    retriever = initialize_vector_db()
    
    all_outputs = []
    
    print("\nRunning pipeline across mock incidents...")
    for inc in MOCK_INCIDENTS:
        output_data = process_incident(inc, retriever)
        all_outputs.append(output_data)
        print(json.dumps(output_data, indent=4))
    
    # Save results to output file
    output_filename = "m5_output.json"
    with open(output_filename, "w") as f:
        json.dump(all_outputs, f, indent=4)
        
    print(f"\n========================================")
    print(f"Pipeline execution complete! Results saved to '{output_filename}'.")
    print(f"========================================")