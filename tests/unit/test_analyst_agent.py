from unittest.mock import patch

from backend.simulation.analyst_agent import AnalystAgent


class TestAnalystAgentConfig:
    def test_default_uses_report_llm_config(self):
        with patch.dict("os.environ", {
            "LLM_MODEL": "DeepSeek-V3.2",
            "REPORT_LLM_MODEL": "DeepSeek-R1-0528-64k",
            "REPORT_LLM_BASE_URL": "http://report/v1",
            "REPORT_LLM_API_KEY": "report-key",
            "REPORT_LLM_TIMEOUT": "120",
            "REPORT_LLM_MAX_TOKENS": "2000",
            "REPORT_LLM_TEMPERATURE": "0.5",
        }, clear=False):
            agent = AnalystAgent()

        assert agent.llm_config.model == "DeepSeek-R1-0528-64k"
        assert agent.llm_config.base_url == "http://report/v1"
        assert agent.llm_config.api_key == "report-key"
        assert agent.llm_config.timeout == 120
        assert agent.llm_config.max_tokens == 2000
        assert agent.llm_config.temperature == 0.5
