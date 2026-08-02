import json
import unittest
from unittest.mock import Mock, patch

from backend.agent import azure_openai, runner
from backend.data_layer import excel_store


class AzureOpenAIClientTests(unittest.TestCase):
    def test_chat_completion_uses_azure_deployment_endpoint_and_tool_schema(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "done"}}]
        }
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_open_invoices",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        with (
            patch.object(azure_openai, "AZURE_OPENAI_API_KEY", "test-key"),
            patch.object(azure_openai.requests, "post", return_value=response) as post,
        ):
            result = azure_openai.chat_completion(
                [{"role": "user", "content": "Run"}],
                tools=tools,
                max_completion_tokens=1234,
            )

        self.assertEqual(result["choices"][0]["message"]["content"], "done")
        call = post.call_args
        self.assertIn("/openai/deployments/t1-gpt-5-nano/chat/completions", call.args[0])
        self.assertEqual(call.kwargs["params"], {"api-version": "2024-12-01-preview"})
        self.assertEqual(call.kwargs["headers"]["api-key"], "test-key")
        self.assertEqual(call.kwargs["json"]["tools"], tools)
        self.assertEqual(call.kwargs["json"]["tool_choice"], "auto")
        self.assertEqual(call.kwargs["json"]["max_completion_tokens"], 1234)

    def test_missing_api_key_fails_before_network_call(self):
        with (
            patch.object(azure_openai, "AZURE_OPENAI_API_KEY", ""),
            patch.object(azure_openai.requests, "post") as post,
            self.assertRaisesRegex(
                azure_openai.AzureOpenAIError, "AZURE_OPENAI_API_KEY"
            ),
        ):
            azure_openai.chat_completion([{"role": "user", "content": "Run"}])
        post.assert_not_called()


class AzureAgentRunnerTests(unittest.TestCase):
    def test_tool_result_is_returned_to_model_in_openai_message_format(self):
        first = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "get_open_invoices",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                }
            ]
        }
        second = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Cycle complete.",
                    }
                }
            ]
        }
        state = {"current_date": "2026-08-02", "cycle_count": 0}

        with (
            patch.object(runner, "chat_completion", side_effect=[first, second]) as chat,
            patch.object(
                runner,
                "execute_tool",
                return_value=json.dumps({"open_invoices": [], "count": 0}),
            ) as execute,
            patch.object(excel_store, "get_system_state", return_value=state),
            patch.object(excel_store, "save_system_state"),
        ):
            result = runner.run_daily_cycle("2026-08-02")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provider"], "azure_openai")
        self.assertEqual(result["tool_calls"], 1)
        execute.assert_called_once_with("get_open_invoices", {}, "2026-08-02")
        second_messages = chat.call_args_list[1].args[0]
        tool_messages = [
            message for message in second_messages if message["role"] == "tool"
        ]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0]["tool_call_id"], "call-1")


if __name__ == "__main__":
    unittest.main()
