from seed.schemas import PlaceholderCandidate
from llm_core.api_provider import LLM
from llm_core.api_call import make_api_call
from tqdm import tqdm
import json
import asyncio
import csv
import os

class PlaceholderGenerator:
    """
    Maintains a catalog of placeholders and, for each summary, asks the LLM to:
      1) select relevant placeholders from the catalog, and
      2) propose new ones (with name + description + example).
    """

    def __init__(self, summaries_path, summaries_and_placeholders_path=None, placeholders_path=None):
        self.placeholders = self.initialize_placeholders()
        llm_instance = LLM(provider="openai", model="gpt-4o", use_response_api=True)
        self.llm = llm_instance.get_llm()
        self.summaries = self.parse_summary(summaries_path)
        self.summaries_and_placeholders_path = summaries_and_placeholders_path or "summaries_and_placeholders.json"
        self.placeholders_path = placeholders_path or "placeholders.json"

    async def generate_placeholders_for_summaries(self, summary_list):
        results = []
        for summary in tqdm(summary_list, desc="Generating placeholders"):
            try:
                response = await self._generate_placeholders_from_one_summary(summary)
                if response:
                    results.append({"summary": summary, "placeholders": response})
            except Exception as e:
                print(f"Error generating placeholders for summary '{summary}': {e}")
                continue

        with open(self.summaries_and_placeholders_path, "w") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        return results

    async def _generate_placeholders_from_one_summary(self, summary):
        """
        Ask the LLM to select existing placeholders and add new ones.
        Returns a flat list of placeholder NAMES used for this summary.
        """

        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(summary)

        response = await make_api_call(llm=self.llm, system_prompt=system_prompt,
                                 user_prompt=user_prompt, response_schema=PlaceholderCandidate)

        placeholders_for_this_summary = []

        selected = list(response.selected_placeholders)
        added = [
            {"placeholder_name": placeholder.name,
            "description": placeholder.description,
            "example": placeholder.example}
            for placeholder in response.added_placeholders
        ]

        # We want to ensure:
        # 1) The total number of placeholders (selected + added) is between 4 and 6.
        # 2) The selected placeholders are unique and in the provided list.
        # 3) The added placeholders are unique and not already in the provided list.
        # 4) <caller_name> and <callee_name> are always included.

        # check 1)
        if len(selected) + len(added) < 4 or len(selected) + len(added) > 6:
            print(f"Warning: Total placeholders (selected + added) is {len(selected) + len(added)}, "
                  "which is outside the ideal range of 4 to 6.")

        # check 2)
        existed_placeholder_names = list(set([p["placeholder_name"] for p in self.placeholders]))
        for selected_placeholder in selected:
            if selected_placeholder in existed_placeholder_names:
                placeholders_for_this_summary.append(selected_placeholder)
            else:
                print(f"Warning: Selected placeholder '{selected_placeholder}' not found in provided list -> Skipped.")

        # Check 3)
        for added_placeholder in added:
            if added_placeholder["placeholder_name"] not in existed_placeholder_names:
                placeholders_for_this_summary.append(added_placeholder["placeholder_name"])
                self.placeholders.append(added_placeholder)
                existed_placeholder_names.append(added_placeholder["placeholder_name"])
            else:
                print(f"Warning: Placeholder '{added_placeholder['placeholder_name']}' already exists -> Skipped.")

        # Check 4)
        if "<caller_name>" not in placeholders_for_this_summary:
            placeholders_for_this_summary.append("<caller_name>")
            print("Added <caller_name> to placeholders.")
        if "<callee_name>" not in placeholders_for_this_summary:
            placeholders_for_this_summary.append("<callee_name>")
            print("Added <callee_name> to placeholders.")

        return placeholders_for_this_summary

    def _create_user_prompt(self, summary: str):
        provided_placeholders_str = ", ".join(
            f"{p['placeholder_name']} (e.g., {p['example']})"
            for p in self.placeholders
        ) if self.placeholders else "(none)"

        return (
            f"Summary: {summary}\n"
            f"Provided placeholders: {provided_placeholders_str}\n"
        )

    def _create_system_prompt(self):
        return (
            "You are an expert in localization and dataset preparation.\n\n"
            "From a scam-call SUMMARY:\n"
            "1. Select non-repetitive relevant placeholders from a provided catalog. "
            "Do NOT include placeholders that will be used similarly (e.g., <money_amount_small> and <money_amount_medium>).\n"
            "2. Add any missing placeholders that would vary by country, region, or culture. "
            "Do NOT include universal elements (e.g., generic due dates).\n\n"
            "If a placeholder is missing from the provided catalog, ADD it with:\n"
            "- `name` in snake_case wrapped in < > (e.g., <male_name>),\n"
            "- `description` explaining the cultural variation,\n"
            "- `example` realistic for the United States.\n\n"
            "Output schema (exact):\n"
            "1) selected_placeholders: List[str]\n"
            "2) added_placeholders: List[Placeholder]  # fields: name, description, example\n\n"
            "Hard constraints\n"
            "- Always include <caller_name> and <callee_name>.\n"
            "- TOTAL Placeholders (selected + added) MUST be between 4 and 6. Never exceed 6.\n"
            "- The placeholders should be specific, (e.g., <proof_of_income_document> instead of <document>)\n\n"
        )

    def parse_summary(self, file_path):
        """
        Parse a CSV file containing summaries.
        CSV format is expected to have summaries in the second column and without headers.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        summaries = []
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 1:  # ensure there is a second column
                    val = (row[1] or "").strip()
                    if val:
                        summaries.append(val)
        return summaries

    def initialize_placeholders(self):
        return [
            {
                "placeholder_name": "<caller_name>",
                "description": "Localized personal name for the person making the scam call, common in the target locale.",
                "example": "Michael"
            },
            {
                "placeholder_name": "<callee_name>",
                "description": "Localized personal name for the person receiving the scam call, common in the target locale.",
                "example": "Emily"
            },
            {
                "placeholder_name": "<money_amount_small>",
                "description": "Small amount of money relative to the target locale's purchasing power.",
                "example": "$25"
            },
            {
                "placeholder_name": "<money_amount_medium>",
                "description": "Medium amount of money relative to the target locale's purchasing power.",
                "example": "$250"
            },
            {
                "placeholder_name": "<money_amount_large>",
                "description": "Large amount of money relative to the target locale's purchasing power.",
                "example": "$2,500"
            }
        ]

# Example usage:
if __name__ == "__main__":
    limit = 5  # Limit for testing
    generator = PlaceholderGenerator(summaries_path="summaries.csv",)
    asyncio.run(generator.generate_placeholders_for_summaries(generator.summaries[:min(len(generator.summaries), limit)]))
    with open(generator.placeholders_path, "w") as f:
        json.dump(generator.placeholders, f, indent=4, ensure_ascii=False)
