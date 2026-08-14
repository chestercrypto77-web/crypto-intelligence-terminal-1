from __future__ import annotations
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

def run(script_name:str,required:bool=True)->bool:
    command=[sys.executable,str(ROOT/'scripts'/script_name)]
    print(f'\n=== Running {script_name} ===')
    result=subprocess.run(command,cwd=ROOT,check=False)
    if result.returncode==0:return True
    if required:raise subprocess.CalledProcessError(result.returncode,command)
    print(f'WARNING: {script_name} exited with {result.returncode}; non-critical research continues.')
    return False

def main()->int:
    # Hourly loop deliberately DOES NOT rerun 5m/15m observers. Those are protected fast/decision loops.
    run('bootstrap_runtime.py')
    run('workflow_audit.py')
    run('signal_recorder.py')
    run('external_intelligence.py',required=False)
    run('external_attention.py',required=False)
    run('research_desk.py',required=False)
    run('strategy_lab.py',required=False)
    run('strategy_integrity.py')

    # Decision/risk refresh from already-recorded fast-loop evidence.
    run('risk_guardian.py')
    run('market_school.py',required=False)
    run('move_phase_intelligence.py')
    run('adaptive_attention.py',required=False)
    run('confidence_ledger.py',required=False)
    run('investment_committee.py')
    run('intelligence_hub.py')
    run('portfolio_manager.py')
    run('stop_execution_guard.py')
    run('active_trade_casefiles.py')

    # Trusted learning chain. Integrity is mandatory; optional research may fail without corrupting observations.
    run('trade_review_engine.py')
    run('trade_integrity.py')
    run('market_truth_guard.py')
    run('learning_quarantine.py')
    run('winner_failure_school.py')
    run('reverse_trade_lab.py',required=False)
    run('trade_reflection_engine.py')
    run('profit_capture_engine.py')
    run('time_intelligence.py')
    run('experience_store.py')
    run('reward_engine.py')
    run('counterfactual_lab.py',required=False)
    run('missed_clue_miner.py',required=False)
    run('lesson_promotion_board.py')
    run('adversarial_learning_challenger.py')
    run('curriculum_engine.py')
    run('learning_governor.py')

    # Deeper research / challenger layer.
    run('trade_dna.py',required=False)
    run('peak_trough_intelligence.py',required=False)
    run('pattern_miner.py',required=False)
    run('management_challenger.py',required=False)
    run('trade_diagnostics.py',required=False)
    run('trade_coach.py',required=False)
    run('committee_memory.py',required=False)
    run('learning_engine.py',required=False)
    run('challenger_arena.py',required=False)
    run('ai_scorecard.py',required=False)
    run('strategy_brain_status.py',required=False)
    run('learning_evidence_centre.py')
    run('cross_learning_bus.py',required=False)

    # Proof / health at end of cycle.
    run('collect_brain_receipts.py')
    run('observer_audit.py')
    run('runtime_watchdog.py')
    run('brain_audit.py')
    run('brain_health.py')
    return 0
if __name__=='__main__':raise SystemExit(main())
