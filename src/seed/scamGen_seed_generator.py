from schemas import SeedRecord
from llm_core.api_call import make_api_call
from llm_core.api_provider import LLM
import asyncio
import json
from utils_async import run_concurrent_tasks, save_json_array

class ScamGenSeedGenerator:
    def __init__(self, max_concurrent=10):
        self.max_concurrent = max_concurrent
        llm_instance = LLM(model="gpt-5", provider="openai")
        self.llm = llm_instance.get_llm()
        self.scam_categories = self.initialize_scam_categories()

    def initialize_scam_categories(self):
        return [
            "Government Authority",
            "Consumer Services",
            "Workplace",
            "Employment",
            "Financial Service",
            "Healthcare",
            "Education",
            "Personal Relationships",
            "Technology",
            "Prize and Lottery",
            "Charity and Nonprofit",
            "Sexual Blackmail",
            "Other"
        ]

    async def generate_seeds_from_scenarios(self, input_path, output_path):
        """
        Generate seeds from a file containing scam conversation scenarios.
        Each line in the input file is treated as a separate scenario.
        """
         # Load lines
        with open(input_path, 'r') as infile:
            lines = [line.strip() for line in infile if line.strip()]

        # Create tasks (these are coroutines)
        tasks = [self._generate_seed_from_single_scenario(line) for line in lines]

        # Run with concurrency control
        results = await run_concurrent_tasks(tasks,
                                             max_concurrent=self.max_concurrent,
                                             description="Generating Seeds")

        # Process results with error handling
        seeds = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Task {idx} failed: {result}")
            elif result:
                seeds.append(result)

        # Save successful results
        save_json_array(seeds, output_path)

        print(f"Generated {len(seeds)} seeds from {input_path} to {output_path}.")
        return seeds

    async def _generate_seed_from_single_scenario(self, line):
        """
        Generate a SeedRecord from a single scenario line.
        """
        example_seed_record = {
            "type": "Government Authority",
            "summary": "Government tax agency requesting payment or personal ID verification.",
            "seed": "The caller (scammer) claims to be from the national tax authority and tells the callee there is an outstanding tax balance or an error in recent filings that must be fixed immediately. The caller warns that failure to act will result in legal action, frozen accounts, or seizure of assets. The caller instructs the callee to provide personal identification details such as a national ID number, tax number, or bank information, or to make an immediate payment through methods like wire transfer, prepaid card, or cryptocurrency."
        }
        system_prompt = (
            "You are an expert at creating scam call seed record from a given scam scenario.\n"
            "A seed record consists of a scam type, a concise short one-sentence summary, and a 2-4 sentences scam call description.\n"
            "\n"
            "1. for the scam type, choose the most appropriate category from the provided list of scam categories: "
            + ", ".join(self.scam_categories) + ".\n"
            "2. for the summary, explain the scam scenario concisely in a short sentence.\n"
            "3. for the scam call description, provide a detailed description of how the phone call scam typically unfolds, you only need to provide things happened WITHIN the scam call conversation.\n"
            "\n"
            "STRICT RULES:\n"
            "- The output must be general for any country.\n"
            "- Use only generic terms such as 'a bank', 'a government tax agency', 'a delivery company'.\n"
            "\n"
            "Here is an example of a well-formed seed record:\n"
            f"{json.dumps(example_seed_record, indent=4)}\n"
            "\n"
            "Format your response as a JSON object with fields: type, summary, seed."
        )
        user_prompt = (
            f"Scam Scenario: {line}\n"
            "Please provide the scam type, summary, and seed as specified."
        )
        response_schema = SeedRecord
        response = await make_api_call(
            llm = self.llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema)
        return response

if __name__ == "__main__":
    input_path = "./scamGen_scenario.txt"
    output_path = "./seeds_scamGen.json"
    scam_gen_seed_generator = ScamGenSeedGenerator()
    asyncio.run(
        scam_gen_seed_generator.generate_seeds_from_scenarios(input_path,output_path)
    )
