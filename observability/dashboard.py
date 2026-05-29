# observability/dashboard.py

from observability.metrics import load_traces, compute_metrics


# ── Helpers defined BEFORE print_dashboard ──────────────────────────────────

def _print_header(count: int) -> None:
    print(f"\n{'='*62}")
    print(f"  AGENT OBSERVABILITY DASHBOARD  —  last {count} runs")
    print(f"{'='*62}")


def _print_metrics(metrics: dict) -> None:
    print(f"\n  AGGREGATE METRICS")
    print(f"  {'─'*58}")
    print(f"  Total runs:        {metrics.get('total_runs', 0)}")
    print(f"  Completion rate:   {metrics.get('completion_rate', 0):.0%}")
    print(f"  Error rate:        {metrics.get('error_rate', 0):.0%}")
    print(f"  Abstention rate:   {metrics.get('abstention_rate', 0):.0%}")
    print(f"  Latency p50:       {metrics.get('latency_p50_s', 0)}s")
    print(f"  Latency p90:       {metrics.get('latency_p90_s', 0)}s")
    print(f"  Avg relevance:     {metrics.get('avg_relevance', 'n/a')}")
    print(f"  HITL rate:         {metrics.get('hitl_rate', 0):.0%}")


def _print_recent_runs(traces: list[dict]) -> None:
    print(f"\n  RECENT RUNS")
    print(f"  {'─'*58}")
    print(f"  {'ID':<10} {'Status':<10} {'Latency':>8}  Question")
    print(f"  {'─'*58}")

    for t in traces:
        run_id   = t.get("run_id", "?")[:8]
        status   = t.get("status", "?")
        duration = f"{t.get('duration_s', 0)}s"
        question = t.get("question", "")[:38]
        icon     = "✅" if status == "success" else "❌"
        print(f"  {run_id:<10} {icon} {status:<8} {duration:>8}  {question}")


def _print_span_breakdown(span_latencies: dict) -> None:
    if not span_latencies:
        return

    print(f"\n  AVERAGE SPAN LATENCY")
    print(f"  {'─'*58}")

    for name, avg in sorted(span_latencies.items(),
                             key=lambda x: x[1], reverse=True):
        bar_len = min(int(avg * 0.5), 30)
        bar     = "█" * bar_len
        print(f"  {name:<20} {avg:>8}s  {bar}")


def _print_alerts(metrics: dict) -> None:
    alerts = []

    if metrics.get("error_rate", 0) > 0.10:
        alerts.append(f"⚠️  Error rate {metrics['error_rate']:.0%} exceeds 10% threshold")
    if metrics.get("latency_p90_s", 0) > 4.0:
        alerts.append(f"⚠️  p90 latency {metrics['latency_p90_s']}s exceeds 4s target")
    if metrics.get("avg_relevance") and metrics["avg_relevance"] < 0.55:
        alerts.append(f"⚠️  Avg relevance {metrics['avg_relevance']} below 0.55 threshold")
    if metrics.get("hitl_rate", 0) > 0.30:
        alerts.append(f"⚠️  HITL rate {metrics['hitl_rate']:.0%} exceeds 30%")

    if alerts:
        print(f"\n  ALERTS")
        print(f"  {'─'*58}")
        for alert in alerts:
            print(f"  {alert}")

    print(f"\n{'='*62}\n")


# ── Main function ────────────────────────────────────────────────────────────

def print_dashboard(last_n: int = 20) -> None:
    traces  = load_traces(last_n=last_n)
    metrics = compute_metrics(traces)

    if not traces or not metrics:
        print("No traces found. Run the agent first.")
        return

    _print_header(len(traces))
    _print_metrics(metrics)
    _print_recent_runs(traces[:10])
    _print_span_breakdown(metrics.get("span_latencies", {}))
    _print_alerts(metrics)