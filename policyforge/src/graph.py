"""LangGraph state machine — 6-node PolicyForge pipeline with conditional routing."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from src.agents.adjudicator import adjudicate_edit
from src.agents.compiler import compile_criteria_to_edit
from src.agents.extractor import extract_criteria_from_policy
from src.rag import Chunk, build_hybrid_retriever
from src.schema import CompiledEdit, FlaggedProvider, PolicyCriteria

load_dotenv()

logger = logging.getLogger(__name__)

# Data paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POLICIES_DIR = DATA_DIR / "policies"
RAG_CACHE_DIR = DATA_DIR / "rag_cache"
ANCHOR_POLICY_TXT = POLICIES_DIR / "NCD_150.3.txt"


class PolicyForgeState(TypedDict, total=False):
    """
    State passed between LangGraph nodes.
    
    Uses TypedDict for LangGraph compatibility while maintaining type hints.
    """
    # Input
    policy_id: str
    policy_path: str
    use_rag: bool  # Enable/disable RAG retrieval
    
    # Pipeline data
    raw_policy_text: str | None
    retrieved_chunks: list[Chunk]  # RAG chunks
    retrieval_metrics: dict[str, float]
    extracted_criteria: PolicyCriteria | None
    compiled_edit: CompiledEdit | None
    flagged_providers: list[FlaggedProvider]
    
    # Validation & control flow
    validation_status: Literal["pending", "passed", "failed"]
    validation_message: str
    retry_count: int
    
    # Observability
    node_costs: dict[str, float]
    node_latencies_ms: dict[str, float]
    
    # Output
    summary: str | None
    error: str | None


def retriever_node(state: PolicyForgeState) -> PolicyForgeState:
    """
    Node 1: Read policy text and optionally retrieve relevant chunks via RAG.
    
    Args:
        state: Must contain policy_id and policy_path
        
    Returns:
        State with raw_policy_text and retrieved_chunks populated
    """
    start_time = time.time()
    logger.info("[RETRIEVER] Loading policy from %s", state.get("policy_path"))
    
    policy_path = Path(state["policy_path"])
    if not policy_path.exists():
        logger.error("[RETRIEVER] Policy file not found: %s", policy_path)
        state["error"] = f"Policy file not found: {policy_path}"
        state["raw_policy_text"] = None
        state["retrieved_chunks"] = []
    else:
        state["raw_policy_text"] = policy_path.read_text(encoding="utf-8")
        logger.info(
            "[RETRIEVER] Loaded %d chars from policy %s",
            len(state["raw_policy_text"]),
            state["policy_id"],
        )
        
        # RAG retrieval (optional)
        if state.get("use_rag", False):
            try:
                logger.info("[RETRIEVER] Building hybrid RAG index...")
                retriever = build_hybrid_retriever(
                    state["raw_policy_text"],
                    doc_id=state["policy_id"],
                    cache_dir=RAG_CACHE_DIR,
                )
                
                # Retrieve relevant chunks for frequency/eligibility criteria
                query = (
                    "frequency limit months coverage eligibility "
                    "HCPCS procedure codes bone mass measurement"
                )
                chunks, metrics = retriever.retrieve_with_context(
                    query,
                    top_k=5,
                    retrieval_k=20,
                )
                
                state["retrieved_chunks"] = chunks
                state["retrieval_metrics"] = metrics
                
                logger.info(
                    "[RETRIEVER] Retrieved %d chunks (top score: %.3f, sections: %d)",
                    metrics["num_results"],
                    metrics["top_score"],
                    metrics["unique_sections"],
                )
            except Exception as exc:
                logger.warning("[RETRIEVER] RAG failed, using full text: %s", exc)
                state["retrieved_chunks"] = []
                state["retrieval_metrics"] = {}
        else:
            state["retrieved_chunks"] = []
            state["retrieval_metrics"] = {}
    
    elapsed_ms = (time.time() - start_time) * 1000
    state["node_latencies_ms"]["retriever"] = elapsed_ms
    state["node_costs"]["retriever"] = 0.0  # File read + local embeddings
    
    return state


def extractor_node(state: PolicyForgeState) -> PolicyForgeState:
    """
    Node 2: Extract structured criteria from policy text using LLM.
    
    Args:
        state: Must contain raw_policy_text and policy_id
        
    Returns:
        State with extracted_criteria populated
    """
    start_time = time.time()
    logger.info("[EXTRACTOR] Extracting criteria from policy %s", state["policy_id"])
    
    if not state.get("raw_policy_text"):
        logger.error("[EXTRACTOR] No policy text available")
        state["error"] = "Cannot extract: no policy text loaded"
        state["extracted_criteria"] = None
        state["validation_status"] = "failed"
        return state
    
    try:
        # Try to use cached criteria first to avoid API call
        cache_json = POLICIES_DIR / f"{state['policy_id']}_criteria.json"
        if cache_json.exists():
            logger.info("[EXTRACTOR] Using cached criteria from %s", cache_json)
            import json
            criteria_data = json.loads(cache_json.read_text(encoding="utf-8"))
            from src.schema import PolicyCriteria
            criteria = PolicyCriteria(**criteria_data)
        else:
            # Call LLM extraction
            policy_path = Path(state["policy_path"])
            criteria = extract_criteria_from_policy(
                policy_path,
                policy_id=state["policy_id"],
            )
        
        state["extracted_criteria"] = criteria
        
        logger.info(
            "[EXTRACTOR] Extracted criteria: freq=%s months, HCPCS=%s",
            criteria.frequency_limit_months,
            criteria.target_hcpcs_codes,
        )
        
        # Rough cost estimate for LLM call (cached or actual)
        state["node_costs"]["extractor"] = 0.0 if cache_json.exists() else 0.01
        
    except Exception as exc:
        logger.error("[EXTRACTOR] Extraction failed: %s", exc)
        state["error"] = f"Extraction failed: {exc}"
        state["extracted_criteria"] = None
        state["validation_status"] = "failed"
    
    elapsed_ms = (time.time() - start_time) * 1000
    state["node_latencies_ms"]["extractor"] = elapsed_ms
    
    return state


def critic_node(state: PolicyForgeState) -> PolicyForgeState:
    """
    Node 3: Validate extracted criteria (hallucination gate).
    
    Checks:
    1. Criteria object is not None
    2. frequency_limit_months is set and > 0
    3. target_hcpcs_codes is non-empty
    
    Args:
        state: Must contain extracted_criteria
        
    Returns:
        State with validation_status set to "passed" or "failed"
    """
    start_time = time.time()
    logger.info("[CRITIC] Validating extracted criteria")
    
    criteria = state.get("extracted_criteria")
    
    if criteria is None:
        state["validation_status"] = "failed"
        state["validation_message"] = "Extraction returned None"
        logger.warning("[CRITIC] Validation FAILED: No criteria extracted")
    elif not criteria.frequency_limit_months or criteria.frequency_limit_months <= 0:
        state["validation_status"] = "failed"
        state["validation_message"] = (
            f"Invalid frequency_limit_months: {criteria.frequency_limit_months}"
        )
        logger.warning("[CRITIC] Validation FAILED: %s", state["validation_message"])
    elif not criteria.target_hcpcs_codes:
        state["validation_status"] = "failed"
        state["validation_message"] = "No target_hcpcs_codes found"
        logger.warning("[CRITIC] Validation FAILED: %s", state["validation_message"])
    else:
        state["validation_status"] = "passed"
        state["validation_message"] = (
            f"Criteria validated: {criteria.frequency_limit_months} months, "
            f"{len(criteria.target_hcpcs_codes)} HCPCS codes"
        )
        logger.info("[CRITIC] Validation PASSED: %s", state["validation_message"])
    
    elapsed_ms = (time.time() - start_time) * 1000
    state["node_latencies_ms"]["critic"] = elapsed_ms
    state["node_costs"]["critic"] = 0.0  # Validation is deterministic
    
    return state


def compiler_node(state: PolicyForgeState) -> PolicyForgeState:
    """
    Node 4: Compile criteria into executable edit logic.
    
    Args:
        state: Must contain extracted_criteria
        
    Returns:
        State with compiled_edit populated
    """
    start_time = time.time()
    logger.info("[COMPILER] Compiling edit from criteria")
    
    criteria = state.get("extracted_criteria")
    if not criteria:
        logger.error("[COMPILER] No criteria available")
        state["error"] = "Cannot compile: no criteria"
        state["compiled_edit"] = None
        return state
    
    try:
        edit = compile_criteria_to_edit(criteria, edit_type="frequency")
        state["compiled_edit"] = edit
        
        logger.info("[COMPILER] Compiled edit: %s", edit.threshold_expression)
        
        state["node_costs"]["compiler"] = 0.0  # Deterministic compilation
        
    except Exception as exc:
        logger.error("[COMPILER] Compilation failed: %s", exc)
        state["error"] = f"Compilation failed: {exc}"
        state["compiled_edit"] = None
    
    elapsed_ms = (time.time() - start_time) * 1000
    state["node_latencies_ms"]["compiler"] = elapsed_ms
    
    return state


def adjudicator_node(state: PolicyForgeState) -> PolicyForgeState:
    """
    Node 5: Apply compiled edit to CMS Part B data and flag providers.
    
    Args:
        state: Must contain compiled_edit
        
    Returns:
        State with flagged_providers populated
    """
    start_time = time.time()
    logger.info("[ADJUDICATOR] Applying edit to Part B data")
    
    edit = state.get("compiled_edit")
    if not edit:
        logger.error("[ADJUDICATOR] No compiled edit available")
        state["error"] = "Cannot adjudicate: no compiled edit"
        state["flagged_providers"] = []
        return state
    
    try:
        flagged = adjudicate_edit(edit)
        state["flagged_providers"] = flagged
        
        logger.info(
            "[ADJUDICATOR] Flagged %d providers (severity breakdown: %s)",
            len(flagged),
            {
                sev: sum(1 for p in flagged if p.severity == sev)
                for sev in ["critical", "high", "medium", "low"]
            },
        )
        
        state["node_costs"]["adjudicator"] = 0.0  # Data processing, no API cost
        
    except Exception as exc:
        logger.error("[ADJUDICATOR] Adjudication failed: %s", exc)
        state["error"] = f"Adjudication failed: {exc}"
        state["flagged_providers"] = []
    
    elapsed_ms = (time.time() - start_time) * 1000
    state["node_latencies_ms"]["adjudicator"] = elapsed_ms
    
    return state


def explainer_node(state: PolicyForgeState) -> PolicyForgeState:
    """
    Node 6: Format flagged providers into human-readable summary.
    
    Args:
        state: Must contain flagged_providers
        
    Returns:
        State with summary populated
    """
    start_time = time.time()
    logger.info("[EXPLAINER] Generating summary report")
    
    flagged = state.get("flagged_providers", [])
    criteria = state.get("extracted_criteria")
    
    lines = [
        "=" * 80,
        "POLICYFORGE ADJUDICATION REPORT",
        "=" * 80,
        f"Policy: {state['policy_id']}",
        "",
    ]
    
    if criteria:
        lines.extend([
            "Policy Rules:",
            f"  - Frequency: Once every {criteria.frequency_limit_months} months",
            f"  - HCPCS codes: {', '.join(criteria.target_hcpcs_codes)}",
            f"  - Eligible conditions: {len(criteria.eligible_conditions)}",
            "",
        ])
    
    lines.extend([
        f"Total Providers Flagged: {len(flagged)}",
        "",
    ])
    
    if flagged:
        # Severity breakdown
        severity_counts = {}
        for p in flagged:
            severity_counts[p.severity] = severity_counts.get(p.severity, 0) + 1
        
        lines.append("Severity Distribution:")
        for sev in ["critical", "high", "medium", "low"]:
            count = severity_counts.get(sev, 0)
            pct = 100.0 * count / len(flagged)
            lines.append(f"  {sev.upper():>8}: {count:>5} ({pct:>5.1f}%)")
        
        lines.extend([
            "",
            "Top 10 High-Risk Providers:",
            "-" * 80,
        ])
        
        for i, provider in enumerate(flagged[:10], 1):
            lines.append(
                f"{i:>2}. NPI {provider.npi} | {provider.provider_type}"
            )
            lines.append(
                f"    Utilization: {provider.tot_srvcs} srvcs / {provider.tot_benes} benes "
                f"= {provider.avg_srvcs_per_bene:.2f} srvcs/bene"
            )
            lines.append(
                f"    Anomaly: {provider.anomaly_score:.2f}x expected | "
                f"Severity: {provider.severity.upper()}"
            )
            lines.append(f"    Reason: {provider.flag_reason[:120]}...")
            lines.append("")
    else:
        lines.append("No providers flagged. All utilization within policy limits.")
    
    # Pipeline metrics
    lines.extend([
        "=" * 80,
        "PIPELINE METRICS",
        "=" * 80,
    ])
    
    total_latency = sum(state.get("node_latencies_ms", {}).values())
    total_cost = sum(state.get("node_costs", {}).values())
    
    lines.append(f"Total latency: {total_latency:.0f}ms")
    lines.append(f"Estimated cost: ${total_cost:.4f}")
    lines.append("")
    lines.append("Per-node breakdown:")
    for node in ["retriever", "extractor", "critic", "compiler", "adjudicator", "explainer"]:
        latency = state.get("node_latencies_ms", {}).get(node, 0)
        cost = state.get("node_costs", {}).get(node, 0)
        lines.append(f"  {node:>12}: {latency:>6.0f}ms | ${cost:.4f}")
    
    lines.append("=" * 80)
    
    state["summary"] = "\n".join(lines)
    
    elapsed_ms = (time.time() - start_time) * 1000
    state["node_latencies_ms"]["explainer"] = elapsed_ms
    state["node_costs"]["explainer"] = 0.0
    
    logger.info("[EXPLAINER] Summary generated (%d chars)", len(state["summary"]))
    
    return state


def should_retry_extraction(state: PolicyForgeState) -> Literal["retry", "proceed", "fail"]:
    """
    Conditional routing after critic node.
    
    Returns:
        "proceed" if validation passed
        "retry" if validation failed and retries remain
        "fail" if validation failed and no retries left
    """
    validation = state.get("validation_status")
    retry_count = state.get("retry_count", 0)
    max_retries = 0  # Disable retries for now (API key may be missing)
    
    if validation == "passed":
        logger.info("[ROUTER] Validation passed → proceeding to compiler")
        return "proceed"
    elif retry_count < max_retries:
        logger.warning("[ROUTER] Validation failed, retry %d/%d", retry_count + 1, max_retries)
        state["retry_count"] = retry_count + 1
        return "retry"
    else:
        logger.error("[ROUTER] Validation failed → terminating")
        state["error"] = f"Validation failed: {state.get('validation_message')}"
        return "fail"


def build_graph() -> StateGraph:
    """
    Construct the 6-node PolicyForge LangGraph with conditional routing.
    
    Flow:
        START → retriever → extractor → critic
                                           ↓
                               [validation check]
                                    ↙     ↓     ↘
                              retry  proceed   fail
                                ↓      ↓        ↓
                           extractor compiler  END
                                      ↓
                                 adjudicator → explainer → END
    """
    workflow = StateGraph(PolicyForgeState)
    
    # Add all 6 nodes
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("compiler", compiler_node)
    workflow.add_node("adjudicator", adjudicator_node)
    workflow.add_node("explainer", explainer_node)
    
    # Linear flow: START → retriever → extractor → critic
    workflow.add_edge(START, "retriever")
    workflow.add_edge("retriever", "extractor")
    workflow.add_edge("extractor", "critic")
    
    # Conditional routing after critic
    workflow.add_conditional_edges(
        "critic",
        should_retry_extraction,
        {
            "proceed": "compiler",
            "retry": "extractor",
            "fail": END,
        },
    )
    
    # Success path: compiler → adjudicator → explainer → END
    workflow.add_edge("compiler", "adjudicator")
    workflow.add_edge("adjudicator", "explainer")
    workflow.add_edge("explainer", END)
    
    logger.info("LangGraph workflow constructed with 6 nodes + conditional routing")
    
    return workflow


def run_pipeline(
    policy_id: str = "NCD_150.3",
    policy_path: Path | str = ANCHOR_POLICY_TXT,
    *,
    use_rag: bool = False,
) -> PolicyForgeState:
    """
    Execute the full PolicyForge pipeline on a given policy.
    
    Args:
        policy_id: Policy identifier
        policy_path: Path to policy text file
        use_rag: Enable hybrid RAG retrieval
        
    Returns:
        Final state with summary and flagged providers
    """
    logger.info("=" * 80)
    logger.info("STARTING POLICYFORGE PIPELINE")
    logger.info("Policy: %s", policy_id)
    logger.info("RAG enabled: %s", use_rag)
    logger.info("=" * 80)
    
    # Initialize state
    initial_state: PolicyForgeState = {
        "policy_id": policy_id,
        "policy_path": str(policy_path),
        "use_rag": use_rag,
        "raw_policy_text": None,
        "retrieved_chunks": [],
        "retrieval_metrics": {},
        "extracted_criteria": None,
        "compiled_edit": None,
        "flagged_providers": [],
        "validation_status": "pending",
        "validation_message": "",
        "retry_count": 0,
        "node_costs": {},
        "node_latencies_ms": {},
        "summary": None,
        "error": None,
    }
    
    # Build and compile graph
    workflow = build_graph()
    app = workflow.compile()
    
    # Execute
    logger.info("Executing pipeline...")
    start_time = time.time()
    
    final_state = app.invoke(initial_state)
    
    total_time = time.time() - start_time
    logger.info("Pipeline completed in %.2fs", total_time)
    
    return final_state


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    
    import sys
    
    # Check for --rag flag
    use_rag = "--rag" in sys.argv
    
    # Run the full pipeline
    final_state = run_pipeline(use_rag=use_rag)
    
    # Print results
    summary = final_state.get("summary")
    if summary:
        print("\n" + summary)
    else:
        print("\nNo summary generated (pipeline may have terminated early)")
    
    # Print RAG metrics if used
    if final_state.get("retrieved_chunks"):
        print("\n" + "=" * 80)
        print("RAG RETRIEVAL METRICS")
        print("=" * 80)
        metrics = final_state.get("retrieval_metrics", {})
        chunks = final_state.get("retrieved_chunks", [])
        print(f"Chunks retrieved: {len(chunks)}")
        print(f"Top score: {metrics.get('top_score', 0):.3f}")
        print(f"Mean score: {metrics.get('mean_score', 0):.3f}")
        print(f"Unique sections: {metrics.get('unique_sections', 0)}")
        print("\nTop 3 Retrieved Chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\n{i}. Section: {chunk.section or 'Unknown'}")
            print(f"   Chars: {chunk.start_char}-{chunk.end_char}")
            print(f"   Preview: {chunk.text[:150]}...")
    
    if final_state.get("error"):
        print(f"\nERROR: {final_state['error']}")
    
    # Exit code based on success
    sys.exit(0 if not final_state.get("error") else 1)
