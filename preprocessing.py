from config_arabic import preprocessing_input_path, preprocessing_output_path, preprocessing_map_path
import re
import json

def extract_tags(input_path, output_path, map_path):
    # Mapping state
    mapping = {}
    records = {}

    # Pattern to match tags including <>
    pattern = re.compile(r'<[^>]+>')

    # Process TXT: replace tags and build mapping
    with open(input_path, "r", encoding="utf-8") as infile, \
         open(output_path, "w", encoding="utf-8") as outfile:
        for line in infile:
            def repl(m):
                tag = m.group(0)
                if tag not in mapping:
                    code = f"{{{len(mapping) + 1:05d}}}"
                    mapping[tag] = code
                    records[code] = {"tag": tag, "substitutions": [], "translations": []}
                return mapping[tag]

            new_line = pattern.sub(repl, line)
            outfile.write(new_line)

    # Write mapping JSON (code→tag & substitutions)
    with open(map_path, "w", encoding="utf-8") as mf:
        json.dump(records, mf, indent=2, ensure_ascii=False)

    print(f"Replaced tags in {output_path} and wrote mapping to {map_path}")


extract_tags(preprocessing_input_path, preprocessing_output_path, preprocessing_map_path)
