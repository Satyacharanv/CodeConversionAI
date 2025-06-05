import json
import os
from pathlib import Path
from dotenv import load_dotenv
from models.migration import MigrationResult
from utils.file_utils import prepare_download_links
import asyncio
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.azureopenai_agent import agent, llm
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



def is_code_file(filename):
    CODE_EXTENSIONS = {'.java', '.xml', '.yml', '.yaml', '.properties', '.md', '.txt', '.json', '.js', '.ts', '.py', '.sh', '.bat', '.cmd', '.gradle', '.kts', '.sql'}
    return any(filename.lower().endswith(ext) for ext in CODE_EXTENSIONS)

async def process_migration_chunk(chunk_prompt: str, timeout: int = 300) -> str:
    logger.info("Processing migration chunk with timeout %d", timeout)
    messages = [
        SystemMessage(content="You are a helpful AI assistant that uses tools to solve problems."),
        HumanMessage(content=chunk_prompt)
    ]
    try:
        response = await asyncio.wait_for(
            agent.ainvoke({"messages": messages}, config={"recursion_limit": 50}),
            timeout=timeout
        )
        logger.info("Chunk processed successfully")
        return str(response["messages"][-1].content)
    except Exception as e:
        logger.error("Error processing chunk: %s", str(e))
        return f"Error processing chunk: {str(e)}"

async def run_migration_agent(uploads_dir, downloads_dir, code_language, fro_version, to_version):
    logger.info("Starting migration agent for %s -> %s (%s)", fro_version, to_version, code_language)
    # Step 1: Analyze Project Structure
    step1_prompt = f"""
    STEP 1: Analyze Project Structure for Code Migration
    - Scan the uploaded project files in: {uploads_dir}
    - Get the complete file and folder structure
    - return a summary of the project structure and key points to be noted for migration
    Focus ONLY on understanding the project structure in this step.
    """
    step1_result = await process_migration_chunk(step1_prompt, timeout=400)
    logger.info("Step 1 (structure analysis) complete")

    # Step 2: Review Version Documentation
    step2_prompt = f"""
    STEP 2: Review Version Documentation
    - Check the documentation for version changes in: {str(Path(__file__).parent.parent / 'documents')}
    - Identify key changes needed for migrating from {fro_version} to {to_version} in {code_language}
    - List the main changes and migration steps needed
    Focus ONLY on understanding the version changes in this step.
    """
    step2_result = await process_migration_chunk(step2_prompt, timeout=400)
    logger.info("Step 2 (version doc review) complete")

    step1_results = f"Step 1 Results:\n{step1_result}"
    step2_results = f"Step 2 Results:\n{step2_result}"

    # Per-file migration
    migration_summaries = []
    structured_llm = llm.with_structured_output(MigrationResult)
    for root, dirs, files in os.walk(uploads_dir):
        rel_dir = os.path.relpath(root, uploads_dir)
        dst_dir = os.path.join(downloads_dir, rel_dir) if rel_dir != '.' else downloads_dir
        os.makedirs(dst_dir, exist_ok=True)
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(dst_dir, file)
            if is_code_file(file):
                logger.info("Migrating code file: %s", src_file)
                try:
                    with open(src_file, "r", encoding="utf-8") as f:
                        file_content = f.read()
                except Exception:
                    with open(src_file, "rb") as f:
                        file_content = f.read().decode("utf-8", errors="replace")
                migration_prompt = {
                    "context": (
                        f"You are a senior {code_language} developer and code migration assistant. "
                        f"Your task is to update the following file from version {fro_version} to {to_version} for the {code_language} language.\n\n"
                        f"Project Structure Analysis:\n{step1_results}\n\n"
                        f"Version Change Documentation:\n{step2_results}\n\n"
                        "--- BEGIN ORIGINAL FILE CONTENT ---\n"
                        f"{file_content}\n"
                        "--- END ORIGINAL FILE CONTENT ---"
                    ),
                    "instructions": [
                        f"Carefully review the version change documentation and project structure.",
                        f"Convert the code to version {to_version} for {code_language}.",
                        "Make all necessary code, configuration, and syntax changes.",
                        "Ensure the output is fully functional, syntactically correct, and ready to use.",
                        "Do NOT include placeholders, TODOs, or incomplete code.",
                        "Preserve all business logic and comments unless changes are required for compatibility.",
                        "Double-check for syntax errors, missing imports, and migration mistakes.",
                        "Return ONLY the complete, updated file content as plain text in the 'migrated_code' field.",
                        "In the 'summary' field, provide a concise summary (1-3 sentences) of what was changed in this file, and confirm that the code was checked for syntax and migration errors."
                    ]
                }
                result = await structured_llm.ainvoke(json.dumps(migration_prompt))
                try:
                    with open(dst_file, "w", encoding="utf-8") as f:
                        f.write(result.migrated_code)
                    logger.info("Migration result written to: %s", dst_file)
                except Exception as e:
                    logger.error("Error migrating file %s: %s", src_file, str(e))
                migration_summaries.append({
                    "filename": file,
                    "summary": result.summary,
                    "migrated_code": result.migrated_code
                })
            else:
                try:
                    with open(src_file, "rb") as src_f, open(dst_file, "wb") as dst_f:
                        dst_f.write(src_f.read())
                    logger.info("Copied non-code file: %s", src_file)
                    migration_summaries.append({
                        "filename": file,
                        "summary": "No migration needed, file copied as-is.",
                        "migrated_code": None
                    })
                except Exception as e:
                    logger.error("Failed to copy file %s: %s", src_file, str(e))
                    migration_summaries.append({
                        "filename": file,
                        "summary": f"Copy failed: {e}",
                        "migrated_code": None
                    })

    # Step 3: Review all migrated code and summarize
    step3_prompt = f"""
    STEP 3: Review Migrated Project Files

    You are to review the following migrated files for any issues, including:
    - Syntax errors
    - Annotation errors
    - Variable naming or usage issues
    - Any other migration mistakes

    Here is the list of migrated files and their summaries:
    {json.dumps([{k: v for k, v in summary.items() if k != "migrated_code"} for summary in migration_summaries], indent=2)}

    For each file, check the migrated code for correctness and compatibility with {to_version} of {code_language}.
    Then, provide a final summary with:
    - A list of filenames that were updated (no paths, just names)
    - An overview of the application or code after migration
    - Any issues found and suggestions for fixes

    Do NOT include any file paths in your summary.
    """

    step3_result = await process_migration_chunk(step3_prompt, timeout=400)
    logger.info("Step 3 (summary) complete")
    summary = step3_result
    download_links = prepare_download_links(downloads_dir)
    logger.info("Migration agent finished for job.")
    return summary, download_links, migration_summaries
