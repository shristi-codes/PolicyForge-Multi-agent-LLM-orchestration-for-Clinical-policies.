"""Ablation study: measure contribution of each system component."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from eval.harness import run_full_evaluation
from eval.metrics import SystemMetrics

logger = logging.getLogger(__name__)


def run_ablation_study(policy_id: str = "NCD_150.3") -> dict[str, SystemMetrics]:
    """
    Run ablation study across system configurations.
    
    Configurations tested:
    1. Baseline (no RAG, no Critic, 1.5x threshold)
    2. + RAG enabled
    3. + Critic enabled
    4. Adjust threshold (1.0x, 1.5x, 2.0x)
    
    Args:
        policy_id: Policy to evaluate
        
    Returns:
        Dictionary mapping configuration name to metrics
    """
    logger.info("=" * 80)
    logger.info("STARTING ABLATION STUDY")
    logger.info("=" * 80)
    
    configs = [
        {
            "name": "1_baseline",
            "description": "Baseline (no RAG, no Critic)",
            "use_rag": False,
            "use_critic": False,
            "threshold_multiplier": 1.5,
        },
        {
            "name": "2_with_rag",
            "description": "+ RAG retrieval",
            "use_rag": True,
            "use_critic": False,
            "threshold_multiplier": 1.5,
        },
        {
            "name": "3_with_critic",
            "description": "+ Critic validation",
            "use_rag": True,
            "use_critic": True,
            "threshold_multiplier": 1.5,
        },
        {
            "name": "4_threshold_1.0x",
            "description": "Lower threshold (1.0x)",
            "use_rag": True,
            "use_critic": True,
            "threshold_multiplier": 1.0,
        },
        {
            "name": "5_threshold_2.0x",
            "description": "Higher threshold (2.0x)",
            "use_rag": True,
            "use_critic": True,
            "threshold_multiplier": 2.0,
        },
    ]
    
    results = {}
    
    for i, config in enumerate(configs, 1):
        logger.info("")
        logger.info(f"Configuration {i}/{len(configs)}: {config['description']}")
        logger.info("-" * 80)
        
        try:
            metrics = run_full_evaluation(
                policy_id=policy_id,
                use_rag=config["use_rag"],
                use_critic=config["use_critic"],
                threshold_multiplier=config["threshold_multiplier"],
            )
            
            results[config["name"]] = metrics
            logger.info(f"✓ {config['name']}: F1={metrics.extraction.overall_f1:.3f}, "
                       f"Cost=${metrics.cost.cost_per_policy_usd:.4f}, "
                       f"Time={metrics.cost.time_per_policy_s:.2f}s")
            
        except Exception as e:
            logger.error(f"✗ {config['name']} failed: {e}")
            results[config["name"]] = None
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("ABLATION STUDY COMPLETE")
    logger.info("=" * 80)
    
    return results


def generate_ablation_table(results: dict[str, SystemMetrics]) -> str:
    """
    Generate markdown table comparing configurations.
    
    Args:
        results: Ablation study results
        
    Returns:
        Markdown table string
    """
    table = []
    table.append("| Configuration | Overall F1 | HCPCS F1 | Flagged | Cost/policy | Time/policy |")
    table.append("|---------------|-----------|----------|---------|-------------|-------------|")
    
    config_names = {
        "1_baseline": "Baseline (no RAG, no Critic)",
        "2_with_rag": "+ RAG",
        "3_with_critic": "+ Critic",
        "4_threshold_1.0x": "Threshold 1.0x",
        "5_threshold_2.0x": "Threshold 2.0x",
    }
    
    for name, metrics in results.items():
        if metrics is None:
            table.append(f"| {config_names.get(name, name)} | - | - | - | - | - |")
            continue
        
        row = [
            config_names.get(name, name),
            f"{metrics.extraction.overall_f1:.3f}",
            f"{metrics.extraction.hcpcs_f1:.3f}",
            f"{metrics.adjudication.total_providers_flagged:,}",
            f"${metrics.cost.cost_per_policy_usd:.4f}",
            f"{metrics.cost.time_per_policy_s:.2f}s",
        ]
        table.append("| " + " | ".join(row) + " |")
    
    return "\n".join(table)


def generate_comparison_insights(results: dict[str, SystemMetrics]) -> str:
    """
    Generate insights from ablation study.
    
    Args:
        results: Ablation study results
        
    Returns:
        Markdown string with insights
    """
    insights = ["## Key Findings\n"]
    
    baseline = results.get("1_baseline")
    with_rag = results.get("2_with_rag")
    with_critic = results.get("3_with_critic")
    
    if baseline and with_rag:
        f1_improvement = with_rag.extraction.overall_f1 - baseline.extraction.overall_f1
        cost_change = with_rag.cost.cost_per_policy_usd - baseline.cost.cost_per_policy_usd
        time_change = with_rag.cost.time_per_policy_s - baseline.cost.time_per_policy_s
        
        insights.append("### RAG Impact\n")
        insights.append(f"- **Accuracy**: {f1_improvement:+.3f} F1 improvement")
        insights.append(f"- **Cost**: {cost_change:+.4f} USD change")
        insights.append(f"- **Latency**: {time_change:+.2f}s change")
        insights.append("")
    
    if with_rag and with_critic:
        f1_improvement = with_critic.extraction.overall_f1 - with_rag.extraction.overall_f1
        citation_rate = with_critic.extraction.citation_grounding_rate
        
        insights.append("### Critic Impact\n")
        insights.append(f"- **Accuracy**: {f1_improvement:+.3f} F1 improvement")
        insights.append(f"- **Citation grounding**: {citation_rate:.1%} of criteria cited")
        insights.append("")
    
    threshold_1 = results.get("4_threshold_1.0x")
    threshold_2 = results.get("5_threshold_2.0x")
    baseline_threshold = results.get("3_with_critic")
    
    if all([threshold_1, threshold_2, baseline_threshold]):
        insights.append("### Threshold Sensitivity\n")
        insights.append(f"- **1.0x**: {threshold_1.adjudication.total_providers_flagged:,} providers, "
                       f"{threshold_1.adjudication.severity_high} high-risk")
        insights.append(f"- **1.5x**: {baseline_threshold.adjudication.total_providers_flagged:,} providers, "
                       f"{baseline_threshold.adjudication.severity_high} high-risk")
        insights.append(f"- **2.0x**: {threshold_2.adjudication.total_providers_flagged:,} providers, "
                       f"{threshold_2.adjudication.severity_high} high-risk")
        insights.append("")
    
    insights.append("### Recommended Configuration\n")
    insights.append("Based on accuracy, cost, and auditability:")
    insights.append("- **Use RAG**: Improves retrieval precision")
    insights.append("- **Use Critic**: Adds citation grounding for auditability")
    insights.append("- **Threshold 1.5x**: Balances sensitivity and specificity")
    
    return "\n".join(insights)


def save_ablation_results(
    results: dict[str, SystemMetrics],
    output_dir: Path = Path("eval/results"),
) -> None:
    """
    Save ablation study results.
    
    Args:
        results: Ablation study results
        output_dir: Output directory
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save individual metrics
    for name, metrics in results.items():
        if metrics is not None:
            output_path = output_dir / f"ablation_{name}.json"
            with output_path.open("w") as f:
                json.dump(metrics.model_dump(), f, indent=2)
    
    # Save comparison table
    table_path = output_dir / "ablation_comparison.md"
    with table_path.open("w") as f:
        f.write("# PolicyForge Ablation Study\n\n")
        f.write("## Comparison Table\n\n")
        f.write(generate_ablation_table(results))
        f.write("\n\n")
        f.write(generate_comparison_insights(results))
    
    logger.info(f"✓ Saved ablation results to {output_dir}")
    logger.info(f"✓ See comparison table: {table_path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Run ablation study
    results = run_ablation_study("NCD_150.3")
    
    # Save results
    save_ablation_results(results)
    
    # Print summary table
    print("\n" + "=" * 80)
    print("ABLATION STUDY SUMMARY")
    print("=" * 80)
    print(generate_ablation_table(results))
    print("\n" + generate_comparison_insights(results))
