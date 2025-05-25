#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from backend.app.admin.service.knowledge_graph.text_utils import chunk_text
from backend.app.admin.service.knowledge_graph.llm import call_llm, extract_json_from_text
from backend.app.admin.service.knowledge_graph.prompts import MAIN_SYSTEM_PROMPT, MAIN_USER_PROMPT
from backend.app.admin.service.knowledge_graph.entity_standardization import standardize_entities, infer_relationships, limit_predicate_length


def get_unique_entities(triples):
    """
    Get the set of unique entities from the triples.
    
    Args:
        triples: List of triple dictionaries
        
    Returns:
        Set of unique entity names
    """
    entities = set()
    for triple in triples:
        if not isinstance(triple, dict):
            continue
        if "subject" in triple:
            entities.add(triple["subject"])
        if "object" in triple:
            entities.add(triple["object"])
    return entities

def process_with_llm(config, input_text, debug=False):
    """
    Process input text with LLM to extract triples.
    
    Args:
        config: Configuration dictionary
        input_text: Text to analyze
        debug: If True, print detailed debug information
        
    Returns:
        List of extracted triples or None if processing failed
    """
    # Use prompts from the prompts module
    system_prompt = MAIN_SYSTEM_PROMPT
    user_prompt = MAIN_USER_PROMPT
    user_prompt += f"```\n{input_text}```\n" 

    # LLM configuration
    model = config.get("llm", {}).get("model", "gpt-3.5-turbo")
    api_key = config.get("llm", {}).get("api_key")
    max_tokens = config.get("llm", {}).get("max_tokens", 1000)
    temperature = config.get("llm", {}).get("temperature", 0.7)
    base_url = config.get("llm", {}).get("base_url", "https://api.openai.com/v1/chat/completions")
    
    # Process with LLM
    metadata = {}
    response = call_llm(model, user_prompt, api_key, system_prompt, max_tokens, temperature, base_url)
    
    # Print raw response only if debug mode is on
    if debug:
        print("Raw LLM response:")
        print(response)
        print("\n---\n")
    
    # Extract JSON from the response
    result = extract_json_from_text(response)
    
    if result:
        # Validate and filter triples to ensure they have all required fields
        valid_triples = []
        invalid_count = 0
        
        for item in result:
            if isinstance(item, dict) and "subject" in item and "predicate" in item and "object" in item:
                # Add metadata to valid items
                valid_triples.append(dict(item, **metadata))
            else:
                invalid_count += 1
        
        if invalid_count > 0:
            print(f"Warning: Filtered out {invalid_count} invalid triples missing required fields")
        
        if not valid_triples:
            print("Error: No valid triples found in LLM response")
            return None
        
        # Apply predicate length limit to all valid triples
        for triple in valid_triples:
            triple["predicate"] = limit_predicate_length(triple["predicate"])
        
        # Print extracted JSON only if debug mode is on
        if debug:
            print("Extracted JSON:")
            print(json.dumps(valid_triples, indent=2))  # Pretty print the JSON
        
        return valid_triples
    else:
        # Always print error messages even if debug is off
        print("\n\nERROR ### Could not extract valid JSON from response: ", response, "\n\n")
        return None

def get_entity_types(entities, config):
    """
    获取实体的类型
    
    Args:
        entities: 实体列表
        config: 配置信息
        
    Returns:
        dict: 实体类型字典，key为实体，value为类型
    """
    system_prompt = """你是一个实体类型分类专家。你需要判断给定实体的类型。
类型只能是以下几种：人物、事件、组织、概念、地点。
请以JSON格式返回，key为实体，value为类型。"""
    
    # 将实体列表转换为字符串
    entities_text = "、".join(entities)
    user_prompt = f"请判断以下实体的类型：{entities_text}"
    
    # LLM configuration
    model = config.get("llm", {}).get("model", "gpt-3.5-turbo")
    api_key = config.get("llm", {}).get("api_key")
    max_tokens = config.get("llm", {}).get("max_tokens", 1000)
    temperature = config.get("llm", {}).get("temperature", 0.7)
    base_url = config.get("llm", {}).get("base_url", "https://api.openai.com/v1/chat/completions")
    
    # 调用LLM
    response = call_llm(
        model,
        user_prompt,
        api_key,
        system_prompt,
        max_tokens,
        temperature,
        base_url
    )

    debug = config.get("debug", False)
    # Print raw response only if debug mode is on
    if debug:
        print("Raw LLM response:")
        print(response)
        print("\n---\n")
    
    # 解析返回的JSON
    entity_types = extract_json_from_text(response)
    return entity_types if entity_types else {}

def process_text_in_chunks(config: dict, full_text, debug=False):
    """
    Process a large text by breaking it into chunks with overlap,
    and then processing each chunk separately.
    
    Args:
        config: Configuration dictionary
        full_text: The complete text to process
        debug: If True, print detailed debug information
    
    Returns:
        List of all extracted triples from all chunks
    """
    # Get chunking parameters from config
    chunk_size = config.get("chunking", {}).get("chunk_size", 500)
    overlap = config.get("chunking", {}).get("overlap", 50)
    
    # Split text into chunks
    text_chunks = chunk_text(full_text, chunk_size, overlap)
    
    print("=" * 50)
    print("PHASE 1: INITIAL TRIPLE EXTRACTION")
    print("=" * 50)
    print(f"Processing text in {len(text_chunks)} chunks (size: {chunk_size} words, overlap: {overlap} words)")
    
    # Process each chunk
    all_results = []
    for i, chunk in enumerate(text_chunks):
        print(f"Processing chunk {i+1}/{len(text_chunks)} ({len(chunk.split())} words)")
        
        # Process the chunk with LLM
        chunk_results = process_with_llm(config, chunk, debug)
        
        if chunk_results:
            # Add chunk information to each triple
            for item in chunk_results:
                item["chunk"] = i + 1
            
            # Add to overall results
            all_results.extend(chunk_results)
        else:
            print(f"Warning: Failed to extract triples from chunk {i+1}")
    
    print(f"\nExtracted a total of {len(all_results)} triples from all chunks")
    
    # Apply entity standardization if enabled
    if config.get("standardization", {}).get("enabled", False):
        print("\n" + "="*50)
        print("PHASE 2: ENTITY STANDARDIZATION")
        print("="*50)
        print(f"Starting with {len(all_results)} triples and {len(get_unique_entities(all_results))} unique entities")
        
        all_results = standardize_entities(all_results, config)
        
        print(f"After standardization: {len(all_results)} triples and {len(get_unique_entities(all_results))} unique entities")
    
    # Apply relationship inference if enabled
    if config.get("inference", {}).get("enabled", False):
        print("\n" + "="*50)
        print("PHASE 3: RELATIONSHIP INFERENCE")
        print("="*50)
        print(f"Starting with {len(all_results)} triples")
        
        # Count existing relationships
        relationship_counts = {}
        for triple in all_results:
            relationship_counts[triple["predicate"]] = relationship_counts.get(triple["predicate"], 0) + 1
        
        print("Top 5 relationship types before inference:")
        for pred, count in sorted(relationship_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {pred}: {count} occurrences")
        
        all_results = infer_relationships(all_results, config)
        
        # Count relationships after inference
        relationship_counts_after = {}
        for triple in all_results:
            relationship_counts_after[triple["predicate"]] = relationship_counts_after.get(triple["predicate"], 0) + 1
        
        print("\nTop 5 relationship types after inference:")
        for pred, count in sorted(relationship_counts_after.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {pred}: {count} occurrences")
        
        # Count inferred relationships
        inferred_count = sum(1 for triple in all_results if triple.get("inferred", False))
        print(f"\nAdded {inferred_count} inferred relationships")
        print(f"Final knowledge graph: {len(all_results)} triples")
    
    # 在实体标准化之后，添加实体类型识别
    if all_results:
        print("\n" + "="*50)
        print("PHASE 4: ENTITY TYPE CLASSIFICATION")
        print("="*50)
        
        # 收集所有唯一的主语和宾语
        unique_entities = set()
        for triple in all_results:
            if "subject" in triple:
                unique_entities.add(triple["subject"])
            if "object" in triple:
                unique_entities.add(triple["object"])
        
        print(f"开始识别 {len(unique_entities)} 个唯一实体的类型")
        
        # 获取实体类型
        entity_types = get_entity_types(list(unique_entities), config)
        
        # 将类型信息添加到三元组中
        for triple in all_results:
            if triple["subject"] in entity_types:
                triple["subject_type"] = entity_types[triple["subject"]]
            if triple["object"] in entity_types:
                triple["object_type"] = entity_types[triple["object"]]
        
        print("实体类型识别完成")
        
        # 统计各类型实体数量
        type_counts = {}
        for entity_type in entity_types.values():
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        print("\n实体类型统计：")
        for type_name, count in type_counts.items():
            print(f"- {type_name}: {count} 个")
    
    return all_results



class KnowledgeGraphService:

    @staticmethod
    def generate_knowledge_graph(input_text: str, config: dict, debug: bool = False) -> None:
        result = process_text_in_chunks(config, input_text, debug)
        if result:
            print("Knowledge graph generation completed successfully.")
            return result
        else:
            print("Knowledge graph generation failed due to errors in LLM processing.")

kg_service = KnowledgeGraphService()