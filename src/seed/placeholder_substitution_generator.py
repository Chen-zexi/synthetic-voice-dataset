from schemas import PlaceholderSubstitution
from llm_core.api_call import make_api_call
from llm_core.api_provider import LLM
from utils_async import run_concurrent_tasks, save_json_array
import asyncio
import json

class PlaceholderSubstitutionGenerator:
    def __init__(self, region, language, placeholders_path, substitutions_output_path, max_concurrent, num_substitutions_min, num_substitutions_max):
        self.region = region
        self.language = language
        self.placeholders = self.load_placeholders(placeholders_path)
        self.substitutions_output_path = substitutions_output_path
        self.llm = LLM(provider="openai", model="gpt-5", use_response_api=True).get_llm()
        self.max_concurrent = max_concurrent
        self.num_substitutions_min = num_substitutions_min
        self.num_substitutions_max = num_substitutions_max

    def load_placeholders(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def generate_substitutions_from_placeholders(self):
        tasks = []
        for placeholder in self.placeholders:
            name = placeholder["placeholder_name"]
            description = placeholder["description"]
            example = placeholder["example"]
            tasks.append(self.generate_substitutions_for_a_single_placeholder(name, description, example, self.num_substitutions_min, self.num_substitutions_max))

        results = await run_concurrent_tasks(tasks,
                                            max_concurrent=self.max_concurrent,
                                            description="Generating Substitutions")

        substitutions = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Task {idx} failed: {result}")
            elif result:
                if result.placeholder_name != self.placeholders[idx]["placeholder_name"]:
                    print(f"Warning: Mismatched placeholder name for task {idx}: expected {self.placeholders[idx]['placeholder_name']}, got {result.placeholder_name}")
                    # add a dict with the original name and the substitutions from the LLM result
                    substitutions.append({
                        "placeholder_name": self.placeholders[idx]["placeholder_name"],
                        "description": self.placeholders[idx]["description"],
                        "substitutions": result.substitutions,
                        "english_translation_substitutions": result.english_translation_substitutions
                    })
                else:
                    substitutions.append({
                        "placeholder_name": result.placeholder_name,
                        "description": self.placeholders[idx]["description"],
                        "substitutions": result.substitutions,
                        "english_translation_substitutions": result.english_translation_substitutions
                    })

        save_json_array(substitutions, self.substitutions_output_path)

        print(f"Generated substitutions for {len(substitutions)} placeholders.")
        return substitutions

    async def generate_substitutions_for_a_single_placeholder(self, name, description, example, num_substitutions_min, num_substitutions_max):
        system_prompt = (
            "You are a helpful assistant that generates natural, spoken placeholder substitutions "
            "that would realistically appear in a scam call transcript in a specific region and language.\n"
            "Given a placeholder name, its description, and an example, generate the specified number of substitutions "
            "following these strict rules:\n\n"

            "RULES:\n"
            "1) Substitutions should sound natural for BOTH scammer and victim unless clearly one-sided.\n"
            "2) Substitutions should be a SIMPLE NOUN, unless really necessary, DON'T USE longer phrase/sentence.\n"
            "3) Do not add details beyond the placeholder meaning (e.g., <person_name> must be only a name, not include roles or titles)."
            "4) Substitutions must be realistic and believable in spoken conversation—no generic filler like 'Jane Doe' or fake IDs.\n"
            "5) Use only what would be spoken out loud—no brackets, colons, dashes, slashes, or codes.\n"
            "6) Tone must reflect real phone conversations: informal, believable, and locale-appropriate.\n"
            "7) Examples are only for intent clarification (They are not localized or conform to the rules).\n"
            "8) Output must be in the specified language.\n\n"

            "Output JSON format:\n"
            "- placeholder_name: same as input\n"
            "- substitutions: list of localized spoken substitutions\n"
            "- english_translation_substitutions: list of English translations\n"
        )


        user_prompt = (f"Region: {self.region}\n"
                       f"Language: {self.language}\n"
                       f"Placeholder Name: {name}\n"
                       f"Description: {description}\n"
                       f"Example (not localized yet): {example}\n"
                       f"Number of substitutions to generate: around {num_substitutions_min} to {num_substitutions_max}\n")

        response_schema = PlaceholderSubstitution
        response = await make_api_call(
            llm=self.llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema)
        return response

if __name__ == "__main__":
    placeholder_substitution_generator = PlaceholderSubstitutionGenerator(
        region = "Indonesia",
        language = "Indonesian",
        placeholders_path = "./placeholders.json",
        substitutions_output_path = "./id-id_substitutions.json",
        max_concurrent = 3,
        num_substitutions_min=3,
        num_substitutions_max=7
    )
    asyncio.run(
        placeholder_substitution_generator.generate_substitutions_from_placeholders()
    )

