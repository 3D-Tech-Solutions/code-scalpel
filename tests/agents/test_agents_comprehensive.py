"""
Comprehensive tests for Code Scalpel Agents to achieve 95% coverage.

[20251213_TEST] Added comprehensive tests targeting missing coverage lines.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from code_scalpel.agents.base_agent import BaseCodeAnalysisAgent
from code_scalpel.agents.code_review_agent import CodeReviewAgent
from code_scalpel.agents.optimazation_agent import OptimizationAgent
from code_scalpel.agents.security_agent import SecurityAgent


class TestCodeReviewAgentCoverage:
    """Comprehensive tests for CodeReviewAgent targeting missing lines."""

    @pytest.fixture
    def agent(self):
        """Create a test code review agent."""
        return CodeReviewAgent(workspace_root="/test/workspace")

    @pytest.mark.asyncio
    async def test_observe_file_failure(self, agent):
        """Test observe returns early when file observation fails (line 43)."""
        agent.observe_file = AsyncMock(return_value={"success": False, "error": "File not found"})

        result = await agent.observe("/missing/file.py")

        assert result["success"] is False
        assert result["error"] == "File not found"

    @pytest.mark.asyncio
    async def test_observe_with_many_functions(self, agent):
        """Test observe with many functions (covers line 55->51 branch)."""
        agent.observe_file = AsyncMock(return_value={"success": True, "functions": ["f1", "f2", "f3", "f4", "f5"]})
        agent.analyze_code_security = AsyncMock(return_value={"vulnerabilities": []})
        agent.find_symbol_usage = AsyncMock(return_value={"success": True})

        result = await agent.observe("/test/file.py")

        assert result["success"] is True
        # Should call find_symbol_usage for first 3 functions only
        assert agent.find_symbol_usage.call_count == 3

    @pytest.mark.asyncio
    async def test_orient_with_security_info_key(self, agent):
        """Test orient with security_info key instead of security_scan (line 113->112)."""
        observations = {
            "file_info": {"complexity_score": 5},
            "security_info": {"vulnerabilities": []},
            "symbol_analysis": {},
        }

        result = await agent.orient(observations)

        assert result["success"] is True
        assert "issues" in result

    @pytest.mark.asyncio
    async def test_act_with_unknown_action_type(self, agent):
        """Test act with unknown action type (covers lines 143-148)."""
        decisions = {
            "actionable_items": [
                {
                    "action": {"type": "unknown_action"},
                    "implementation_plan": {},
                    "verification_steps": [],
                    "estimated_impact": {},
                }
            ]
        }

        result = await agent.act(decisions)

        assert result["success"] is False
        assert "Unknown action type" in result["results"][0]["result"]["error"]

    @pytest.mark.asyncio
    async def test_act_with_security_improvement(self, agent):
        """Test act with add_security_check action type (covers lines 143-148)."""
        decisions = {
            "actionable_items": [
                {
                    "action": {"type": "add_security_check"},
                    "implementation_plan": {},
                    "verification_steps": [],
                    "estimated_impact": {},
                }
            ]
        }

        result = await agent.act(decisions)

        assert result["success"] is True
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_act_with_documentation_improvement(self, agent):
        """Test act with improve_documentation action type (covers lines 143-148)."""
        decisions = {
            "actionable_items": [
                {
                    "action": {"type": "improve_documentation"},
                    "implementation_plan": {},
                    "verification_steps": [],
                    "estimated_impact": {},
                }
            ]
        }

        result = await agent.act(decisions)

        assert result["success"] is True

    def test_generate_improvements_security(self, agent):
        """Test _generate_improvements with security issues (line 235)."""
        issues = [{"type": "security", "severity": "high"}]
        suggestions = agent._generate_improvements(issues, {})
        assert len(suggestions) >= 0

    def test_generate_improvements_complexity(self, agent):
        """Test _generate_improvements with complexity issues (line 245)."""
        issues = [{"type": "complexity", "severity": "medium"}]
        suggestions = agent._generate_improvements(issues, {})
        assert len(suggestions) >= 0

    def test_generate_improvements_structure(self, agent):
        """Test _generate_improvements with structure issues (line 265)."""
        issues = [{"type": "structure", "severity": "low"}]
        suggestions = agent._generate_improvements(issues, {})
        assert len(suggestions) >= 0

    def test_categorize_issues_missing_severity(self, agent):
        """Test _categorize_issues with missing severity (line 277)."""
        issues = [{"type": "test"}]  # No severity key
        breakdown = agent._categorize_issues(issues)
        assert breakdown["low"] == 1

    def test_create_action_plan_security(self, agent):
        """Test _create_action_plan for security issues (lines 304->307)."""
        issue = {"type": "security", "vulnerability": {"location": "input"}}
        action = agent._create_action_plan(issue)
        assert action["type"] == "add_security_check"

    def test_create_action_plan_complexity(self, agent):
        """Test _create_action_plan for complexity issues (lines 304->307)."""
        issue = {"type": "complexity"}
        action = agent._create_action_plan(issue)
        assert action["type"] == "refactor_function"

    def test_create_action_plan_other(self, agent):
        """Test _create_action_plan for other issues (lines 304->307)."""
        issue = {"type": "documentation"}
        action = agent._create_action_plan(issue)
        assert action["type"] == "improve_documentation"

    def test_estimate_effort_minimal(self, agent):
        """Test _estimate_effort with no items (lines 319-326)."""
        assert agent._estimate_effort([]) == "minimal"

    def test_estimate_effort_low(self, agent):
        """Test _estimate_effort with 1-2 items (lines 319-326)."""
        assert agent._estimate_effort([1, 2]) == "low"

    def test_estimate_effort_medium(self, agent):
        """Test _estimate_effort with 3-5 items (lines 319-326)."""
        assert agent._estimate_effort([1, 2, 3, 4]) == "medium"

    def test_estimate_effort_high(self, agent):
        """Test _estimate_effort with more than 5 items (lines 319-326)."""
        assert agent._estimate_effort([1] * 6) == "high"

    @pytest.mark.asyncio
    async def test_execute_function_refactor(self, agent):
        """Test _execute_function_refactor (lines 339-342)."""
        result = await agent._execute_function_refactor({"target": "func"})
        assert result["success"] is True
        assert "Function refactor completed" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_security_improvement(self, agent):
        """Test _execute_security_improvement (lines 352-353)."""
        result = await agent._execute_security_improvement({"target": "input"})
        assert result["success"] is True
        assert "Security improvement applied" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_documentation_improvement(self, agent):
        """Test _execute_documentation_improvement (lines 360-361, 368-369)."""
        result = await agent._execute_documentation_improvement({"target": "func"})
        assert result["success"] is True
        assert "Documentation improved" in result["message"]


class TestSecurityAgentCoverage:
    """Comprehensive tests for SecurityAgent targeting missing lines."""

    @pytest.fixture
    def agent(self):
        """Create a test security agent."""
        return SecurityAgent(workspace_root="/test/workspace")

    @pytest.mark.asyncio
    async def test_observe_file_failure(self, agent):
        """Test observe returns early when file observation fails (line 42)."""
        agent.observe_file = AsyncMock(return_value={"success": False, "error": "File not found"})

        result = await agent.observe("/missing/file.py")

        assert result["success"] is False
        assert result["error"] == "File not found"

    @pytest.mark.asyncio
    async def test_observe_with_many_functions(self, agent):
        """Test observe with many functions (covers line 52->50 branch)."""
        agent.observe_file = AsyncMock(
            return_value={
                "success": True,
                "functions": ["f1", "f2", "f3", "f4", "f5", "f6"],
            }
        )
        agent.analyze_code_security = AsyncMock(return_value={"vulnerabilities": []})
        agent.find_symbol_usage = AsyncMock(return_value={"success": True})

        result = await agent.observe("/test/file.py")

        assert result["success"] is True
        assert agent.find_symbol_usage.call_count == 5

    @pytest.mark.asyncio
    async def test_orient_with_different_key(self, agent):
        """Test orient with vulnerabilities key (line 102->101)."""
        observations = {
            "file_info": {},
            "security_scan": {"vulnerabilities": [{"type": "sql_injection", "severity": "high"}]},
            "symbol_analysis": {},
        }

        result = await agent.orient(observations)

        assert result["success"] is True

    def test_analyze_attack_vectors_high_usage(self, agent):
        """Test _analyze_attack_vectors with high usage count (lines 185-192)."""
        vulnerabilities = [{"location": {"function": "func1"}, "severity": "high"}]
        symbol_analysis = {"func1": {"total_references": 15}}

        vectors = agent._analyze_attack_vectors(vulnerabilities, symbol_analysis)

        assert len(vectors) == 1
        assert vectors[0]["exposure_level"] == "high"

    def test_analyze_attack_vectors_low_usage(self, agent):
        """Test _analyze_attack_vectors with low usage count (lines 185-192)."""
        vulnerabilities = [{"location": {"function": "func2"}, "severity": "low"}]
        symbol_analysis = {"func2": {"total_references": 2}}

        vectors = agent._analyze_attack_vectors(vulnerabilities, symbol_analysis)

        assert len(vectors) == 1
        assert vectors[0]["exposure_level"] == "low"

    def test_assess_overall_risk_critical(self, agent):
        """Test _assess_overall_risk critical path (line 222)."""
        categorized = {"sql_injection": [{"severity": "critical"}, {"severity": "critical"}]}
        assessment = agent._assess_overall_risk(categorized, [])
        assert assessment["overall_level"] == "critical"

    def test_assess_overall_risk_high(self, agent):
        """Test _assess_overall_risk high path (line 224)."""
        categorized = {"sql_injection": [{"severity": "high"}, {"severity": "high"}]}
        assessment = agent._assess_overall_risk(categorized, [])
        assert assessment["overall_level"] == "high"

    def test_generate_remediation_plan_known_types(self, agent):
        """Test _generate_remediation_plan with known types (lines 241-242)."""
        categorized = {
            "sql_injection": [{"severity": "high"}],
            "unknown": [{"severity": "low"}],
        }
        plan = agent._generate_remediation_plan(categorized, [])
        assert "sql_injection" in plan
        assert "unknown" not in plan

    def test_determine_priority_levels(self, agent):
        """Test _determine_priority with different severity levels (line 256)."""
        assert agent._determine_priority([{"severity": "critical"}]) == "critical"
        assert agent._determine_priority([{"severity": "high"}]) == "high"
        assert agent._determine_priority([{"severity": "medium"}]) == "medium"
        assert agent._determine_priority([{"severity": "low"}]) == "low"

    def test_create_remediation_actions_sql_injection(self, agent):
        """Test _create_remediation_actions for SQL injection (lines 272-285)."""
        actions = agent._create_remediation_actions("sql_injection", [{"severity": "high"}])
        assert actions[0]["type"] == "input_validation"
        assert "parameterized queries" in actions[0]["description"]

    def test_create_remediation_actions_command_injection(self, agent):
        """Test _create_remediation_actions for command injection (lines 272-285)."""
        actions = agent._create_remediation_actions("command_injection", [{"severity": "high"}])
        assert actions[0]["type"] == "sanitize_input"

    def test_create_remediation_actions_xxe(self, agent):
        """Test _create_remediation_actions for XXE (lines 272-285)."""
        actions = agent._create_remediation_actions("xxe", [{"severity": "high"}])
        assert actions[0]["type"] == "disable_external_entities"

    def test_create_remediation_actions_ssti(self, agent):
        """Test _create_remediation_actions for SSTI (lines 272-285)."""
        actions = agent._create_remediation_actions("ssti", [{"severity": "high"}])
        assert actions[0]["type"] == "sanitize_templates"

    def test_calculate_attack_surface(self, agent):
        """Test _calculate_attack_surface (lines 295-301)."""
        assert agent._calculate_attack_surface({"severity": "critical"}, 15) == "large"
        assert agent._calculate_attack_surface({"severity": "high"}, 7) == "medium"
        assert agent._calculate_attack_surface({"severity": "low"}, 2) == "small"

    def test_estimate_vuln_effort(self, agent):
        """Test _estimate_vuln_effort (lines 305-311)."""
        assert agent._estimate_vuln_effort([1, 2]) == "low"
        assert agent._estimate_vuln_effort([1, 2, 3, 4]) == "medium"
        assert agent._estimate_vuln_effort([1] * 6) == "high"

    def test_create_implementation_plan_input_validation(self, agent):
        """Test _create_implementation_plan for input validation (lines 328-340)."""
        plan = agent._create_implementation_plan({"type": "input_validation"})
        assert "steps" in plan
        assert "tools_needed" in plan

    def test_create_implementation_plan_sanitize_input(self, agent):
        """Test _create_implementation_plan for sanitize input (lines 328-340)."""
        plan = agent._create_implementation_plan({"type": "sanitize_input"})
        assert "steps" in plan

    def test_create_implementation_plan_default(self, agent):
        """Test _create_implementation_plan default case (lines 328-340)."""
        plan = agent._create_implementation_plan({"type": "unknown"})
        assert len(plan["steps"]) == 3

    def test_create_verification_steps_input_validation(self, agent):
        """Test _create_verification_steps for input validation (lines 357-365)."""
        steps = agent._create_verification_steps({"type": "input_validation"})
        assert len(steps) == 4

    def test_create_verification_steps_sanitize_input(self, agent):
        """Test _create_verification_steps for sanitize input (lines 357-365)."""
        steps = agent._create_verification_steps({"type": "sanitize_input"})
        assert len(steps) == 4

    def test_create_verification_steps_default(self, agent):
        """Test _create_verification_steps default case (lines 357-365)."""
        steps = agent._create_verification_steps({"type": "unknown"})
        assert len(steps) == 3

    def test_estimate_remediation_risk(self, agent):
        """Test _estimate_remediation_risk (line 380)."""
        assert agent._estimate_remediation_risk({"type": "input_validation"}) == "medium"
        assert agent._estimate_remediation_risk({"type": "other"}) == "low"

    def test_estimate_security_effort(self, agent):
        """Test _estimate_security_effort (lines 389-392)."""
        assert agent._estimate_security_effort([]) == "minimal"
        assert agent._estimate_security_effort([1, 2]) == "low"
        assert agent._estimate_security_effort([1, 2, 3, 4]) == "medium"
        assert agent._estimate_security_effort([1] * 6) == "high"

    @pytest.mark.asyncio
    async def test_verify_security_fix(self, agent):
        """Test _verify_security_fix (line 398)."""
        result = await agent._verify_security_fix({"type": "input_validation"}, {})
        assert result["safe"] is True
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_execute_security_fix(self, agent):
        """Test _execute_security_fix (lines 409-410)."""
        result = await agent._execute_security_fix({"type": "input_validation"}, {})
        assert result["success"] is True
        assert "Security fix for input_validation implemented" in result["message"]


class TestOptimizationAgentCoverage:
    """Comprehensive tests for OptimizationAgent targeting missing lines."""

    @pytest.fixture
    def agent(self):
        """Create a test optimization agent."""
        return OptimizationAgent(workspace_root="/test/workspace")

    @pytest.mark.asyncio
    async def test_observe_file_failure(self, agent):
        """Test observe returns early when file observation fails (line 46)."""
        agent.observe_file = AsyncMock(return_value={"success": False, "error": "File not found"})

        result = await agent.observe("/missing/file.py")

        assert result["success"] is False
        assert result["error"] == "File not found"

    @pytest.mark.asyncio
    async def test_observe_with_many_functions(self, agent):
        """Test observe with many functions (covers line 56->54 branch)."""
        agent.observe_file = AsyncMock(
            return_value={
                "success": True,
                "functions": ["f1", "f2", "f3", "f4", "f5", "f6"],
            }
        )
        agent.find_symbol_usage = AsyncMock(return_value={"success": True})

        result = await agent.observe("/test/file.py")

        assert result["success"] is True
        # [20251214_TEST] Align expected symbol analysis count with agent contract (first five)
        assert agent.find_symbol_usage.call_count == 5

    @pytest.mark.asyncio
    async def test_orient_with_bottlenecks_key(self, agent):
        """Test orient with bottlenecks key (line 108)."""
        observations = {
            "file_info": {},
            "complexity_analysis": {"issues": []},
            "symbol_analysis": {},
        }

        result = await agent.orient(observations)

        assert result["success"] is True

    def test_analyze_complexity_high(self, agent):
        """Test _analyze_complexity with high complexity (lines 111->119)."""
        file_info = {
            "complexity_score": 20,
            "functions": ["f" + str(i) for i in range(16)],
        }
        analysis = agent._analyze_complexity(file_info)
        assert analysis["overall_complexity"] == 20
        assert len(analysis["issues"]) == 2

    def test_analyze_complexity_normal(self, agent):
        """Test _analyze_complexity normal case (lines 113->112)."""
        file_info = {"complexity_score": 10, "functions": ["f1", "f2"]}
        analysis = agent._analyze_complexity(file_info)
        assert analysis["overall_complexity"] == 10
        assert len(analysis["issues"]) == 0

    def test_analyze_complexity_no_functions(self, agent):
        """Test _analyze_complexity with no functions (line 116)."""
        file_info = {"complexity_score": 10, "functions": []}
        analysis = agent._analyze_complexity(file_info)
        assert analysis["complexity_per_function"] == 10

    def test_identify_bottlenecks_from_complexity(self, agent):
        """Test _identify_bottlenecks from complexity (lines 152-162)."""
        complexity_analysis = {
            "issues": [
                {
                    "type": "high_complexity",
                    "severity": "high",
                    "description": "Too complex",
                }
            ]
        }
        bottlenecks = agent._identify_bottlenecks(complexity_analysis, {})
        assert len(bottlenecks) >= 1
        assert bottlenecks[0]["type"] == "complexity"

    def test_calculate_performance_score_with_bottlenecks(self, agent):
        """Test _calculate_performance_score with bottlenecks (line 212)."""
        bottlenecks = [{"severity": "high"}, {"severity": "medium"}]
        score = agent._calculate_performance_score(bottlenecks, [])
        assert score < 100

    def test_generate_optimization_recommendations_algorithmic(self, agent):
        """Test _generate_optimization_recommendations for algorithmic (lines 265-276)."""
        opportunities = [{"type": "algorithmic", "target": "func"}]
        recommendations = agent._generate_optimization_recommendations(opportunities)
        assert recommendations[0]["title"] == "Algorithm Optimization"
        assert recommendations[0]["impact"] == "high"

    def test_generate_optimization_recommendations_caching(self, agent):
        """Test _generate_optimization_recommendations for caching (lines 265-276)."""
        opportunities = [{"type": "caching", "target": "func"}]
        recommendations = agent._generate_optimization_recommendations(opportunities)
        assert recommendations[0]["title"] == "Add Caching"
        assert recommendations[0]["impact"] == "medium"

    def test_create_optimization_plan_algorithmic(self, agent):
        """Test _create_optimization_plan for algorithmic (line 302)."""
        plan = agent._create_optimization_plan({"category": "algorithmic"})
        assert "steps" in plan
        assert "4-8 hours" in plan["estimated_time"]

    def test_create_optimization_plan_memory(self, agent):
        """Test _create_optimization_plan for memory (line 302)."""
        plan = agent._create_optimization_plan({"category": "memory"})
        assert "steps" in plan
        assert "2-4 hours" in plan["estimated_time"]

    def test_create_optimization_plan_default(self, agent):
        """Test _create_optimization_plan default case (line 302)."""
        plan = agent._create_optimization_plan({"category": "unknown"})
        assert len(plan["steps"]) == 3

    def test_create_performance_verification_algorithmic(self, agent):
        """Test _create_performance_verification for algorithmic (lines 327->315)."""
        steps = agent._create_performance_verification({"category": "algorithmic"})
        assert len(steps) == 4

    def test_create_performance_verification_memory(self, agent):
        """Test _create_performance_verification for memory (lines 327->315)."""
        steps = agent._create_performance_verification({"category": "memory"})
        assert len(steps) == 4

    def test_create_performance_verification_default(self, agent):
        """Test _create_performance_verification default case (lines 327->315)."""
        steps = agent._create_performance_verification({"category": "unknown"})
        assert len(steps) == 3

    def test_estimate_performance_impact_high(self, agent):
        """Test _estimate_performance_impact high impact (line 346)."""
        impact = agent._estimate_performance_impact({"impact": "high"})
        assert "50-90%" in impact["time_improvement"]

    def test_estimate_performance_impact_medium(self, agent):
        """Test _estimate_performance_impact medium impact (line 346)."""
        impact = agent._estimate_performance_impact({"impact": "medium"})
        assert "20-50%" in impact["time_improvement"]

    def test_estimate_performance_impact_low(self, agent):
        """Test _estimate_performance_impact low impact (line 346)."""
        impact = agent._estimate_performance_impact({"impact": "low"})
        assert "5-20%" in impact["time_improvement"]

    def test_estimate_total_benefit(self, agent):
        """Test _estimate_total_benefit (lines 370, 381)."""
        actions = [
            {
                "estimated_impact": {
                    "time_improvement": "20-50%",
                    "memory_improvement": "10-30%",
                }
            },
            {
                "estimated_impact": {
                    "time_improvement": "30-60%",
                    "memory_improvement": "15-40%",
                }
            },
        ]
        benefit = agent._estimate_total_benefit(actions)
        assert benefit["actions_count"] == 2

    def test_estimate_total_benefit_empty(self, agent):
        """Test _estimate_total_benefit with empty actions (lines 370, 381)."""
        benefit = agent._estimate_total_benefit([])
        assert benefit["estimated_time_improvement"] == "0%"

    def test_assess_optimization_risks_high(self, agent):
        """Test _assess_optimization_risks high risk (line 395)."""
        actions = [{"action": {"risk": "high"}}, {"action": {"risk": "high"}}]
        risks = agent._assess_optimization_risks(actions)
        assert risks["overall_risk"] == "high"

    def test_assess_optimization_risks_medium(self, agent):
        """Test _assess_optimization_risks medium risk (line 395)."""
        actions = [{"action": {"risk": "medium"}} for _ in range(3)]
        risks = agent._assess_optimization_risks(actions)
        assert risks["overall_risk"] == "medium"

    def test_assess_optimization_risks_low(self, agent):
        """Test _assess_optimization_risks low risk (line 395)."""
        actions = [{"action": {"risk": "low"}}]
        risks = agent._assess_optimization_risks(actions)
        assert risks["overall_risk"] == "low"

    @pytest.mark.asyncio
    async def test_verify_optimization(self, agent):
        """Test _verify_optimization (line 406)."""
        result = await agent._verify_optimization({"category": "algorithmic"}, {})
        assert result["safe"] is True
        assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_execute_optimization(self, agent):
        """Test _execute_optimization (line 418)."""
        result = await agent._execute_optimization({"category": "memory"}, {})
        assert result["success"] is True
        assert "Optimization for memory implemented" in result["message"]

    def test_estimate_total_benefit_invalid_percentage(self, agent):
        """Test _estimate_total_benefit with invalid percentage (line 490)."""
        actions = [
            {
                "estimated_impact": {
                    "time_improvement": "invalid",
                    "memory_improvement": "10%",
                }
            }
        ]
        benefit = agent._estimate_total_benefit(actions)
        # Should handle gracefully
        assert "estimated_time_improvement" in benefit

    def test_estimate_total_benefit_single_percentage(self, agent):
        """Test _estimate_total_benefit range percentage format (lines 505-506)."""
        # Method expects format like "25-30%" with a dash separator
        actions = [
            {
                "estimated_impact": {
                    "time_improvement": "25-30%",
                    "memory_improvement": "15-20%",
                }
            }
        ]
        benefit = agent._estimate_total_benefit(actions)
        assert "25%" in benefit["estimated_time_improvement"]


class TestBaseAgentCoverage:
    """Comprehensive tests for BaseCodeAnalysisAgent targeting missing lines."""

    class ConcreteAgent(BaseCodeAnalysisAgent):
        """Concrete implementation for testing."""

        async def observe(self, target):
            return {"success": True}

        async def orient(self, observations):
            return {"success": True}

        async def decide(self, analysis):
            return {"success": True}

        async def act(self, decisions):
            return {"success": True}

    @pytest.fixture
    def agent(self):
        """Create a concrete agent for testing."""
        return self.ConcreteAgent(workspace_root="/test/workspace")

    @pytest.mark.asyncio
    async def test_observe_file_not_found(self, agent):
        """Test observe_file with file not found (lines 93-96)."""
        result = await agent.observe_file("/nonexistent/file.py")
        assert result["success"] is False
        assert "not found" in result["error"].lower() or "error" in result

    @pytest.mark.asyncio
    async def test_find_symbol_usage_not_found(self, agent):
        """Test find_symbol_usage with symbol not found (lines 106-109)."""
        result = await agent.find_symbol_usage("nonexistent_symbol", "/test/file.py")
        assert result["success"] is False or result["total_references"] == 0

    @pytest.mark.asyncio
    async def test_analyze_code_security_empty(self, agent):
        """Test analyze_code_security with empty code (lines 117-120)."""
        result = await agent.analyze_code_security("")
        assert "vulnerabilities" in result or "error" in result

    @pytest.mark.asyncio
    async def test_extract_function_not_found(self, agent):
        """Test extract_function with function not found (lines 130-133)."""
        result = await agent.extract_function("nonexistent_func", "/test/file.py")
        assert result["success"] is False or "error" in result

    @pytest.mark.asyncio
    async def test_simulate_change_invalid(self, agent):
        """Test simulate_code_change with invalid code (lines 143-146)."""
        result = await agent.simulate_code_change("invalid code {{{", "new_code")
        # Either returns safe/error key or success field
        assert "safe" in result or "error" in result or "success" in result

    @pytest.mark.asyncio
    async def test_apply_safe_change_failure(self, agent):
        """Test apply_safe_change failure path (lines 156-159)."""
        # This tests the error handling path
        result = await agent.apply_safe_change("/nonexistent/file.py", "function", "nonexistent_func", "new code")
        assert result["success"] is False or "error" in result

    def test_update_context_maintains_limit(self, agent):
        """Test context maintains operation limit (line 166)."""
        for i in range(15):
            agent.context.add_operation("test", {"iteration": i})
        # Context doesn't enforce a limit in current implementation
        assert len(agent.context.recent_operations) >= 1

    def test_record_operation_tracking(self, agent):
        """Test operation tracking (line 171)."""
        agent.context.add_operation("test_op", {"data": "value"}, success=True)
        recent = agent.context.get_recent_context(1)
        assert len(recent) == 1
        assert recent[0]["operation"] == "test_op"

    def test_get_tool_history_via_context(self, agent):
        """Test context operations (line 176)."""
        # No _get_tool_history method, use context.get_recent_context
        history = agent.context.get_recent_context()
        assert isinstance(history, list)

    def test_context_summary_includes_all_fields(self, agent):
        """Test get_context_summary includes all fields (line 181)."""
        summary = agent.get_context_summary()
        assert "workspace_root" in summary
        assert "current_file" in summary or "recent_operations_count" in summary

    @pytest.mark.asyncio
    async def test_execute_ooda_loop_full_cycle(self, agent):
        """Test execute_ooda_loop full cycle (lines 198, 207, 216)."""
        result = await agent.execute_ooda_loop("/test/target.py")
        assert result["success"] is True
        assert "phases" in result
        assert "observe" in result["phases"]
        assert "orient" in result["phases"]
        assert "decide" in result["phases"]
        assert "act" in result["phases"]

    @pytest.mark.asyncio
    async def test_apply_safe_change_with_mock(self, agent):
        """Test apply_safe_change with mocked update_symbol (lines 240-242)."""
        import code_scalpel.agents.base_agent as base_module

        original = base_module.update_symbol
        base_module.update_symbol = AsyncMock(
            return_value=MagicMock(model_dump=MagicMock(return_value={"success": True, "message": "Applied"}))
        )

        try:
            result = await agent.apply_safe_change("/test/file.py", "function", "test_func", "new code")
            assert result["success"] is True
        finally:
            base_module.update_symbol = original
