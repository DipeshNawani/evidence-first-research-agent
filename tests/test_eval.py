import importlib.util
from pathlib import Path

from research_agent.config import Settings
from research_agent.runtime import build_agent
from research_agent.schemas import EvalCase
from research_agent.tracing import read_trace

EVAL_PATH = Path(__file__).resolve().parents[1] / "eval/run_eval.py"


async def test_eval_records_failed_quality_checks(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("evaluation", EVAL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    settings = Settings(trace_dir=tmp_path, _env_file=None)
    async with build_agent(settings) as agent:
        answer = await agent.research("Compare approaches to memory in an AI support agent.")
    case = EvalCase(
        id="quality_probe",
        question=answer.user_question,
        expected_behavior="Concrete downsides, not just feature names.",
        must_have=["concrete_downside"],
        failure_criteria=["one_sided"],
    )
    measured = module.measure(case, answer, read_trace(tmp_path, answer.meta.trace_id))
    assert measured.schema_valid
    # Current extractive mock emits only the first sentence; this should be a real FAIL.
    assert not measured.behavior_pass
