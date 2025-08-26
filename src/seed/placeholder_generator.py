from seed.schemas import PlaceholderCandidate
from llm_core.api_provider import LLM
from llm_core.api_call import make_api_call
from tqdm import tqdm
import json
import asyncio
import os

class PlaceholderGenerator:
    """
    Maintains a catalog of placeholders and, for each seed, asks the LLM to:
      1) select relevant placeholders from the catalog, and
      2) propose new ones (with name + description + example).
    """

    def __init__(self, seeds_path, seeds_and_placeholders_path=None, placeholders_path=None):
        """
        seeds_path: path to a JSON file containing newly generated seeds that need placeholders

        seeds_and_placeholders_path: path to the output JSON file containing seeds with their placeholders,
        if the file already exists, we will append to it, otherwise create a new one.
        If None, defaults to "seeds_and_placeholders.json".

        placeholders_path: path to a JSON file containing the catalog of placeholders,
        if the file already exists, we will load from it, otherwise start with a default list.
        If None, defaults to "placeholders.json".
        """
        self.seeds_and_placeholders_path = seeds_and_placeholders_path or "seeds_and_placeholders.json"
        self.placeholders_path = placeholders_path or "placeholders.json"

        self.seeds = self.load_seeds(seeds_path)
        self.placeholders = self.initialize_placeholders()
        self.seeds_and_placeholders = self.initialize_seeds_and_placeholders()

        self.llm = LLM(provider="openai", model="gpt-5", use_response_api=True).get_llm()

    def load_seeds(self, seeds_path):
        if not os.path.isfile(seeds_path):
            raise FileNotFoundError(f"Seed file not found: {seeds_path}")
        with open(seeds_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def initialize_seeds_and_placeholders(self):
        if os.path.isfile(self.seeds_and_placeholders_path):
            with open(self.seeds_and_placeholders_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return []

    def initialize_placeholders(self):
        """
        if self.placeholders_path exists, load from it;
        otherwise, return a default list
        """
        default_placeholders = [
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
        if self.placeholders_path and os.path.isfile(self.placeholders_path):
            with open(self.placeholders_path, "r", encoding="utf-8") as f:
                placeholders = json.load(f)
                if len(placeholders) == 0:
                    return default_placeholders
                else:
                    return placeholders
        else:
            return default_placeholders

    async def generate_placeholders_for_seeds(self):
        results = self.seeds_and_placeholders
        for seed_record in tqdm(self.seeds, desc="Generating placeholders"):
            try:
                seed = seed_record["seed"]
                response = await self._generate_placeholders_from_one_seed(seed)
                if response:
                    results.append({
                        "type": seed_record["type"],
                        "summary": seed_record["summary"],
                        "seed": seed,
                        "placeholders": response}
                    )
            except Exception as e:
                print(f"Error generating placeholders for seed '{seed_record["seed"]}': {e}")
                continue

        with open(self.seeds_and_placeholders_path, "w") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        return results

    async def _generate_placeholders_from_one_seed(self, seed):
        """
        Ask the LLM to select existing placeholders and add new ones.
        Returns a flat list of placeholder NAMES used for this seed.
        """

        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(seed)

        response = await make_api_call(
            llm=self.llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=PlaceholderCandidate
        )

        placeholders_for_this_seed = []

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
                placeholders_for_this_seed.append(selected_placeholder)
            else:
                print(f"Warning: Selected placeholder '{selected_placeholder}' not found in provided list -> Skipped.")

        # Check 3)
        for added_placeholder in added:
            if added_placeholder["placeholder_name"] not in existed_placeholder_names:
                placeholders_for_this_seed.append(added_placeholder["placeholder_name"])
                self.placeholders.append(added_placeholder)
                existed_placeholder_names.append(added_placeholder["placeholder_name"])
            else:
                print(f"Warning: Placeholder '{added_placeholder['placeholder_name']}' already exists -> Skipped.")

        # Check 4)
        if "<caller_name>" not in placeholders_for_this_seed:
            placeholders_for_this_seed.append("<caller_name>")
            print("Added <caller_name> to placeholders.")
        if "<callee_name>" not in placeholders_for_this_seed:
            placeholders_for_this_seed.append("<callee_name>")
            print("Added <callee_name> to placeholders.")

        return placeholders_for_this_seed

    def _create_user_prompt(self, seed: str):
        provided_placeholders_str = ", ".join(
            f"{p['placeholder_name']} (e.g., {p['example']})"
            for p in self.placeholders
        ) if self.placeholders else "(none)"

        return (
            f"Seed: {seed}\n"
            f"Provided placeholders: {provided_placeholders_str}\n"
        )

    def _create_system_prompt(self):
        return (
            "You are an expert in localization and dataset preparation.\n\n"
            "From a scam-call SEED:\n"
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
            "- The placeholders should be specific, so any substitution would make sense in the conversation (e.g., <proof_of_income_document> instead of <document>; <immigration_agency_name> instead of <agency_name>)\n\n"
        )


# Example usage:
if __name__ == "__main__":
    generator = PlaceholderGenerator(seeds_path="./seeds_llm.json")
    asyncio.run(generator.generate_placeholders_for_seeds())
    with open(generator.placeholders_path, "w") as f:
        json.dump(generator.placeholders, f, indent=4, ensure_ascii=False)
